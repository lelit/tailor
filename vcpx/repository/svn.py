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

from vcpx.changes import ChangesetEntry
from vcpx.config import ConfigurationError
from vcpx.repository import Repository
from vcpx.shwrap import ExternalCommand, PIPE, STDOUT, ReopenableNamedTemporaryFile
from vcpx.source import UpdatableSourceWorkingDir, ChangesetApplicationFailure
from vcpx.target import SynchronizableTargetWorkingDir, TargetInitializationFailure, \
                        PostCommitCheckFailure
from vcpx.tzinfo import UTC


class SvnRepository(Repository):
    METADIR = '.svn'

    def command(self, *args, **kwargs):
        if kwargs.get('svnadmin', False):
            kwargs['executable'] = self.__svnadmin
        return Repository.command(self, *args, **kwargs)

    def _load(self, project):
        Repository._load(self, project)
        cget = project.config.get
        self.EXECUTABLE = cget(self.name, 'svn-command', 'svn')
        self.__svnadmin = cget(self.name, 'svnadmin-command', 'svnadmin')
        self.use_propset = cget(self.name, 'use-propset', False)
        self.propset_date = cget(self.name, 'propset-date', True)
        self.filter_badchars = cget(self.name, 'filter-badchars', False)
        self.use_limit = cget(self.name, 'use-limit', True)
        self.trust_root = cget(self.name, 'trust-root', False)
        self.ignore_externals = cget(self.name, 'ignore-externals', True)
        self.commit_all_files = cget(self.name, 'commit-all-files', True)
        self.tags_path = cget(self.name, 'svn-tags', '/tags')
        self.branches_path = cget(self.name, 'svn-branches', '/branches')
        self._setupTagsDirectory = None

    def setupTagsDirectory(self):
        if self._setupTagsDirectory == None:
            self._setupTagsDirectory = False
            if self.module and self.module <> '/':

                # Check the existing tags directory
                cmd = self.command("ls")
                svnls = ExternalCommand(command=cmd)
                svnls.execute(self.repository + self.tags_path)
                if svnls.exit_status:
                    # create it, if not exist
                    cmd = self.command("mkdir", "-m",
                                       "This directory will host the tags")
                    svnmkdir = ExternalCommand(command=cmd)
                    svnmkdir.execute(self.repository + self.tags_path)
                    if svnmkdir.exit_status:
                        raise TargetInitializationFailure(
                                    "Was not able to create tags directory '%s'"
                                    % self.tags_path)
                else:
                    self.log.debug("Directory '%s' already exists"
                                   % self.tags_path)
                self._setupTagsDirectory = True
            else:
                self.log.debug("Tags needs module setup other than '/'")

        return self._setupTagsDirectory


    def _validateConfiguration(self):
        from vcpx.config import ConfigurationError

        Repository._validateConfiguration(self)

        if not self.repository:
            self.log.critical('Missing repository information in %r', self.name)
            raise ConfigurationError("Must specify the root of the "
                                     "Subversion repository used "
                                     "as %s with the option "
                                     "'repository'" % self.which)
        elif self.repository.endswith('/'):
            self.log.debug("Removing final slash from %r in %r",
                           self.repository, self.name)
            self.repository = self.repository.rstrip('/')

        if not self.module:
            self.log.critical('Missing module information in %r', self.name)
            raise ConfigurationError("Must specify the path within the "
                                     "Subversion repository as 'module'")

        if self.module == '.':
            self.log.warning("Replacing '.' with '/' in module name in %r",
                             self.name)
            self.module = '/'
        elif not self.module.startswith('/'):
            self.log.debug("Prepending '/' to module %r in %r",
                           self.module, self.name)
            self.module = '/' + self.module

        if not self.tags_path.startswith('/'):
            self.log.debug("Prepending '/' to svn-tags %r in %r",
                           self.tags_path, self.name)
            self.tags_path = '/' + self.tags_path

        if not self.branches_path.startswith('/'):
            self.log.debug("Prepending '/' to svn-branches %r in %r",
                           self.branches_path, self.name)
            self.branches_path = '/' + self.branches_path

    def create(self):
        """
        Create a local SVN repository, if it does not exist, and configure it.
        """

        from os.path import join, exists
        from sys import platform

        # Verify the existence of repository by listing its root
        cmd = self.command("ls")
        svnls = ExternalCommand(command=cmd)
        svnls.execute(self.repository)

        # Create it if it isn't a valid repository
        if svnls.exit_status:
            if not self.repository.startswith('file:///'):
                raise TargetInitializationFailure("%r does not exist and "
                                                  "cannot be created since "
                                                  "it's not a local (file:///) "
                                                  "repository" %
                                                  self.repository)

            if platform != 'win32':
                repodir = self.repository[7:]
            else:
                repodir = self.repository[8:]
            cmd = self.command("create", "--fs-type", "fsfs", svnadmin=True)
            svnadmin = ExternalCommand(command=cmd)
            svnadmin.execute(repodir)

            if svnadmin.exit_status:
                raise TargetInitializationFailure("Was not able to create a 'fsfs' "
                                                  "svn repository at %r" %
                                                  self.repository)
        if self.use_propset:
            if not self.repository.startswith('file:///'):
                self.log.warning("Repository is remote, cannot verify if it "
                                 "has the 'pre-revprop-change' hook active, needed "
                                 "by 'use-propset=True'. Assuming it does...")
            else:
                if platform != 'win32':
                    repodir = self.repository[7:]
                else:
                    repodir = self.repository[8:]
                hookname = join(repodir, 'hooks', 'pre-revprop-change')
                if platform == 'win32':
                    hookname += '.bat'
                if not exists(hookname):
                    prehook = open(hookname, 'w')
                    if platform <> 'win32':
                        prehook.write('#!/bin/sh\n')
                    prehook.write('exit 0\n')
                    prehook.close()
                    if platform <> 'win32':
                        from os import chmod
                        chmod(hookname, 0755)

        if self.module and self.module <> '/':
            cmd = self.command("ls")
            svnls = ExternalCommand(command=cmd)
            svnls.execute(self.repository + self.module)
            if svnls.exit_status:

                paths = []

                # Auto detect missing "branches/"
                if self.module.startswith(self.branches_path + '/'):
                    path = self.repository + self.branches_path
                    cmd = self.command("ls")
                    svnls = ExternalCommand(command=cmd)
                    svnls.execute(path)
                    if svnls.exit_status:
                        paths.append(path)

                paths.append(self.repository + self.module)
                cmd = self.command("mkdir", "-m",
                                   "This directory will host the upstream sources")
                svnmkdir = ExternalCommand(command=cmd)
                svnmkdir.execute(paths)
                if svnmkdir.exit_status:
                    raise TargetInitializationFailure("Was not able to create the "
                                                      "module %r, maybe more than "
                                                      "one level directory?" %
                                                      self.module)

def changesets_from_svnlog(log, repository, chunksize=2**15):
    from xml.sax import make_parser
    from xml.sax.handler import ContentHandler, ErrorHandler
    from datetime import datetime
    from vcpx.changes import ChangesetEntry, Changeset

    def get_entry_from_path(path, module=repository.module):
        # Given the repository url of this wc, say
        #   "http://server/plone/CMFPlone/branches/Plone-2_0-branch"
        # extract the "entry" portion (a relative path) from what
        # svn log --xml says, ie
        #   "/CMFPlone/branches/Plone-2_0-branch/tests/PloneTestCase.py"
        # that is to say "tests/PloneTestCase.py"

        if not module.endswith('/'):
            module = module + '/'
        if path.startswith(module):
            relative = path[len(module):]
            return relative

        # The path is outside our tracked tree...
        repository.log.warning('Ignoring %r since it is not under %r',
                               path, module)
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
            self.copies = []

        def startElement(self, name, attributes):
            if name == 'logentry':
                self.current = {}
                self.current['revision'] = attributes['revision']
                self.current['entries'] = []
                self.copies = []
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

                def parent_was_copied(n):
                    for p in self.copies:
                        if n.startswith(p+'/'):
                            return True
                    return False

                # Find renames from deleted directories:
                # $ svn mv dir/a.txt a.txt
                # $ svn del dir
                def check_renames_from_dir(name):
                    for e in mv_or_cp.values():
                        if e.old_name.startswith(name+'/'):
                            e.action_kind = e.RENAMED

                entries = []
                entries2 = []
                for e in self.current['entries']:
                    if e.action_kind==e.DELETED:
                        if mv_or_cp.has_key(e.name):
                            mv_or_cp[e.name].action_kind = e.RENAMED
                        else:
                            check_renames_from_dir(e.name)
                            entries2.append(e)
                    elif e.action_kind=='R':
                        # In svn parlance, 'R' means Replaced: a typical
                        # scenario is
                        #   $ svn mv a.txt b.txt
                        #   $ touch a.txt
                        #   $ svn add a.txt
                        if mv_or_cp.has_key(e.name):
                            mv_or_cp[e.name].action_kind = e.RENAMED
                        else:
                            check_renames_from_dir(e.name)
                        e.action_kind = e.ADDED
                        entries2.append(e)
                    elif parent_was_copied(e.name):
                        if e.action_kind != e.DELETED:
                            e.action_kind = e.ADDED
                            entries.append(e)
                    else:
                        entries.append(e)

                # Changes sort: first MODIFY|ADD|RENAME, than REPLACE|DELETE
                for e in entries2:
                    entries.append(e)

                svndate = self.current['date']
                # 2004-04-16T17:12:48.000000Z
                y,m,d = map(int, svndate[:10].split('-'))
                hh,mm,ss = map(int, svndate[11:19].split(':'))
                ms = int(svndate[20:-1])
                timestamp = datetime(y, m, d, hh, mm, ss, ms, UTC)

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
                        self.copies.append(entry.name)
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

    parser = make_parser()
    handler = SvnXMLLogHandler()
    parser.setContentHandler(handler)
    parser.setErrorHandler(ErrorHandler())

    chunk = log.read(chunksize)
    while chunk:
        parser.feed(chunk)
        for cs in handler.changesets:
            yield cs
        handler.changesets = []
        chunk = log.read(chunksize)
    parser.close()
    for cs in handler.changesets:
        yield cs


class SvnWorkingDir(UpdatableSourceWorkingDir, SynchronizableTargetWorkingDir):

    ## UpdatableSourceWorkingDir

    def _getUpstreamChangesets(self, sincerev=None):
        if sincerev:
            sincerev = int(sincerev)
        else:
            sincerev = 0

        cmd = self.repository.command("log", "--verbose", "--xml", "--non-interactive",
                                      "--revision", "%d:HEAD" % (sincerev+1))
        svnlog = ExternalCommand(cwd=self.repository.basedir, command=cmd)
        log = svnlog.execute('.', stdout=PIPE, TZ='UTC0')[0]

        if svnlog.exit_status:
            return []

        if self.repository.filter_badchars:
            from string import maketrans
            from cStringIO import StringIO

            # Apparently some (SVN repo contains)/(SVN server dumps) some
            # characters that are illegal in an XML stream. This was the case
            # with Twisted Matrix master repository. To be safe, we replace
            # all of them with a question mark.

            if isinstance(self.repository.filter_badchars, basestring):
                allbadchars = self.repository.filter_badchars
            else:
                allbadchars = "\x00\x01\x02\x03\x04\x05\x06\x07\x08\x09" \
                              "\x0B\x0C\x0E\x0F\x10\x11\x12\x13\x14\x15" \
                              "\x16\x17\x18\x19\x1A\x1B\x1C\x1D\x1E\x1F\x7f"

            tt = maketrans(allbadchars, "?"*len(allbadchars))
            log = StringIO(log.read().translate(tt))

        return changesets_from_svnlog(log, self.repository)

    def _applyChangeset(self, changeset):
        from os import walk
        from os.path import join, isdir
        from time import sleep

        # Complete changeset information, determining the is_directory
        # flag of the removed entries, before updating to the given revision
        for entry in changeset.entries:
            if entry.action_kind == entry.DELETED:
                entry.is_directory = isdir(join(self.repository.basedir, entry.name))

        cmd = self.repository.command("update")
        if self.repository.ignore_externals:
            cmd.append("--ignore-externals")
        cmd.extend(["--revision", changeset.revision])
        svnup = ExternalCommand(cwd=self.repository.basedir, command=cmd)

        retry = 0
        while True:
            out, err = svnup.execute(".", stdout=PIPE, stderr=PIPE)

            if svnup.exit_status == 1:
                retry += 1
                if retry>3:
                    break
                delay = 2**retry
                self.log.error("%s returned status %s saying\n%s",
                               str(svnup), svnup.exit_status, err.read())
                self.log.warning("Retrying in %d seconds...", delay)
                sleep(delay)
            else:
                break

        if svnup.exit_status:
            raise ChangesetApplicationFailure(
                "%s returned status %s saying\n%s" % (str(svnup),
                                                     svnup.exit_status,
                                                     err.read()))

        self.log.debug("%s updated to %s",
                       ','.join([e.name for e in changeset.entries]),
                       changeset.revision)

        # Complete changeset information, determining the is_directory
        # flag of the added entries
        implicitly_added_entries = []
        known_added_entries = set()
        for entry in changeset.entries:
            if entry.action_kind == entry.ADDED:
                known_added_entries.add(entry.name)
                fullname = join(self.repository.basedir, entry.name)
                entry.is_directory = isdir(fullname)
                # If it is a directory, extend the entries of the
                # changeset with all its contents, if not already there.
                if entry.is_directory:
                    for root, subdirs, files in walk(fullname):
                        if '.svn' in subdirs:
                            subdirs.remove('.svn')
                        for f in files:
                            name = join(root, f)[len(self.repository.basedir)+1:]
                            newe = ChangesetEntry(name)
                            newe.action_kind = newe.ADDED
                            implicitly_added_entries.append(newe)
                        for d in subdirs:
                            name = join(root, d)[len(self.repository.basedir)+1:]
                            newe = ChangesetEntry(name)
                            newe.action_kind = newe.ADDED
                            newe.is_directory = True
                            implicitly_added_entries.append(newe)

        for e in implicitly_added_entries:
            if not e.name in known_added_entries:
                changeset.entries.append(e)

        result = []
        for line in out:
            if len(line)>2 and line[0] == 'C' and line[1] == ' ':
                self.log.warning("Conflict after svn update: %r", line)
                result.append(line[2:-1])

        return result

    def _checkoutUpstreamRevision(self, revision):
        """
        Concretely do the checkout of the upstream revision.
        """

        from os.path import join, exists

        # Verify that the we have the root of the repository: do that
        # iterating an "svn ls" over the hierarchy until one fails

        lastok = self.repository.repository
        if not self.repository.trust_root:
            # Use --non-interactive, so that it fails if credentials
            # are needed.
            cmd = self.repository.command("ls", "--non-interactive")
            svnls = ExternalCommand(command=cmd)

            # First verify that we have a valid repository
            svnls.execute(self.repository.repository)
            if svnls.exit_status:
                lastok = None
            else:
                # Then verify it really points to the root of the
                # repository: this is needed because later the svn log
                # parser needs to know the "offset".

                reporoot = lastok[:lastok.rfind('/')]

                # Even if it would be enough asserting that the uplevel
                # directory is not a repository, find the real root to
                # suggest it in the exception.  But don't go too far, that
                # is, stop when you hit schema://...
                while '//' in reporoot:
                    svnls.execute(reporoot)
                    if svnls.exit_status:
                        break
                    lastok = reporoot
                    reporoot = reporoot[:reporoot.rfind('/')]

        if lastok is None:
            raise ConfigurationError('%r is not the root of a svn repository. If '
                                     'you are sure it is indeed, you may try setting '
                                     'the option "trust-root" to "True".' %
                                     self.repository.repository)
        elif lastok <> self.repository.repository:
            module = self.repository.repository[len(lastok):]
            module += self.repository.module
            raise ConfigurationError('Non-root svn repository %r. '
                                     'Please specify that as "repository=%s" '
                                     'and "module=%s".' %
                                     (self.repository.repository,
                                      lastok, module.rstrip('/')))

        if revision == 'INITIAL':
            initial = True
            cmd = self.repository.command("log", "--verbose", "--xml",
                                          "--non-interactive", "--stop-on-copy",
                                          "--revision", "1:HEAD")
            if self.repository.use_limit:
                cmd.extend(["--limit", "1"])
            svnlog = ExternalCommand(command=cmd)
            out, err = svnlog.execute("%s%s" % (self.repository.repository,
                                                self.repository.module),
                                      stdout=PIPE, stderr=PIPE)

            if svnlog.exit_status:
                raise TargetInitializationFailure(
                    "%s returned status %d saying\n%s" %
                    (str(svnlog), svnlog.exit_status, err.read()))

            csets = changesets_from_svnlog(out, self.repository)
            last = csets.next()
            revision = last.revision
        else:
            initial = False

        if not exists(join(self.repository.basedir, self.repository.METADIR)):
            self.log.debug("Checking out a working copy")

            cmd = self.repository.command("co", "--quiet")
            if self.repository.ignore_externals:
                cmd.append("--ignore-externals")
            cmd.extend(["--revision", revision])
            svnco = ExternalCommand(command=cmd)

            out, err = svnco.execute("%s%s@%s" % (self.repository.repository,
                                                  self.repository.module,
                                                  revision),
                                     self.repository.basedir, stdout=PIPE, stderr=PIPE)
            if svnco.exit_status:
                raise TargetInitializationFailure(
                    "%s returned status %s saying\n%s" % (str(svnco),
                                                         svnco.exit_status,
                                                         err.read()))
        else:
            self.log.debug("%r already exists, assuming it's "
                           "a svn working dir", self.repository.basedir)

        if not initial:
            if revision=='HEAD':
                revision = 'COMMITTED'
            cmd = self.repository.command("log", "--verbose", "--xml",
                                          "--non-interactive",
                                          "--revision", revision)
            svnlog = ExternalCommand(cwd=self.repository.basedir, command=cmd)
            out, err = svnlog.execute(stdout=PIPE, stderr=PIPE)

            if svnlog.exit_status:
                raise TargetInitializationFailure(
                    "%s returned status %d saying\n%s" %
                    (str(svnlog), svnlog.exit_status, err.read()))

            csets = changesets_from_svnlog(out, self.repository)
            last = csets.next()

        self.log.debug("Working copy up to svn revision %s", last.revision)

        return last

    ## SynchronizableTargetWorkingDir

    def _addPathnames(self, names):
        """
        Add some new filesystem objects.
        """

        cmd = self.repository.command("add", "--quiet", "--no-auto-props",
                                      "--non-recursive")
        ExternalCommand(cwd=self.repository.basedir, command=cmd).execute(names)

    def _propsetRevision(self, out, command, date, author):

        from re import search

        encode = self.repository.encode

        line = out.readline()
        if not line:
            # svn did not find anything to commit
            self.log.warning('svn did not find anything to commit')
            return

        # Assume svn output the revision number in the last output line
        while line:
            lastline = line
            line = out.readline()
        revno = search('\d+', lastline)
        if revno is None:
            out.seek(0)
            raise ChangesetApplicationFailure("%s wrote unrecognizable "
                                              "revision number:\n%s" %
                                              (str(command), out.read()))

        revision = revno.group(0)

        if self.repository.use_propset:

            cmd = self.repository.command("propset", "%(propname)s",
                                          "--quiet", "--revprop",
                                          "--revision", revision)
            pset = ExternalCommand(cwd=self.repository.basedir, command=cmd)
            if self.repository.propset_date:
                date = date.astimezone(UTC).replace(microsecond=0, tzinfo=None)
                pset.execute(date.isoformat()+".000000Z", propname='svn:date')
            pset.execute(encode(author), propname='svn:author')

        return revision

    def _tag(self, tag, date, author):
        """
        TAG current revision.
        """
        if self.repository.setupTagsDirectory():
            src = self.repository.repository + self.repository.module
            dest = self.repository.repository + self.repository.tags_path \
                                              + '/' + tag.replace('/', '_')

            cmd = self.repository.command("copy", src, dest, "-m", tag)
            svntag = ExternalCommand(cwd=self.repository.basedir, command=cmd)
            out, err = svntag.execute(stdout=PIPE, stderr=PIPE)

            if svntag.exit_status:
                raise ChangesetApplicationFailure("%s returned status %d saying\n%s"
                                                  % (str(svntag),
                                                     svntag.exit_status,
                                                     err.read()))

            self._propsetRevision(out, svntag, date, author)

    def _commit(self, date, author, patchname, changelog=None, entries=None,
                tags = [], isinitialcommit = False):
        """
        Commit the changeset.
        """

        encode = self.repository.encode

        logmessage = []
        if patchname:
            logmessage.append(patchname)
        if changelog:
            logmessage.append(changelog)

        # If we cannot use propset, fall back to old behaviour of
        # appending these info to the changelog

        if not self.repository.use_propset:
            logmessage.append('')
            logmessage.append('Original author: %s' % encode(author))
            logmessage.append('Date: %s' % date)
        elif not self.repository.propset_date:
            logmessage.append('')
            logmessage.append('Date: %s' % date)

        rontf = ReopenableNamedTemporaryFile('svn', 'tailor')
        log = open(rontf.name, "w")
        log.write(encode('\n'.join(logmessage)))
        log.close()

        cmd = self.repository.command("commit", "--file", rontf.name)
        commit = ExternalCommand(cwd=self.repository.basedir, command=cmd)

        if not entries or self.repository.commit_all_files:
            entries = ['.']

        out, err = commit.execute(entries, stdout=PIPE, stderr=PIPE)

        if commit.exit_status:
            raise ChangesetApplicationFailure("%s returned status %d saying\n%s"
                                              % (str(commit),
                                                 commit.exit_status,
                                                 err.read()))

        revision = self._propsetRevision(out, commit, date, author)
        if not revision:
            # svn did not find anything to commit
            return

        cmd = self.repository.command("update", "--quiet")
        if self.repository.ignore_externals:
            cmd.append("--ignore-externals")
        cmd.extend(["--revision", revision])

        ExternalCommand(cwd=self.repository.basedir, command=cmd).execute()

    def _postCommitCheck(self):
        """
        Assert that all the entries in the working dir are versioned.
        """

        cmd = self.repository.command("status")
        whatsnew = ExternalCommand(cwd=self.repository.basedir, command=cmd)
        output = whatsnew.execute(stdout=PIPE, stderr=STDOUT)[0]
        unknown = [l for l in output.readlines() if l.startswith('?')]
        if unknown:
            raise PostCommitCheckFailure(
                "Changes left in working dir after commit:\n%s" % ''.join(unknown))

    def _removePathnames(self, names):
        """
        Remove some filesystem objects.
        """

        cmd = self.repository.command("remove", "--quiet", "--force")
        remove = ExternalCommand(cwd=self.repository.basedir, command=cmd)
        remove.execute(names)

    def _renamePathname(self, oldname, newname):
        """
        Rename a filesystem object.
        """

        from os import rename
        from os.path import join, exists, isdir
        from time import sleep
        from datetime import datetime

        # --force in case the file has been changed and moved in one revision
        cmd = self.repository.command("mv", "--quiet", "--force")
        # Subversion does not seem to allow
        #   $ mv a.txt b.txt
        #   $ svn mv a.txt b.txt
        # Here we are in this situation, since upstream VCS already
        # moved the item.
        # It may be better to let subversion do the move itself. For one thing,
        # svn's cp+rm is different from rm+add (cp preserves history).
        unmoved = False
        oldpath = join(self.repository.basedir, oldname)
        newpath = join(self.repository.basedir, newname)
        if not exists(oldpath):
            try:
                rename(newpath, oldpath)
            except OSError:
                self.log.critical('Cannot rename %r back to %r',
                                  newpath, oldpath)
                raise
            unmoved = True

        # Ticket #135: Need a timediff between rsync and directory move
        if isdir(oldpath):
            now = datetime.now()
            if hasattr(self, '_last_svn_move'):
                last = self._last_svn_move
            else:
                last = now
            if not (now-last).seconds:
                sleep(1)
            self._last_svn_move = now

        move = ExternalCommand(cwd=self.repository.basedir, command=cmd)
        out, err = move.execute(oldname, newname, stdout=PIPE, stderr=PIPE)
        if move.exit_status:
            if unmoved:
                rename(oldpath, newpath)
            raise ChangesetApplicationFailure("%s returned status %d saying\n%s"
                                              % (str(move), move.exit_status,
                                                 err.read()))

    def _prepareTargetRepository(self):
        """
        Check for target repository existence, eventually create it.
        """

        if not self.repository.repository:
            return

        self.repository.create()

    def _prepareWorkingDirectory(self, source_repo):
        """
        Checkout a working copy of the target SVN repository.
        """

        from os.path import join, exists
        from vcpx.dualwd import IGNORED_METADIRS

        if not self.repository.repository or exists(join(self.repository.basedir, self.repository.METADIR)):
            return

        cmd = self.repository.command("co", "--quiet")
        if self.repository.ignore_externals:
            cmd.append("--ignore-externals")

        svnco = ExternalCommand(command=cmd)
        svnco.execute("%s%s" % (self.repository.repository,
                                self.repository.module), self.repository.basedir)

        ignore = [md for md in IGNORED_METADIRS]

        if self.logfile.startswith(self.repository.basedir):
            ignore.append(self.logfile[len(self.repository.basedir)+1:])
        if self.state_file.filename.startswith(self.repository.basedir):
            sfrelname = self.state_file.filename[len(self.repository.basedir)+1:]
            ignore.append(sfrelname)
            ignore.append(sfrelname+'.old')
            ignore.append(sfrelname+'.journal')

        cmd = self.repository.command("propset", "%(propname)s", "--quiet")
        pset = ExternalCommand(cwd=self.repository.basedir, command=cmd)
        pset.execute('\n'.join(ignore), '.', propname='svn:ignore')

    def _initializeWorkingDir(self):
        """
        Add the given directory to an already existing svn working tree.
        """

        from os.path import exists, join

        if not exists(join(self.repository.basedir, self.repository.METADIR)):
            raise TargetInitializationFailure("'%s' needs to be an SVN working copy already under SVN" % self.repository.basedir)

        SynchronizableTargetWorkingDir._initializeWorkingDir(self)
