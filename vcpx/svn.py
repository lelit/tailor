#! /usr/bin/python
# -*- mode: python; coding: utf-8 -*-
# :Progetto: vcpx -- Subversion details
# :Creato:   ven 18 giu 2004 15:00:52 CEST
# :Autore:   Lele Gaifax <lele@nautilus.homeip.net>
#

"""
This module contains supporting classes for Subversion.
"""

__docformat__ = 'reStructuredText'

from shwrap import SystemCommand
from source import UpdatableSourceWorkingDir, ChangesetApplicationFailure
from target import SyncronizableTargetWorkingDir, TargetInitializationFailure


class SvnUpdate(SystemCommand):
    COMMAND = "svn update --revision %(revision)s %(entry)s"


class SvnInfo(SystemCommand):
    COMMAND = "LANG= svn info %(entry)s"

    def __call__(self, output=None, dry_run=False, **kwargs):
        output = SystemCommand.__call__(self, output=True,
                                        dry_run=dry_run,
                                        **kwargs)
        res = {}
        for l in output:
            l = l[:-1]
            if l:
                key, value = l.split(':', 1)
                res[key] = value[1:]
        return res

                 
class SvnPropGet(SystemCommand):
    COMMAND = "svn propget %(property)s %(entry)s"

    
class SvnPropSet(SystemCommand):
    COMMAND = "svn propset --quiet %(property)s %(value)s %(entry)s"


class SvnLog(SystemCommand):
    COMMAND = "TZ=UTC svn log %(quiet)s %(xml)s --revision %(startrev)s:%(endrev)s %(entry)s 2>&1"
    
    def __call__(self, output=None, dry_run=False, **kwargs):
        quiet = kwargs.get('quiet', True)
        if quiet == True:
            kwargs['quiet'] = '--quiet'
        elif quiet == False:
            kwargs['quiet'] = ''
            
        xml = kwargs.get('xml', False)
        if xml:
            kwargs['xml'] = '--xml'
            output = True
        else:
            kwargs['xml'] = ''

        startrev = kwargs.get('startrev')
        if not startrev:
            kwargs['startrev'] = 'BASE'

        endrev = kwargs.get('endrev')
        if not endrev:
            kwargs['endrev'] = 'HEAD'

        output = SystemCommand.__call__(self, output=output,
                                        dry_run=dry_run, **kwargs)

        if xml:
            # parse the output and return the result
            pass

        return output


class SvnCommit(SystemCommand):
    COMMAND = "svn commit --quiet --file %(logfile)s %(entries)s"

    def __call__(self, output=None, dry_run=False, **kwargs):
        logfile = kwargs.get('logfile')
        if not logfile:
            from tempfile import NamedTemporaryFile

            log = NamedTemporaryFile(bufsize=0)
            logmessage = kwargs.get('logmessage')
            if logmessage:
                log.write(logmessage)
            
            kwargs['logfile'] = log.name
        
        return SystemCommand.__call__(self, output=output,
                                      dry_run=dry_run, **kwargs)


class SvnAdd(SystemCommand):
    COMMAND = "svn add --quiet --no-auto-props --non-recursive %(entry)s"

        
class SvnRemove(SystemCommand):
    COMMAND = "svn remove --quiet --force %(entry)s"


class SvnMv(SystemCommand):
    COMMAND = "svn mv --quiet %(old)s %(new)s"

    
class SvnCheckout(SystemCommand):
    COMMAND = "svn co --revision %(revision)s %(repository)s/%(module)s %(wc)s"

def changesets_from_svnlog(log, url):
    from xml.sax import parseString
    from xml.sax.handler import ContentHandler
    from changes import ChangesetEntry, Changeset
    from datetime import datetime

    def get_entry_from_path(path, url=url):
        # Given the repository url of this wc, say
        #   "http://server/plone/CMFPlone/branches/Plone-2_0-branch"
        # extract the "entry" portion (a relative path) from what
        # svn log --xml says, ie
        #   "/CMFPlone/branches/Plone-2_0-branch/tests/PloneTestCase.py"
        # that is to say "tests/PloneTestCase.py"

        from os.path import split

        prefix = split(path)[0]
        while prefix:
            if url.endswith(prefix):
                return path[len(prefix)+1:]

            prefix = split(prefix)[0]

        # The path is outside our tracked tree...
        return None

    class SvnXMLLogHandler(ContentHandler):
        def __init__(self):
            self.changesets = []
            self.current = None
            self.current_field = []
            self.renamed = {}
            
        def startElement(self, name, attributes):
            if name == 'logentry':
                self.current = {}
                self.current['revision'] = attributes['revision']
                self.current['entries'] = []
            elif name in ['author', 'date', 'msg']:
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
            if name == 'logentry':
                # Sort the paths to make tests easier
                self.current['entries'].sort(lambda a,b: cmp(a.name, b.name))

                # Eliminate renamed entries
                entries = [e for e in self.current['entries']
                           if e.name not in self.renamed]
                
                svndate = self.current['date']
                # 2004-04-16T17:12:48.000000Z
                y,m,d = map(int, svndate[:10].split('-'))
                hh,mm,ss = map(int, svndate[11:19].split(':'))
                ms = int(svndate[20:-1])
                timestamp = datetime(y, m, d, hh, mm, ss, ms)
                
                changeset = Changeset(self.current['revision'],
                                      timestamp,
                                      self.current['author'],
                                      self.current['msg'],
                                      entries)
                self.changesets.append(changeset)
                self.current = None
            elif name in ['author', 'date', 'msg']:
                self.current[name] = ''.join(self.current_field)
            elif name == 'path':
                path = ''.join(self.current_field)[1:]
                entrypath = get_entry_from_path(path)
                if entrypath:
                    entry = ChangesetEntry(entrypath)

                    if type(self.current_path_action) == type( () ):
                        old = get_entry_from_path(self.current_path_action[1])
                        if old:
                            entry.action_kind = entry.RENAMED
                            entry.old_name = old
                            self.renamed[entry.old_name] = True
                        else:
                            entry.action_kind = entry.ADDED
                    else:
                        entry.action_kind = self.current_path_action

                    self.current['entries'].append(entry)

                    
        def characters(self, data):
            self.current_field.append(data)


    handler = SvnXMLLogHandler()
    parseString(log.getvalue(), handler)
    return handler.changesets


class SvnWorkingDir(UpdatableSourceWorkingDir, SyncronizableTargetWorkingDir):

    ## UpdatableSourceWorkingDir

    def getUpstreamChangesets(self, root, sincerev=None):
        if sincerev:
            sincerev = int(sincerev)
        else:
            sincerev = 0
            
        svnlog = SvnLog(working_dir=root)
        log = svnlog(quiet='--verbose', output=True, xml=True,
                     startrev=sincerev+1, entry='.')
        
        if svnlog.exit_status:
            return []
        
        url = SvnInfo(working_dir=root)(entry='.')['URL']
        
        return self.__parseSvnLog(log, url)

    def __parseSvnLog(self, log, url):
        """Return an object representation of the ``svn log`` thru HEAD."""

        return changesets_from_svnlog(log, url)
    
    def _applyChangeset(self, root, changeset, logger=None):
        svnup = SvnUpdate(working_dir=root)
        out = svnup(output=True, entry='.', revision=changeset.revision)

        if svnup.exit_status:
            raise ChangesetApplicationFailure(
                "'svn update' returned status %s" % svnup.exit_status)
            
        if logger: logger.info("%s updated to %s" % (
            ','.join([e.name for e in changeset.entries]),
            changeset.revision))
        
        result = []
        for line in out:
            if len(line)>2 and line[0] == 'C' and line[1] == ' ':
                logger.warn("Conflict after 'svn update': '%s'" % line)
                result.append(line[2:-1])
            
        return result
        
    def _checkoutUpstreamRevision(self, basedir, repository, module, revision,
                                  subdir=None, logger=None):
        """
        Concretely do the checkout of the upstream revision.
        """
        
        from os.path import join, exists, split
        
        if not subdir:
            subdir = split(module)[1]
            
        wdir = join(basedir, subdir)

        if not exists(wdir):
            svnco = SvnCheckout(working_dir=basedir)
            svnco(output=True, repository=repository, module=module,
                  wc=subdir, revision=revision)
            if svnco.exit_status:
                raise TargetInitializationFailure(
                    "'svn checkout' returned status %s" % svnco.exit_status)

        actual = SvnInfo(working_dir=wdir)(entry='.')['Revision']

        if logger: logger.info("working copy up to svn revision %s",
                               actual)
        
        return actual 
    
    ## SyncronizableTargetWorkingDir

    def _addEntry(self, root, entry):
        """
        Add a new entry.
        """

        c = SvnAdd(working_dir=root)
        c(entry=entry)

    def _commit(self,root, date, author, remark, changelog=None, entries=None):
        """
        Commit the changeset.
        """

        c = SvnCommit(working_dir=root)
        
        logmessage = "%s\nOriginal author: %s\nDate: %s" % (remark, author,
                                                            date)
        if changelog:
            logmessage = logmessage + '\n\n' + changelog
            
        if entries:
            entries = ' '.join(entries)
        else:
            entries = '.'
            
        c(logmessage=logmessage, entries=entries)
        
    def _removeEntry(self, root, entry):
        """
        Remove an entry.
        """

        c = SvnRemove(working_dir=root)
        c(entry=entry)

    def _renameEntry(self, root, oldentry, newentry):
        """
        Rename an entry.
        """

        c = SvnMv(working_dir=root)
        c(old=oldentry, new=newentry)

    def _initializeWorkingDir(self, root, module, addentry=None):
        """
        Add the given directory to an already existing svn working tree.
        """

        from os.path import exists, join

        if not exists(join(root, '.svn')):
            raise TargetInitializationFailure("'%s' should already be under SVN" % root)

        SyncronizableTargetWorkingDir._initializeWorkingDir(self, root, module,
                                                            SvnAdd)
