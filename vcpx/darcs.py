#! /usr/bin/python
# -*- mode: python; coding: utf-8 -*-
# :Progetto: vcpx -- Darcs details
# :Creato:   ven 18 giu 2004 14:45:28 CEST
# :Autore:   Lele Gaifax <lele@nautilus.homeip.net>
# 

"""
This module contains supporting classes for the `darcs` versioning system.
"""

__docformat__ = 'reStructuredText'

from shwrap import SystemCommand
from source import UpdatableSourceWorkingDir
from target import SyncronizableTargetWorkingDir, TargetInitializationFailure


class DarcsRecord(SystemCommand):
    COMMAND = "darcs record --all --pipe %(entries)s"

    def __call__(self, output=None, dry_run=False, **kwargs):
        date = kwargs.get('date').strftime('%Y/%m/%d %H:%M:%S')
        author = kwargs.get('author')
        patchname = kwargs.get('patchname')
        logmessage = kwargs.get('logmessage')
        if not logmessage:
            logmessage = ''

        input = "%s UTC\n%s\n%s\n%s\n" % (date, author, patchname, logmessage)
        
        return SystemCommand.__call__(self, output=output, input=input,
                                      dry_run=dry_run, 
                                      **kwargs)


def changesets_from_darcschanges(changes):
    """
    Parse XML output of ``darcs changes``.

    Return a list of `Changeset`s.
    """
    
    from xml.sax import parseString
    from xml.sax.handler import ContentHandler
    from changes import ChangesetEntry, Changeset
    from datetime import datetime

    class DarcsXMLChangesHandler(ContentHandler):
        def __init__(self):
            self.changesets = []
            self.current = None
            self.current_field = []

        def startElement(self, name, attributes):
            if name == 'patch':
                self.current = {}
                self.current['author'] = attributes['author']
                date = attributes['date']
                # 20040619130027
                y = int(date[:4])
                m = int(date[4:6])
                d = int(date[6:8])
                hh = int(date[8:10])
                mm = int(date[10:12])
                ss = int(date[12:14])
                timestamp = datetime(y, m, d, hh, mm, ss)
                self.current['date'] = timestamp
                self.current['comment'] = ''
                self.current['entries'] = []
            elif name in ['name', 'comment',
                          'add_file', 'add_directory',
                          'modify_file', 'remove_file']:
                self.current_field = []
            elif name == 'move':
                self.old_name = attributes['from']
                self.new_name = attributes['to']

        def endElement(self, name):
            if name == 'patch':
                # Sort the paths to make tests easier
                self.current['entries'].sort(lambda x,y: cmp(x.name, y.name))
                self.changesets.append(Changeset(self.current['name'],
                                                 self.current['date'],
                                                 self.current['author'],
                                                 self.current['comment'],
                                                 self.current['entries']))
                self.current = None
            elif name in ['name', 'comment']:
                self.current[name] = ''.join(self.current_field)
            elif name == 'move':
                entry = ChangesetEntry(self.new_name)
                entry.action_kind = entry.RENAMED
                entry.old_name = self.old_name
                self.current['entries'].append(entry)
            elif name in ['add_file', 'add_directory',
                          'modify_file', 'remove_file']:
                entry = ChangesetEntry(''.join(self.current_field))
                entry.action_kind = { 'add_file': entry.ADDED,
                                      'add_directory': entry.ADDED,
                                      'modify_file': entry.UPDATED,
                                      'remove_file': entry.DELETED,
                                      'rename_file': entry.RENAMED
                                    }[name]

                self.current['entries'].append(entry)

        def characters(self, data):
            self.current_field.append(data)

    handler = DarcsXMLChangesHandler()
    parseString(changes.getvalue(), handler)

    changesets = handler.changesets
    
    # sort changeset by date
    changesets.sort(lambda x, y: cmp(x.date, y.date))

    return changesets

    
class DarcsWorkingDir(UpdatableSourceWorkingDir,SyncronizableTargetWorkingDir):
    """
    A working directory under ``darcs``.
    """

    ## UpdatableSourceWorkingDir
    
    def getUpstreamChangesets(self, root, sincerev=None):
        """
        Do the actual work of fetching the upstream changeset.
        """

        from datetime import datetime
        from time import strptime
        from changes import Changeset
        
        c = SystemCommand(working_dir=root,
                          command="TZ=UTC darcs pull --dry-run")
        output = c(output=True)

        l = output.readline()
        while l and not l.startswith('Would pull the following changes:'):
            l = output.readline()

        changesets = []
        
        ## Sat Jul 17 01:22:08 CEST 2004  lele@nautilus
        ##   * Refix _getUpstreamChangesets for darcs

        l = output.readline()
        while not l.startswith('Making no changes:  this is a dry run.'):
            date,author = l.split('  ')
            y,m,d,hh,mm,ss,d1,d2,d3 = strptime(date, "%a %b %d %H:%M:%S %Z %Y")
            date = datetime(y,m,d,hh,mm,ss)
            author = author[:-1]
            l = output.readline()
            assert l.startswith('  * ')
            name = l[4:-1]
            
            changelog = []
            l = output.readline()
            while l.startswith(' '):
                changelog.append(l.strip())
                l = output.readline()

            changesets.append(Changeset(name,date,author,' '.join(changelog)))
            
            while not l.strip():
                l = output.readline()

        return changesets
    
    def _applyChangeset(self, root, changeset, logger=None):
        """
        Do the actual work of applying the changeset to the working copy.
        """

        c = SystemCommand(working_dir=root,
                          command="darcs pull --all --patches=%(patch)s")
        output = c(output=True, patch=repr(changeset.revision))

        c = SystemCommand(working_dir=root,
                          command="darcs changes --last=1 --xml-output --summ")
        last = changesets_from_darcschanges(c(output=True))
        changeset.entries.extend(last[0].entries)

    def _checkoutUpstreamRevision(self, basedir, repository, module, revision,
                                  subdir=None, logger=None):
        """
        Concretely do the checkout of the upstream revision.
        """

        from os.path import join, exists, split
        
        if not subdir:
            subdir = split(module)[1]
            
        wdir = join(basedir, subdir)
        if not exists(join(wdir, '_darcs')):
            dget = SystemCommand(working_dir=basedir,
                                 command="darcs get --partial --verbose"
                                         " %(tag)s '%(repository)s' %(subdir)s")
            
            dget(output=True, repository=repository,
                 tag=revision<>'HEAD' and '--tag=%s' % repr(revision) or '',
                 subdir=subdir)
            if dget.exit_status:
                raise TargetInitializationFailure(
                    "'darcs get' returned status %s" % dget.exit_status)

        c = SystemCommand(working_dir=wdir,
                          command="darcs changes --last=1 --xml-output")
        last = changesets_from_darcschanges(c(output=True))
        
        return last[0].revision

    
    ## SyncronizableTargetWorkingDir
   
    def _addEntry(self, root, entry):
        """
        Add a new entry.
        """

        c = SystemCommand(working_dir=root,
                          command="darcs add --case-ok --not-recursive"
                                  " --standard-verbosity %(entry)s")
        c(entry=entry)

    def _commit(self,root, date, author, remark, changelog=None, entries=None):
        """
        Commit the changeset.
        """

        c = DarcsRecord(working_dir=root)

        if entries:
            entries = ' '.join(entries)
        else:
            entries = '.'
            
        c(output=True, date=date, patchname=remark,
          logmessage=changelog, author=author, entries=entries)
        
    def _removeEntry(self, root, entry):
        """
        Remove an entry.
        """

        c = SystemCommand(working_dir=root,
                          command="darcs remove --standard-verbosity"
                                  " %(entry)s")
        c(entry=entry)

    def _renameEntry(self, root, oldentry, newentry):
        """
        Rename an entry.
        """

        c = SystemCommand(working_dir=root,
                          command="darcs mv --standard-verbosity"
                                  " %(old)s %(new)s")
        c(old=oldentry, new=newentry)

    def _initializeWorkingDir(self, root, module):
        """
        Execute `darcs initialize`.
        """
        
        c = SystemCommand(working_dir=root, command="darcs initialize")
        c(output=True)

        if c.exit_status:
            raise TargetInitializationFailure(
                "'darcs initialize' returned status %s" % c.exit_status)
        else:
            c = SystemCommand(working_dir=root,
                              command="darcs add --case-ok --recursive"
                                      " --standard-verbosity %(entry)s")
            c(entry=module)

