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
from target import SyncronizableTargetWorkingDir


class DarcsInitialize(SystemCommand):
    COMMAND = "darcs initialize"


class DarcsRecord(SystemCommand):
    COMMAND = "darcs record --all --look-for-adds --author=%(author)s --logfile=%(logfile)s"

    def __call__(self, output=None, dry_run=False, patchname=None, **kwargs):
        logfile = kwargs.get('logfile')
        if not logfile:
            from tempfile import NamedTemporaryFile

            log = NamedTemporaryFile(bufsize=0)
            print >>log, patchname

            logmessage = kwargs.get('logmessage')
            if logmessage:
                print >>log, logmessage
            
            kwargs['logfile'] = log.name
            
        return SystemCommand.__call__(self, output=output,
                                      dry_run=dry_run, 
                                      **kwargs)


class DarcsMv(SystemCommand):
    COMMAND = "darcs mv --standard-verbosity %(old)s %(new)s"


class DarcsRemove(SystemCommand):
    COMMAND = "darcs remove --standard-verbosity %(entry)s"


class DarcsAdd(SystemCommand):
    COMMAND = "darcs add --not-recursive --standard-verbosity %(entry)s"


class DarcsTag(SystemCommand):
    COMMAND = "darcs tag --standard-verbosity --patch-name='%(tagname)s'"


class DarcsChanges(SystemCommand):
    COMMAND = "darcs changes --from-tag=tagname --xml-output --summary"


class DarcsWorkingDir(UpdatableSourceWorkingDir,SyncronizableTargetWorkingDir):
    """
    A working directory under ``darcs``.
    """
    
    ## UpdatableSourceWorkingDir
    
    def _getUpstreamChangesets(self, root):
        """
        Do the actual work of fetching the upstream changeset.
        
        This is different from the other VC mechanisms: here we want
        register with the target the changes we submitted to this
        repository to be sent back to upstream. Since we may want to
        regroup the various patchsets into a single one, we first
        manually pull here what we wanna send, then the sync will replay 
        the changes of all new changesets.
        
        So, here we actually list the changes after the last tag, not
        those pending on the other side.
        """

        tagname = self._getLastTag(root)
        
        c = DarcsChanges(working_dir=root)
        changes = c(output=True)

        changesets = self.__parseDarcsChanges(changes)

        if changesets:
            self._createTag(root,
                            'Sent %d patchsets upstream' % len(changesets))

        return changesets
    
    def __parseDarcsChanges(self, changes):
        from xml.sax import parseString
        from xml.sax.handler import ContentHandler
        from changes import ChangesetEntry, Changeset
        
        class DarcsXMLChangesHandler(ContentHandler):
            def __init__(self):
                self.changesets = []
                self.current = None
                self.current_field = []

            def startElement(self, name, attributes):
                if name == 'patch':
                    self.current = {}
                    self.current['author'] = attributes['author']
                    self.current['date'] = attributes['local_date']
                    self.current['revision'] = attributes['revision']
                    self.current['entries'] = []
                elif name in ['name', 'comment',
                              'add_file', 'add_directory',
                              'modify_file', 'remove_file',
                              'rename_file']:
                    self.current_field = []
                elif name == 'path':
                    self.current_field = []
                    if attributes.has_key('copyfrom-path'):
                        self.current_path_action = (
                            attributes['action'],
                            attributes['copyfrom-path'][1:], # make it relative
                            attributes['copyfrom-rev'])
                    else:
                        self.current_path_action = attributes['action']

            def endElement(self, name):
                if name == 'patch':
                    # Sort the paths to make tests easier
                    self.current['entries'].sort()
                    self.changesets.append(Changeset(self.current['name'],
                                                     self.current['date'],
                                                     self.current['author'],
                                                     self.current['comment'],
                                                     self.current['entries']))
                    self.current = None
                elif name in ['name', 'comment']:
                    self.current[name] = ''.join(self.current_field)
                elif name in ['add_file', 'add_directory',
                              'modify_file', 'remove_file',
                              'rename_file']:
                    entry = ChangesetEntry(''.join(self.current_field))
                    entry.action_kind = { 'add_file': entry.ADDED,
                                          'add_directory': entry.ADDED,
                                          'modify_file': entry.MODIFIED,
                                          'remove_file': entry.REMOVED,
                                          'rename_file': entry.RENAMED
                                        }[name]

                    self.current['entries'].append(entry)

            def characters(self, data):
                self.current_field.append(data)
        
        handler = DarcsXMLChangesHandler()
        parseString(changes.getvalue(), handler)
        return handler.changesets
        
    def _applyChangeset(self, root, changeset):
        """
        Do the actual work of applying the changeset to the working copy.

        The changeset is already applied, so this is a do nothing method.
        """

        return
    
    ## SyncronizableTargetWorkingDir

    def _replayChangeset(self, root, changeset):
        """
        Do nothing except for renames, as darcs will do the right
        thing on disappeared and added files.
        """

        for e in changeset.entries:
            if e.action_kind == e.RENAMED:
                self._renameEntry(root, e.old_name, e.name)
    
    def _addEntry(self, root, entry):
        """
        Add a new entry, maybe registering the directory as well.
        """

        c = DarcsAdd(working_dir=root)
        c(entry=entry)

    def _commit(self, root, author, remark, changelog=None, entries=None):
        """
        Commit the changeset.
        """

        c = DarcsRecord(working_dir=root)
        c(output=True, patchname=remark, logmessage=changelog, author=author)
        
    def _removeEntry(self, root, entry):
        """
        Remove an entry.
        """

        c = DarcsRemove(working_dir=root)
        c(entry=entry)

    def _renameEntry(self, root, oldentry, newentry):
        """
        Rename an entry.
        """

        c = DarcsMv(working_dir=root)
        c(old=oldentry, new=newentry)

    def initializeNewWorkingDir(self, root, repository, revision):
        """
        Initialize the new repository and create a tag.
        """
        
        SyncronizableTargetWorkingDir.initializeNewWorkingDir(self,
                                                              root,
                                                              repository,
                                                              revision)
        self._createTag(root, 'Upstream revision %s' % revision)

    def _createTag(self, root, tagname):
        """
        Tag the current situation and remember this as the *last tag*.
        """

        from os.path import join, exists
        
        c = DarcsTag(working_dir=root)
        c(tagname=tagname)
        
        fname = join(root, '_darcs', 'last-sync-tag')
        f = open(fname, 'w')
        f.write(tagname)
        f.close()
        
    def _getLastTag(self, root):
        """
        Return the name of the last emitted tag, if any, otherwise None.
        """
        
        from os.path import join, exists
        
        fname = join(root, '_darcs', 'last-sync-tag')
        if exists(fname):
            f = open(fname)
            tagname = f.read()
            f.close()
            
            return tagname

    def _initializeWorkingDir(self, root):
        """
        Execute `darcs initialize`.
        """
        
        c = DarcsInitialize(working_dir=root)
        c(output=True)

