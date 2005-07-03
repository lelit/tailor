# -*- mode: python; coding: utf-8 -*-
# :Progetto: vcpx -- Subversion details
# :Creato:   ven 18 giu 2004 15:00:52 CEST
# :Autore:   Lele Gaifax <lele@nautilus.homeip.net>
# :Licenza:  GNU General Public License
#

"""
This module contains supporting classes for Subversion.
"""

__docformat__ = 'reStructuredText'

from shwrap import ExternalCommand, PIPE, ReopenableNamedTemporaryFile
from source import UpdatableSourceWorkingDir, \
     ChangesetApplicationFailure, GetUpstreamChangesetsFailure
from target import SyncronizableTargetWorkingDir, TargetInitializationFailure

SVN_CMD = "svn"

def changesets_from_svnlog(log, url, repository, module):
    from xml.sax import parse
    from xml.sax.handler import ContentHandler
    from changes import ChangesetEntry, Changeset
    from datetime import datetime

    def get_entry_from_path(path, module=module):
        # Given the repository url of this wc, say
        #   "http://server/plone/CMFPlone/branches/Plone-2_0-branch"
        # extract the "entry" portion (a relative path) from what
        # svn log --xml says, ie
        #   "/CMFPlone/branches/Plone-2_0-branch/tests/PloneTestCase.py"
        # that is to say "tests/PloneTestCase.py"

        if path.startswith(module):
            relative = path[len(module):]
            if relative.startswith('/'):
                return relative[1:]
            else:
                return relative
        
        # The path is outside our tracked tree...
        return None
        
    class SvnXMLLogHandler(ContentHandler):
        # Map between svn action and tailor's.
        # NB: 'R', in svn parlance, means REPLACED, something other
        # system may view as a simpler ADD, taking the following as
        # the most common idiom::
        #
        #   # Rename the old file with a better name
        #   $ svn mv somefile nicer-name-scheme.py
        #
        #   # Be nice with lazy users
        #   $ echo "exec nicer-name-scheme.py" > somefile
        #
        #   # Add the wrapper with the old name
        #   $ svn add somefile
        #
        #   $ svn commit -m "Longer name for somefile"

        ACTIONSMAP = {'R': 'R', # will be ChangesetEntry.ADDED
                      'M': ChangesetEntry.UPDATED,
                      'A': ChangesetEntry.ADDED,
                      'D': ChangesetEntry.DELETED}
        
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
                        attributes['copyfrom-path'],
                        attributes['copyfrom-rev'])
                else:
                    self.current_path_action = attributes['action']

        def endElement(self, name):
            if name == 'logentry':
                # Sort the paths to make tests easier
                self.current['entries'].sort(lambda a,b: cmp(a.name, b.name))

                # Eliminate "useless" entries: SVN does not have atomic
                # renames, but rather uses a ADD+RM duo.
                #
                # So cycle over all entries of this patch, discarding
                # the deletion of files that were actually renamed, and
                # at the same time change related entry from ADDED to
                # RENAMED.

                mv_or_cp = {}
                for e in self.current['entries']:
                    if e.action_kind == e.ADDED and e.old_name is not None:
                        mv_or_cp[e.old_name] = e
                
                entries = []
                for e in self.current['entries']:
                    if e.action_kind==e.DELETED and mv_or_cp.has_key(e.name):
                        mv_or_cp[e.name].action_kind = e.RENAMED
                    elif e.action_kind=='R':
                        if mv_or_cp.has_key(e.name):
                            mv_or_cp[e.name].action_kind = e.RENAMED
                        e.action_kind = e.ADDED
                        entries.append(e)
                    else:
                        entries.append(e)                        
                
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
                path = ''.join(self.current_field)
                entrypath = get_entry_from_path(path)
                if entrypath:
                    entry = ChangesetEntry(entrypath)

                    if type(self.current_path_action) == type( () ):
                        old = get_entry_from_path(self.current_path_action[1])
                        if old:
                            entry.action_kind = self.ACTIONSMAP[self.current_path_action[0]]
                            entry.old_name = old
                            self.renamed[entry.old_name] = True
                        else:
                            entry.action_kind = entry.ADDED
                    else:
                        entry.action_kind = self.ACTIONSMAP[self.current_path_action]

                    self.current['entries'].append(entry)

                    
        def characters(self, data):
            self.current_field.append(data)


    handler = SvnXMLLogHandler()
    parse(log, handler)
    return handler.changesets


class SvnWorkingDir(UpdatableSourceWorkingDir, SyncronizableTargetWorkingDir):

    ## UpdatableSourceWorkingDir

    def getUpstreamChangesets(self, root, repository, module, sincerev=None):
        if sincerev:
            sincerev = int(sincerev)
        else:
            sincerev = 0

        cmd = [SVN_CMD, "log", "--verbose", "--xml",
               "--revision", "%d:HEAD" % (sincerev+1)]
        svnlog = ExternalCommand(cwd=root, command=cmd)
        log = svnlog.execute('.', stdout=PIPE, TZ='UTC')
        
        if svnlog.exit_status:
            return []

        cmd = [SVN_CMD, "info"]
        svninfo = ExternalCommand(cwd=root, command=cmd)
        output = svninfo.execute('.', stdout=PIPE, LANG='')

        if svninfo.exit_status:
            raise GetUpstreamChangesetsFailure(
                "%s returned status %d" % (str(svninfo), svninfo.exit_status))

        info = {}
        for l in output:
            l = l[:-1]
            if l:
                key, value = l.split(':', 1)
                info[key] = value[1:]
        
        return self.__parseSvnLog(log, info['URL'], repository, module)

    def __parseSvnLog(self, log, url, repository, module):
        """Return an object representation of the ``svn log`` thru HEAD."""

        return changesets_from_svnlog(log, url, repository, module)
    
    def _applyChangeset(self, root, changeset, logger=None):
        cmd = [SVN_CMD, "update", "--revision", changeset.revision, "."]
        svnup = ExternalCommand(cwd=root, command=cmd)
        out = svnup.execute(stdout=PIPE)

        if svnup.exit_status:
            raise ChangesetApplicationFailure(
                "%s returned status %s" % (str(svnup), svnup.exit_status))
            
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
                                  subdir=None, logger=None, **kwargs):
        """
        Concretely do the checkout of the upstream revision.
        """
        
        from os.path import join, exists
        
        wdir = join(basedir, subdir)

        if not exists(join(wdir, '.svn')):
            if logger: logger.info("checking out a working copy")
            cmd = [SVN_CMD, "co", "--quiet", "--revision", revision]
            svnco = ExternalCommand(cwd=basedir, command=cmd)
            svnco.execute("%s%s" % (repository, module), subdir)
            if svnco.exit_status:
                raise TargetInitializationFailure(
                    "%s returned status %s" % (str(svnco), svnco.exit_status))
        else:
            if logger: logger.info("%s already exists, assuming it's a svn working dir" % wdir)

        cmd = [SVN_CMD, "info"]
        svninfo = ExternalCommand(cwd=wdir, command=cmd)
        output = svninfo.execute('.', stdout=PIPE, LANG='')

        if svninfo.exit_status:
            raise GetUpstreamChangesetsFailure(
                "%s returned status %d" % (str(svninfo), svninfo.exit_status))

        info = {}
        for l in output:
            l = l[:-1]
            if l:
                key, value = l.split(':', 1)
                info[key] = value[1:]

        actual = info['Revision']
        
        if logger: logger.info("working copy up to svn revision %s",
                               actual)
        
        return actual 
    
    ## SyncronizableTargetWorkingDir

    def _addPathnames(self, root, names):
        """
        Add some new filesystem objects.
        """

        cmd = [SVN_CMD, "add", "--quiet", "--no-auto-props", "--non-recursive"]
        ExternalCommand(cwd=root, command=cmd).execute(names)

    def _getCommitEntries(self, changeset):
        """
        Extract the names of the entries for the commit phase.  Since SVN
        handles "rename" operations as "remove+add", both entries must be
        committed.
        """

        entries = SyncronizableTargetWorkingDir._getCommitEntries(self,
                                                                  changeset)
        entries.extend([e.old_name for e in changeset.renamedEntries()])

        return entries
        
    def _commit(self,root, date, author, remark, changelog=None, entries=None):
        """
        Commit the changeset.
        """

        rontf = ReopenableNamedTemporaryFile('svn', 'tailor')
        log = open(rontf.name, "w")
        log.write(remark)
        if changelog:
            log.write('\n')
            log.write(changelog)
        log.write("\n\nOriginal author: %s\nDate: %s\n" % (author, date))
        log.close()            

        cmd = [SVN_CMD, "commit", "--quiet", "--file", rontf.name]
        commit = ExternalCommand(cwd=root, command=cmd)
        
        if not entries:
            entries = ['.']
            
        commit.execute(entries)
        
    def _removePathnames(self, root, names):
        """
        Remove some filesystem objects.
        """

        cmd = [SVN_CMD, "remove", "--quiet", "--force"]
        remove = ExternalCommand(cwd=root, command=cmd)
        remove.execute(names)

    def _renamePathname(self, root, oldname, newname):
        """
        Rename a filesystem object.
        """

        cmd = [SVN_CMD, "mv", "--quiet"]
        move = ExternalCommand(cwd=root, command=cmd)
        move.execute(oldname, newname)
        if move.exit_status:
            # Subversion does not seem to allow
            #   $ mv a.txt b.txt
            #   $ svn mv a.txt b.txt
            # Here we are in this situation, since upstream VCS already
            # moved the item. OTOH, svn really treats "mv" as "cp+rm",
            # so we do the same here
            self._removePathnames(root, oldname)
            self._addPathnames(root, newname)

    def _initializeWorkingDir(self, root, repository, module, subdir):
        """
        Add the given directory to an already existing svn working tree.
        """

        from os.path import exists, join

        if not exists(join(root, '.svn')):
            raise TargetInitializationFailure("'%s' needs to be an SVN working copy already under SVN" % root)

        SyncronizableTargetWorkingDir._initializeWorkingDir(self, root,
                                                            repository, module,
                                                            subdir)
