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

from shwrap import ExternalCommand, PIPE, STDOUT, ReopenableNamedTemporaryFile
from source import UpdatableSourceWorkingDir, \
     ChangesetApplicationFailure, GetUpstreamChangesetsFailure
from target import SyncronizableTargetWorkingDir, TargetInitializationFailure

SVN_CMD = "svn"
SVNADMIN_CMD = "svnadmin"

def changesets_from_svnlog(log, repository, module):
    from xml.sax import parseString
    from xml.sax.handler import ContentHandler
    from changes import ChangesetEntry, Changeset
    from datetime import datetime
    from string import maketrans

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
                                      self.current.get('author'),
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


    # Apparently some (SVN repo contains)/(SVN server dumps) some characters that
    # are illegal in an XML stream. This was the case with Twisted Matrix master
    # repository. To be safe, we replace all of them with a question mark.

    allbadchars = "\x00\x01\x02\x03\x04\x05\x06\x07\x08\x09\x0B\x0C\x0E\x0F\x10\x11" \
                  "\x12\x13\x14\x15\x16\x17\x18\x19\x1A\x1B\x1C\x1D\x1E\x1F\x7f"
    tt = maketrans(allbadchars, "?"*len(allbadchars))
    handler = SvnXMLLogHandler()
    parseString(log.read().translate(tt), handler)
    return handler.changesets


class SvnWorkingDir(UpdatableSourceWorkingDir, SyncronizableTargetWorkingDir):

    ## UpdatableSourceWorkingDir

    def _getUpstreamChangesets(self, root, repository, module, sincerev=None):
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

        return changesets_from_svnlog(log, repository, module)

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

        if revision == 'INITIAL':
            initial = True
            cmd = [SVN_CMD, "log", "--verbose", "--xml", "--limit", "1",
                   "--revision", "1:HEAD"]
            svnlog = ExternalCommand(cwd=wdir, command=cmd)
            output = svnlog.execute("%s%s" % (repository, module), stdout=PIPE)

            if svnlog.exit_status:
                raise ChangesetApplicationFailure(
                    "%s returned status %d saying \"%s\"" %
                    (str(changes), changes.exit_status, output.read()))

            csets = changesets_from_svnlog(output, repository, module)
            revision = escape(csets[0].revision)
        else:
            initial = False

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

        if not initial:
            cmd = [SVN_CMD, "log", "--verbose", "--xml", "--revision", revision]
            svnlog = ExternalCommand(cwd=wdir, command=cmd)
            output = svnlog.execute(stdout=PIPE)

            if svnlog.exit_status:
                raise ChangesetApplicationFailure(
                    "%s returned status %d saying \"%s\"" %
                    (str(changes), changes.exit_status, output.read()))

            csets = changesets_from_svnlog(output, repository, module)

        last = csets[0]

        if logger: logger.info("working copy up to svn revision %s",
                               last.revision)

        return last

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

        from sys import getdefaultencoding

        encoding = ExternalCommand.FORCE_ENCODING or getdefaultencoding()

        logmessage = []
        if remark:
            logmessage.append(remark.encode(encoding))
        if changelog:
            logmessage.append('')
            logmessage.append(changelog.encode(encoding))
        logmessage.append('')

        # If we cannot use propset, fall back to old behaviour of
        # appending these info to the changelog

        if not self.USE_PROPSET:
            logmessage.append('')
            logmessage.append('Original author: %s' % author.encode(encoding))
            logmessage.append('Date: %s' % date)
            logmessage.append('')

        rontf = ReopenableNamedTemporaryFile('svn', 'tailor')
        log = open(rontf.name, "w")
        log.write('\n'.join(logmessage))
        log.close()

        cmd = [SVN_CMD, "commit", "--quiet", "--file", rontf.name]
        commit = ExternalCommand(cwd=root, command=cmd)

        if not entries:
            entries = ['.']

        commit.execute(entries)

        if self.USE_PROPSET:
            cmd = [SVN_CMD, "propset", "%(propname)s",
                   "--quiet", "--revprop", "-rHEAD"]
            propset = ExternalCommand(cwd=root, command=cmd)

            propset.execute(date.isoformat()+".000000Z", propname='svn:date')
            propset.execute(author, propname='svn:author')

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
            self._removePathnames(root, [oldname])
            self._addPathnames(root, [newname])

    def __createRepository(self, target_repository, target_module):
        """
        Create a local repository.
        """

        assert target_repository.startswith('file:///')

        cmd = [SVNADMIN_CMD, "create", "--fs-type", "fsfs"]
        svnadmin = ExternalCommand(command=cmd)
        svnadmin.execute(target_repository[7:])

        if svnadmin.exit_status:
            raise TargetInitializationFailure("Was not able to create a 'fsfs' "
                                              "svn repository at %r" %
                                              target_repository)

        if target_module and target_module <> '/':
            cmd = [SVN_CMD, "mkdir", "-m",
                   "This directory will host the upstream sources"]
            svnmkdir = ExternalCommand(command=cmd)
            svnmkdir.execute(target_repository + target_module)
            if svnmkdir.exit_status:
                raise TargetInitializationFailure("Was not able to create the "
                                                  "module %r, maybe more than "
                                                  "one level directory?" %
                                                  target_module)

    def _prepareTargetRepository(self, root, target_repository, target_module):
        """
        Check for target repository existence, eventually create it.
        """

        cmd = [SVN_CMD, "info"]
        svninfo = ExternalCommand(command=cmd)
        svninfo.execute(target_repository, stdout=PIPE, stderr=STDOUT)

        if svninfo.exit_status:
            if target_repository.startswith('file:///'):
                self.__createRepository(target_repository, target_module)
            else:
                raise TargetInitializationFailure("%r does not exist and "
                                                  "cannot be created since "
                                                  "it's not a local (file:///) "
                                                  "repository" %
                                                  target_repository)

    def _prepareWorkingDirectory(self, root, target_repository, target_module):
        """
        Checkout a working copy of the target SVN repository.
        """

        cmd = [SVN_CMD, "co", "--quiet"]
        svnco = ExternalCommand(command=cmd)
        svnco.execute(target_repository + target_module, root)

    def _initializeWorkingDir(self, root, source_repository, source_module,
                              subdir):
        """
        Add the given directory to an already existing svn working tree.
        """

        from os.path import exists, join

        if not exists(join(root, '.svn')):
            raise TargetInitializationFailure("'%s' needs to be an SVN working copy already under SVN" % root)

        SyncronizableTargetWorkingDir._initializeWorkingDir(self, root,
                                                            source_repository,
                                                            source_module,
                                                            subdir)
