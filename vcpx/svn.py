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
from config import ConfigurationError

def changesets_from_svnlog(log, repository, module):
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
            self.external_copies = []

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

                # When copying a directory from another location in the
                # repository (outside the tracked tree), SVN will report files
                # below this dir that are not being committed as being
                # removed.

                # We thus need to change the action_kind for all entries
                # that are below a dir that was "copyfrom" from a path
                # outside of this module:
                #  D -> Remove entry completely (it's not going to be in here)
                #  (M,A,R) -> A

                mv_or_cp = {}
                for e in self.current['entries']:
                    if e.action_kind == e.ADDED and e.old_name is not None:
                        mv_or_cp[e.old_name] = e

                def parent_was_copied_externally(n):
                    for p in self.external_copies:
                        if n.startswith(p):
                            return True
                    return False

                entries = []
                for e in self.current['entries']:
                    if e.action_kind==e.DELETED and mv_or_cp.has_key(e.name):
                        mv_or_cp[e.name].action_kind = e.RENAMED
                    elif e.action_kind=='R':
                        # In svn parlance, 'R' means Replaced: a typical
                        # scenario is
                        #   $ svn mv a.txt b.txt
                        #   $ touch a.txt
                        #   $ svn add a.txt
                        if mv_or_cp.has_key(e.name):
                            mv_or_cp[e.name].action_kind = e.RENAMED
                        e.action_kind = e.ADDED
                        entries.append(e)
                    elif parent_was_copied_externally(e.name):
                        if e.action_kind != e.DELETED:
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
                            self.external_copies.append(entry.name)
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

    def _getUpstreamChangesets(self, sincerev=None):
        if sincerev:
            sincerev = int(sincerev)
        else:
            sincerev = 0

        cmd = self.repository.command("log", "--verbose", "--xml",
                                      "--revision", "%d:HEAD" % (sincerev+1))
        svnlog = ExternalCommand(cwd=self.basedir, command=cmd)
        log = svnlog.execute('.', stdout=PIPE, TZ='UTC')[0]

        if svnlog.exit_status:
            return []

        if self.repository.filter_badchars:
            from string import maketrans
            from cStringIO import StringIO

            # Apparently some (SVN repo contains)/(SVN server dumps) some
            # characters that are illegal in an XML stream. This was the case
            # with Twisted Matrix master repository. To be safe, we replace
            # all of them with a question mark.

            if isinstance(self.repository.filter_badchars, string):
                allbadchars = self.repository.filter_badchars
            else:
                allbadchars = "\x00\x01\x02\x03\x04\x05\x06\x07\x08\x09" \
                              "\x0B\x0C\x0E\x0F\x10\x11\x12\x13\x14\x15" \
                              "\x16\x17\x18\x19\x1A\x1B\x1C\x1D\x1E\x1F\x7f"

            tt = maketrans(allbadchars, "?"*len(allbadchars))
            log = StringIO(log.read().translate(tt))

        return changesets_from_svnlog(log,
                                      self.repository.repository,
                                      self.repository.module)

    def _applyChangeset(self, changeset):
        from time import sleep

        cmd = self.repository.command("update",
                                      "--revision", changeset.revision, ".")
        svnup = ExternalCommand(cwd=self.basedir, command=cmd)

        retry = 0
        while True:
            out, err = svnup.execute(stdout=PIPE, stderr=PIPE)

            if svnup.exit_status == 1:
                retry += 1
                if retry>3:
                    break
                delay = 2**retry
                self.log_info("%s returned status %s saying %r, "
                              "retrying in %d seconds..." %
                              (str(svnup), svnup.exit_status, err.read(),
                               delay))
                sleep(delay)
            else:
                break

        if svnup.exit_status:
            raise ChangesetApplicationFailure(
                "%s returned status %s saying %r" % (str(svnup),
                                                     svnup.exit_status,
                                                     err.read()))

        self.log_info("%s updated to %s" % (
            ','.join([e.name for e in changeset.entries]),
            changeset.revision))

        result = []
        for line in out:
            if len(line)>2 and line[0] == 'C' and line[1] == ' ':
                self.log_info("Conflict after 'svn update': '%s'" % line)
                result.append(line[2:-1])

        return result

    def _checkoutUpstreamRevision(self, revision):
        """
        Concretely do the checkout of the upstream revision.
        """

        from os.path import join, exists

        # Verify that the we have the root of the repository: do that
        # iterating an "svn ls" over the hierarchy until one fails

        cmd = self.repository.command("ls")
        svnls = ExternalCommand(command=cmd)
        svnls.execute(self.repository.repository)

        lastok = self.repository.repository
        reporoot = lastok[:lastok.rfind('/')]
        while '/' in reporoot:
            svnls.execute(reporoot)
            if svnls.exit_status:
                break
            lastok = reporoot
            reporoot = reporoot[:reporoot.rfind('/')]

        if lastok <> self.repository.repository:
            module = self.repository.repository[len(lastok):]
            module += self.repository.module
            raise ConfigurationError("Non-root svn repository %r. "
                                     "Please specify that as 'repository=%s' "
                                     "and 'module=%s'." %
                                     (self.repository.repository,
                                      lastok, module.rstrip('/')))

        if revision == 'INITIAL':
            initial = True
            cmd = self.repository.command("log", "--verbose", "--xml",
                                          "--limit", "1", "--stop-on-copy",
                                          "--revision", "1:HEAD")
            svnlog = ExternalCommand(command=cmd)
            out, err = svnlog.execute("%s%s" % (self.repository.repository,
                                                self.repository.module),
                                      stdout=PIPE, stderr=PIPE)

            if svnlog.exit_status:
                raise TargetInitializationFailure(
                    "%s returned status %d saying %r" %
                    (str(svnlog), svnlog.exit_status, err.read()))

            csets = changesets_from_svnlog(out,
                                           self.repository.repository,
                                           self.repository.module)
            revision = csets[0].revision
        else:
            initial = False

        if not exists(join(self.basedir, '.svn')):
            self.log_info("checking out a working copy")
            cmd = self.repository.command("co", "--quiet",
                                          "--revision", revision)
            svnco = ExternalCommand(command=cmd)
            out, err = svnco.execute("%s%s" % (self.repository.repository,
                                               self.repository.module),
                                     self.basedir, stdout=PIPE, stderr=PIPE)
            if svnco.exit_status:
                raise TargetInitializationFailure(
                    "%s returned status %s saying %r" % (str(svnco),
                                                         svnco.exit_status,
                                                         err.read()))
        else:
            self.log_info("%s already exists, assuming it's a svn working dir" % self.basedir)

        if not initial:
            if revision=='HEAD':
                revision = 'COMMITTED'
            cmd = self.repository.command("log", "--verbose", "--xml",
                                          "--revision", revision)
            svnlog = ExternalCommand(cwd=self.basedir, command=cmd)
            out, err = svnlog.execute(stdout=PIPE, stderr=PIPE)

            if svnlog.exit_status:
                raise TargetInitializationFailure(
                    "%s returned status %d saying %r" %
                    (str(changes), changes.exit_status, err.read()))

            csets = changesets_from_svnlog(out,
                                           self.repository.repository,
                                           self.repository.module)

        last = csets[0]

        self.log_info("working copy up to svn revision %s" % last.revision)

        return last

    ## SyncronizableTargetWorkingDir

    def _addPathnames(self, names):
        """
        Add some new filesystem objects.
        """

        cmd = self.repository.command("add", "--quiet", "--no-auto-props",
                                      "--non-recursive")
        ExternalCommand(cwd=self.basedir, command=cmd).execute(names)

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

    def _commit(self, date, author, patchname, changelog=None, entries=None):
        """
        Commit the changeset.
        """

        from locale import getpreferredencoding

        encoding = ExternalCommand.FORCE_ENCODING or getpreferredencoding()

        logmessage = []
        if patchname:
            logmessage.append(patchname.encode(encoding))
        if changelog:
            logmessage.append(changelog.encode(encoding))

        # If we cannot use propset, fall back to old behaviour of
        # appending these info to the changelog

        if not self.USE_PROPSET:
            logmessage.append('')
            logmessage.append('Original author: %s' % author.encode(encoding))
            logmessage.append('Date: %s' % date)

        rontf = ReopenableNamedTemporaryFile('svn', 'tailor')
        log = open(rontf.name, "w")
        log.write('\n'.join(logmessage))
        log.close()

        cmd = self.repository.command("commit", "--file", rontf.name)
        commit = ExternalCommand(cwd=self.basedir, command=cmd)

        if not entries:
            entries = ['.']

        out, err = commit.execute(entries, stdout=PIPE, stderr=PIPE, LANG='C')

        if commit.exit_status:
            raise ChangesetApplicationFailure("%s returned status %d saying %r"
                                              % (str(commit),
                                                 commit.exit_status,
                                                 err.read()))
        line = out.readline()
        if not line:
            # svn did not find anything to commit
            return

        while line and not line.startswith('Committed revision '):
            if line <> '\n' and not line.startswith('Sending ') and \
               not line.startswith('Transmitting file data ') and \
               not line.startswith('Adding ') and \
               not line.startswith('Deleting '):
                break
            line = out.readline()

        if not line.startswith('Committed revision '):
            out.seek(0)
            raise ChangesetApplicationFailure("%s wrote unexpected line %r. "
                                              "This the whole output:\n%s" %
                                              (str(commit), line, out.read()))
        revision = line[19:-2]

        if self.USE_PROPSET:
            cmd = self.repository.command("propset", "%(propname)s",
                                          "--quiet", "--revprop",
                                          "--revision", revision)
            propset = ExternalCommand(cwd=self.basedir, command=cmd)

            propset.execute(date.isoformat()+".000000Z", propname='svn:date')
            propset.execute(author.encode(encoding), propname='svn:author')

        cmd = self.repository.command("update", "--quiet",
                                      "--revision", revision)
        ExternalCommand(cwd=self.basedir, command=cmd).execute()

    def _removePathnames(self, names):
        """
        Remove some filesystem objects.
        """

        cmd = self.repository.command("remove", "--quiet", "--force")
        remove = ExternalCommand(cwd=self.basedir, command=cmd)
        remove.execute(names)

    def _renamePathname(self, oldname, newname):
        """
        Rename a filesystem object.
        """

        cmd = self.repository.command("mv", "--quiet")
        move = ExternalCommand(cwd=self.basedir, command=cmd)
        move.execute(oldname, newname)
        if move.exit_status:
            # Subversion does not seem to allow
            #   $ mv a.txt b.txt
            #   $ svn mv a.txt b.txt
            # Here we are in this situation, since upstream VCS already
            # moved the item. OTOH, svn really treats "mv" as "cp+rm",
            # so we do the same here
            self._removePathnames([oldname])
            self._addPathnames([newname])

    def __createRepository(self, target_repository, target_module):
        """
        Create a local repository.
        """

        from os.path import join
        from sys import platform

        assert target_repository.startswith('file:///')
        repodir = target_repository[7:]
        cmd = self.repository.command("create", "--fs-type", "fsfs",
                                      svnadmin=True)
        svnadmin = ExternalCommand(command=cmd)
        svnadmin.execute(repodir)

        if svnadmin.exit_status:
            raise TargetInitializationFailure("Was not able to create a 'fsfs' "
                                              "svn repository at %r" %
                                              target_repository)
        if self.USE_PROPSET:
            hookname = join(repodir, 'hooks', 'pre-revprop-change')
            if platform == 'win32':
                hookname += '.bat'
            prehook = open(hookname, 'wU')
            if platform <> 'win32':
                prehook.write('#!/bin/sh\n')
            prehook.write('exit 0\n')
            prehook.close()
            if platform <> 'win32':
                from os import chmod
                chmod(hookname, 0755)

        if target_module and target_module <> '/':
            cmd = self.repository.command("mkdir", "-m",
                                          "This directory will host the "
                                          "upstream sources")
            svnmkdir = ExternalCommand(command=cmd)
            svnmkdir.execute(target_repository + target_module)
            if svnmkdir.exit_status:
                raise TargetInitializationFailure("Was not able to create the "
                                                  "module %r, maybe more than "
                                                  "one level directory?" %
                                                  target_module)

    def _prepareTargetRepository(self):
        """
        Check for target repository existence, eventually create it.
        """

        if not self.repository.repository:
            return

        # Verify the existence of repository by listing its root
        cmd = self.repository.command("ls")
        svnls = ExternalCommand(command=cmd)
        svnls.execute(self.repository.repository)

        if svnls.exit_status:
            if self.repository.repository.startswith('file:///'):
                self.__createRepository(self.repository.repository,
                                        self.repository.module)
            else:
                raise TargetInitializationFailure("%r does not exist and "
                                                  "cannot be created since "
                                                  "it's not a local (file:///) "
                                                  "repository" %
                                                  self.repository.repository)

    def _prepareWorkingDirectory(self, source_repo):
        """
        Checkout a working copy of the target SVN repository.
        """

        from os.path import join, exists

        if not self.repository.repository or exists(join(self.basedir, '.svn')):
            return

        cmd = self.repository.command("co", "--quiet")
        svnco = ExternalCommand(command=cmd)
        svnco.execute("%s%s" % (self.repository.repository,
                                self.repository.module), self.basedir)

    def _initializeWorkingDir(self):
        """
        Add the given directory to an already existing svn working tree.
        """

        from os.path import exists, join

        if not exists(join(self.basedir, '.svn')):
            raise TargetInitializationFailure("'%s' needs to be an SVN working copy already under SVN" % self.basedir)

        SyncronizableTargetWorkingDir._initializeWorkingDir(self)
