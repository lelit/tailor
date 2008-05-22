# -*- mode: python; coding: utf-8 -*-
# :Progetto: vcpx -- CVSPS details
# :Creato:   mer 16 giu 2004 00:46:12 CEST
# :Autore:   Lele Gaifax <lele@nautilus.homeip.net>
# :Licenza:  GNU General Public License
#

"""
This module contains supporting classes for CVS. To get a
cross-repository revision number a la Subversion, the implementation
uses `cvsps` to fetch the changes from the upstream repository.
"""

__docformat__ = 'reStructuredText'

from vcpx import TailorException
from vcpx.repository import Repository
from vcpx.shwrap import ExternalCommand, PIPE
from vcpx.source import UpdatableSourceWorkingDir, ChangesetApplicationFailure, \
                        InvocationError
from vcpx.target import SynchronizableTargetWorkingDir, TargetInitializationFailure
from vcpx.tzinfo import UTC


class EmptyRepositoriesFoolsMe(TailorException):
    "Cannot handle empty repositories. Maybe wrong module/repository?"

    # This is the exception raised when we try to tailor an empty CVS
    # repository. This is more a shortcoming of tailor, rather than a
    # real problem with those repositories.


class CvspsRepository(Repository):
    METADIR = 'CVS'

    def _load(self, project):
        from datetime import timedelta

        Repository._load(self, project)
        self.EXECUTABLE = project.config.get(self.name, 'cvs-command', 'cvs')
        self.__cvsps = project.config.get(self.name, 'cvsps-command', 'cvsps')
        self.tag_entries = project.config.get(self.name, 'tag-entries', 'True')
        self.freeze_keywords = project.config.get(self.name, 'freeze-keywords', 'False')
        threshold = project.config.get(self.name, 'changeset-threshold', '180')
        self.changeset_threshold = timedelta(seconds=float(threshold))

    def _validateConfiguration(self):
        from os.path import split
        from vcpx.config import ConfigurationError

        Repository._validateConfiguration(self)

        if not self.module and self.repository:
            self.module = split(self.repository)[1]

        if not self.module:
            self.log.critical('Missing module information in %r', self.name)
            raise ConfigurationError("Must specify a repository and maybe "
                                     "a module also")

        if self.module.endswith('/'):
            self.log.debug("Removing final slash from %r in %r",
                           self.module, self.name)
            self.module = self.module.rstrip('/')

    def command(self, *args, **kwargs):
        if kwargs.get('cvsps', False):
            kwargs['executable'] = self.__cvsps
        return Repository.command(self, *args, **kwargs)

    def create(self):
        """
        Create a local CVS repository.
        """

        from os import rmdir, makedirs
        from tempfile import mkdtemp
        from os.path import join, exists

        if self.repository.startswith(':local:'):
            path = self.repository[7:]
        elif self.repository.startswith('/'):
            path = self.repository
        else:
            # Remote repository
            return

        if exists(join(path, 'CVSROOT')):
            return

        makedirs(path)
        cmd = self.command("-f", "-d", path, "init")
        c = ExternalCommand(command=cmd)
        c.execute()
        if c.exit_status:
            raise TargetInitializationFailure("Could not create CVS repository at %r",
                                              path)

        if self.module:
            tempwc = mkdtemp('cvs', 'tailor')
            cmd = self.command("-f", "-d", path, "import",
                               "-m", "This directory will host the "
                               "upstream sources",
                               self.module, "tailor", "start")
            c = ExternalCommand(cwd=tempwc, command=cmd)
            c.execute()
            rmdir(tempwc)
            if c.exit_status:
                raise TargetInitializationFailure("Could not create initial module")


def changesets_from_cvsps(log, sincerev=None):
    """
    Parse CVSps log.
    """

    from datetime import datetime
    from vcpx.changes import Changeset, ChangesetEntry
    from vcpx.repository.cvs import compare_cvs_revs

    # cvsps output sample:
    ## ---------------------
    ## PatchSet 1500
    ## Date: 2004/05/09 17:54:22
    ## Author: grubert
    ## Branch: HEAD
    ## Tag: (none)
    ## Log:
    ## Tell the reason for using mbox (not wrapping long lines).
    ##
    ## Members:
    ##         docutils/writers/latex2e.py:1.78->1.79

    l = None
    while 1:
        l = log.readline()
        if l <> '---------------------\n':
            break

        l = log.readline()
        assert l.startswith('PatchSet '), "Parse error: %s"%l

        pset = {}
        pset['revision'] = l[9:-1].strip()
        l = log.readline()
        while not l.startswith('Log:'):
            field,value = l.split(':',1)
            pset[field.lower()] = value.strip()
            l = log.readline()

        msg = []
        l = log.readline()
        msg.append(l)
        l = log.readline()
        while l <> 'Members: \n':
            msg.append(l)
            l = log.readline()

        assert l.startswith('Members:'), "Parse error: %s" % l

        entries = []
        l = log.readline()
        seen = {}
        while l.startswith('\t'):
            if not sincerev or (sincerev<int(pset['revision'])):
                # Cannot use split here, file may contain ':'
                cpos = l.rindex(':')
                file = l[1:cpos]
                revs = l[cpos+1:-1]
                fromrev,torev = revs.strip().split('->')

                # Due to the fuzzy mechanism, cvsps may group
                # together two commits on a single entry, thus
                # giving something like:
                #
                #   Normalizer.py:1.12->1.13
                #   Registry.py:1.22->1.23
                #   Registry.py:1.21->1.22
                #   Stopwords.py:1.9->1.10
                #
                # Collapse those into a single one.

                e = seen.get(file)
                if not e:
                    e = ChangesetEntry(file)
                    e.old_revision = fromrev
                    e.new_revision = torev
                    seen[file] = e
                    entries.append(e)
                else:
                    if compare_cvs_revs(e.old_revision, fromrev)>0:
                        e.old_revision = fromrev

                    if compare_cvs_revs(e.new_revision, torev)<0:
                        e.new_revision = torev

                if fromrev=='INITIAL':
                    e.action_kind = e.ADDED
                elif "(DEAD)" in torev:
                    e.action_kind = e.DELETED
                    e.new_revision = torev[:torev.index('(DEAD)')]
                else:
                    e.action_kind = e.UPDATED

            l = log.readline()

        if not sincerev or (sincerev<int(pset['revision'])):
            cvsdate = pset['date']
            y,m,d = map(int, cvsdate[:10].split('/'))
            hh,mm,ss = map(int, cvsdate[11:19].split(':'))
            timestamp = datetime(y, m, d, hh, mm, ss, 0, UTC)
            pset['date'] = timestamp

            yield Changeset(pset['revision'], timestamp, pset['author'],
                            ''.join(msg), entries)


class CvspsWorkingDir(UpdatableSourceWorkingDir,
                      SynchronizableTargetWorkingDir):

    """
    An instance of this class represents a read/write CVS working
    directory, so that it can be used both as a source of patches and
    as a target repository.

    It uses `cvsps` to do the actual fetch of the changesets metadata
    from the server, so that we can reasonably group together related
    changes that would otherwise be sparsed, as CVS is file-centric.
    """

    ## UpdatableSourceWorkingDir

    def _getUpstreamChangesets(self, sincerev=None):
        from os.path import join, exists

        branch="HEAD"
        fname = join(self.repository.basedir, 'CVS', 'Tag')
        if exists(fname):
            tag = open(fname).read()
            if tag.startswith('T'):
                branch=tag[1:-1]
        else:
            if sincerev is not None and isinstance(sincerev, basestring) \
                   and not sincerev[0] in '0123456789':
                branch = sincerev
                sincerev = None

        if sincerev:
            sincerev = int(sincerev)

        cmd = self.repository.command("--norc", "--cvs-direct", "-u", "-b", branch,
                                      "--root", self.repository.repository,
                                      cvsps=True)
        cvsps = ExternalCommand(command=cmd)
        log = cvsps.execute(self.repository.module, stdout=PIPE, TZ='UTC0')[0]

        for cs in changesets_from_cvsps(log, sincerev):
            yield cs

    def __maybeDeleteDirectory(self, entrydir, changeset):
        from os.path import join, exists
        from vcpx.repository.cvs import CvsEntries

        if not entrydir:
            return

        absentrydir = join(self.repository.basedir, entrydir)
        if not exists(absentrydir) or CvsEntries(absentrydir).isEmpty():
            # Oh, the directory is empty: if there are no other added entries
            # in the directory, insert a REMOVE event against it.
            for added in changeset.addedEntries():
                if added.name.startswith(entrydir):
                    # entrydir got empty, but only temporarily
                    return False
            return True
        return False

    def _applyChangeset(self, changeset):
        from os.path import join, exists, split
        from os import listdir
        from shutil import rmtree
        from time import sleep
        from vcpx.repository.cvs import CvsEntries, compare_cvs_revs

        entries = CvsEntries(self.repository.basedir)

        # Collect added and deleted directories
        addeddirs = []
        deleteddirs = []

        # Group entries at the same revision
        reventries = {}

        for e in changeset.entries:
            if e.action_kind == e.UPDATED:
                info = entries.getFileInfo(e.name)
                if not info:
                    self.log.debug('promoting "%s" to ADDED at '
                                   'revision %s', e.name, e.new_revision)
                    e.action_kind = e.ADDED
                    for dir in self.__createParentCVSDirectories(changeset, e.name):
                        addeddirs.append((e, dir))
                elif info.cvs_version == e.new_revision:
                    self.log.debug('skipping "%s" since it is already '
                                   'at revision %s', e.name, e.new_revision)
                    continue
            elif e.action_kind == e.DELETED:
                if not exists(join(self.repository.basedir, e.name)):
                    self.log.debug('skipping "%s" since it is already '
                                   'deleted', e.name)
                    entrydir = split(e.name)[0]
                    if self.__maybeDeleteDirectory(entrydir, changeset):
                        deleteddirs.append(entrydir)
                    continue
            elif e.action_kind == e.ADDED:
                if e.new_revision is None:
                    # This is a new directory entry, there is no need to update it
                    continue
                else:
                    for dir in self.__createParentCVSDirectories(changeset, e.name):
                        addeddirs.append((e, dir))

            # If this is a directory (CVS does not version directories,
            # and thus new_revision is always None for them), and it's
            # going to be deleted, do not execute a 'cvs update', that
            # in some cases does not do what one would expect. Instead,
            # remove it with everything it contains (that should be
            # just a single "CVS" subdir, btw)

            if e.action_kind == e.DELETED and e.new_revision is None:
                assert CvsEntries(join(self.repository.basedir, e.name)).isEmpty(), '%s should be empty' % e.name
                self.log.info("removing stale deleted directory %s", path)
                rmtree(join(self.repository.basedir, e.name))
            else:
                names = reventries.setdefault(e.new_revision, [])
                names.append(e.name)

            if e.action_kind == e.DELETED:
                entrydir = split(e.name)[0]
                if self.__maybeDeleteDirectory(entrydir, changeset):
                    deleteddirs.append(entrydir)

        revs = reventries.keys()
        revs.sort(compare_cvs_revs)

        cmd = self.repository.command("-f", "-d", "%(repository)s",
                                      "-q", "update", "-d", "-P",
                                      "-r", "%(revision)s")
        if self.repository.freeze_keywords:
            cmd.append('-kk')
        cvsup = ExternalCommand(cwd=self.repository.basedir, command=cmd)
        for rev in revs:
            names = reventries[rev]
            retry = 0
            while True:
                cvsup.execute(names, repository=self.repository.repository,
                              revision=rev)
                if cvsup.exit_status:
                    retry += 1
                    if retry>3:
                        break
                    delay = 2**retry
                    self.log.warning("%s returned status %s, "
                                     "retrying in %d seconds...",
                                     str(cvsup), cvsup.exit_status, delay)
                    sleep(retry)
                else:
                    break

            if cvsup.exit_status:
                raise ChangesetApplicationFailure(
                    "%s returned status %s" % (str(cvsup),
                                               cvsup.exit_status))

            self.log.debug("%s updated to %s", ','.join(names), e.new_revision)

        # Fake up ADD and DEL events for the directories implicitly
        # added/removed, so that the replayer gets their name.

        for entry,path in addeddirs:
            entry = changeset.addEntry(path, None, before=entry)
            entry.action_kind = entry.ADDED
            entry.is_directory = True
            self.log.debug("registering new %s directory", entry.name)

        for path in deleteddirs:
            deldir = changeset.addEntry(path, None)
            deldir.action_kind = deldir.DELETED
            entry.is_directory = True
            self.log.debug("registering %s directory deletion", path)

            # Since we are not going to issue cvs updates on whole
            # directories but only on files, most probably the -P
            # above has no effect: remove the deleted dir if it's still
            # there.
            if exists(join(self.repository.basedir, e.name)):
                self.log.info("removing stale deleted directory %s", path)
                rmtree(join(self.repository.basedir, e.name))

        # Make sure all files are present on disk: CVS update does not
        # create them nor reports an error if the files have been
        # completely removed from the cvs repository. So loop over the
        # entries and verify the presence of added/changed ones.

        for entry in changeset.entries:
            if (entry.action_kind in (entry.ADDED, entry.UPDATED)
                and not exists(join(self.repository.basedir, entry.name))):
                self.log.warning("Ignoring entry %s, CVS source no "
                                 "longer knows about it.", entry.name)
                changeset.entries.remove(entry)

    def _checkoutUpstreamRevision(self, revision):
        """
        Concretely do the checkout of the upstream sources. Use
        `revision` as the name of the tag to get, or as a date if it
        starts with a number.

        Return the last applied changeset.
        """

        from os.path import join, exists, split
        from time import sleep
        from vcpx.repository.cvs import CvsEntries, compare_cvs_revs
        from vcpx.changes import ChangesetEntry

        if not self.repository.module:
            raise InvocationError("Must specify a module name")

        timestamp = None
        if revision is not None:
            # If the revision contains a space, assume it really
            # specify a branch and a timestamp. If it starts with
            # a digit, assume it's a timestamp. Otherwise, it must
            # be a branch name
            if revision[0] in '0123456789' or revision == 'INITIAL':
                timestamp = revision
                revision = None
            elif ' ' in revision:
                revision, timestamp = revision.split(' ', 1)

        csets = self.getPendingChangesets(revision)
        if not csets:
            raise TargetInitializationFailure(
                "Something went wrong: there are no changesets since "
                "revision '%s'" % revision)
        if timestamp == 'INITIAL':
            initialcset = csets.next()
            timestamp = initialcset.date.replace(tzinfo=None).isoformat(sep=' ')
        else:
            initialcset = None

        if not exists(join(self.repository.basedir, 'CVS')):
            # CVS does not handle "checkout -d multi/level/subdir", so
            # split the basedir and use it's parentdir as cwd below.
            parentdir, subdir = split(self.repository.basedir)
            cmd = self.repository.command("-f", "-q",
                                          "-d", self.repository.repository,
                                          "checkout",
                                          "-d", subdir)
            if revision:
                cmd.extend(["-r", revision])
            if timestamp:
                cmd.extend(["-D", "%s UTC" % timestamp])
            if self.repository.freeze_keywords:
                cmd.append('-kk')

            checkout = ExternalCommand(cwd=parentdir, command=cmd)
            retry = 0
            while True:
                checkout.execute(self.repository.module)
                if checkout.exit_status:
                    retry += 1
                    if retry>3:
                        break
                    delay = 2**retry
                    self.log.warning("%s returned status %s, "
                                     "retrying in %d seconds...",
                                     str(checkout), checkout.exit_status,
                                     delay)
                    sleep(retry)
                else:
                    break

            if checkout.exit_status:
                raise TargetInitializationFailure(
                    "%s returned status %s" % (str(checkout),
                                               checkout.exit_status))
        else:
            self.log.info("Using existing %s", self.repository.basedir)

        if self.repository.tag_entries:
            self.__forceTagOnEachEntry()

        entries = CvsEntries(self.repository.basedir)
        youngest_entry = entries.getYoungestEntry()
        if youngest_entry is None:
            raise EmptyRepositoriesFoolsMe("The working copy '%s' of the "
                                           "CVS repository seems empty, "
                                           "don't know how to deal with "
                                           "that." % self.repository.basedir)

        # loop over the changesets and find the last applied, to find
        # out the actual cvsps revision

        found = False

        def already_applied(cs, entries=entries):
            "Loop over changeset entries to determine if it's already applied."

            applied = False

            # applied become True when an entry is DELETED *and* there is
            # no metainfo for it: thus, a changeset that removes a few entries
            # very late in history would be assumed as applied. Prevent that
            # by checking for at least one explicit match on an existing entry.
            onepositive = False

            for m in cs.entries:
                info = entries.getFileInfo(m.name)

                # If the entry's info exists, compare the on-disk
                # version with what we have: the revision is already
                # applied if the former is greater or equal than the
                # latter. The same if the info does not exist and it's
                # a delete event.

                if info:
                    odversion = info.cvs_version
                    applied = compare_cvs_revs(odversion, m.new_revision) >= 0

                    # If only one "hunk" is not yet applied, the whole
                    # changeset is new.
                    if not applied:
                        break
                    else:
                        onepositive = True
                elif m.action_kind == ChangesetEntry.DELETED:
                    applied = True
            return applied and onepositive

        # We cannot stop at the first not-applied cset, because it may
        # old enough to trick already_applied(): an entry may have
        # been moved in the meantime, and thus the getFileInfo()
        # method would return None, for example... So we really have
        # to loop over the whole queue.

        for cset in self.state_file:
            applied = already_applied(cset)
            found = found or applied
            if applied:
                last = cset

        if not found and initialcset:
            found = already_applied(initialcset)
            if found:
                last = initialcset

        if not found:
            raise TargetInitializationFailure(
                "Something went wrong: unable to determine the exact upstream "
                "revision of the checked out tree in '%s'. Either you specified "
                "the wrong initial timestamp, or you are checking out a "
                "composition of 'CVS modules' and Tailor does not support them; "
                "see the option 'trim-module-components' for a possible "
                "workaround." % self.repository.basedir)
        else:
            self.log.info("Working copy up to revision %s", last.revision)

        return last

    def __createParentCVSDirectories(self, changeset, entry):
        """
        Verify that the hierarchy down to the entry is under CVS.

        If the directory containing the entry does not exist,
        create it and make it appear as under CVS so that a subsequent
        'cvs update' will work.

        Returns the list of eventually added directories.
        """

        from os.path import split, join, exists
        from os import mkdir

        tobeadded = []

        path = split(entry)[0]

        parentcvs = join(self.repository.basedir, path, 'CVS')
        while not exists(parentcvs):
            tobeadded.insert(0, path)
            if not path:
                break
            path = split(path)[0]
            parentcvs = join(self.repository.basedir, path, 'CVS')

        assert exists(parentcvs), "Uhm, strange things happen: " \
               "unable to find or create parent CVS area for %r" % entry

        if tobeadded:
            reposf = open(join(parentcvs, 'Repository'))
            rep = reposf.readline()[:-1]
            reposf.close()

            rootf = open(join(parentcvs, 'Root'))
            root = rootf.readline()
            rootf.close()

        for toadd in tobeadded:
            basedir = join(self.repository.basedir, toadd)
            cvsarea = join(basedir, 'CVS')

            if not exists(basedir):
                mkdir(basedir)

            # Create fake CVS area
            mkdir(cvsarea)

            # Create an empty "Entries" file
            entries = open(join(cvsarea, 'Entries'), 'w')
            entries.close()

            reposf = open(join(cvsarea, 'Repository'), 'w')
            rep = '/'.join((rep, split(basedir)[1]))
            reposf.write("%s\n" % rep)
            reposf.close()

            rootf = open(join(cvsarea, 'Root'), 'w')
            rootf.write(root)
            rootf.close()

        return tobeadded

    ## SynchronizableTargetWorkingDir

    def _prepareTargetRepository(self):
        """
        Create the CVS repository if it's local and does not exist.
        """

        self.repository.create()

    def _prepareWorkingDirectory(self, source_repo):
        """
        Checkout a working copy of the target CVS.
        """

        from os.path import join, exists, split

        if not self.repository.repository or exists(join(self.repository.basedir, 'CVS')):
            return

        # CVS does not handle "checkout -d multi/level/subdir", so
        # split the basedir and use it's parentdir as cwd below.
        parentdir, subdir = split(self.repository.basedir)
        cmd = self.repository.command("-f", "-d", self.repository.repository, "co",
                                      "-d", subdir)
        cvsco = ExternalCommand(cwd=parentdir, command=cmd)
        cvsco.execute(self.repository.module)

    def _parents(self, path):
        from os.path import exists, join, split

        parents = []
        parent = split(path)[0]
        while parent:
            if exists(join(self.repository.basedir, parent, 'CVS')):
                break
            parents.insert(0, parent)
            parent = split(parent)[0]

        return parents

    def _addEntries(self, entries):
        """
        Synthesize missing parent directory additions
        """

        allnames = [e.name for e in entries]
        newdirs = []
        for entry in allnames:
            for parent in [p for p in self._parents(entry) if p not in allnames]:
                if p not in newdirs:
                    newdirs.append(parent)

        newdirs.extend(allnames)
        self._addPathnames(newdirs)

    def _addPathnames(self, names):
        """
        Add some new filesystem objects.
        """

        cmd = self.repository.command("-f", '-q', 'add', '-ko')
        ExternalCommand(cwd=self.repository.basedir, command=cmd).execute(names)

    def __forceTagOnEachEntry(self):
        """
        Massage each CVS/Entries file, locking (ie, tagging) each
        entry to its current CVS version.

        This is to prevent silly errors such those that could arise
        after a manual ``cvs update`` in the working directory.
        """

        from os import walk, rename, remove
        from os.path import join, exists

        self.log.info("Forcing CVS sticky tag in %s", self.repository.basedir)

        for dir, subdirs, files in walk(self.repository.basedir):
            if dir[-3:] == 'CVS':
                efn = join(dir, 'Entries')

                # Strangeness is a foreign word in CVS: sometime
                # the Entries isn't there...
                if not exists(efn):
                    continue

                f = open(efn)
                entries = f.readlines()
                f.close()

                newentries = []
                for e in entries:
                    if e.startswith('/'):
                        fields = e.split('/')
                        fields[-1] = "T%s\n" % fields[2]
                        newe = '/'.join(fields)
                        newentries.append(newe)
                    else:
                        newentries.append(e)

                rename(efn, efn+'.tailor-old')

                f = open(efn, 'w')
                f.writelines(newentries)
                f.close()

                remove(efn+'.tailor-old')


    def _commit(self, date, author, patchname, changelog=None, entries=None,
                tags = [], isinitialcommit = False):
        """
        Commit the changeset.
        """

        from vcpx.shwrap import ReopenableNamedTemporaryFile

        encode = self.repository.encode

        logmessage = []
        if patchname:
            logmessage.append(patchname)
        if changelog:
            logmessage.append(changelog)
        logmessage.append('')
        logmessage.append('Original author: %s' % author)
        logmessage.append('Date: %s' % date)

        rontf = ReopenableNamedTemporaryFile('cvs', 'tailor')
        log = open(rontf.name, "w")
        log.write(encode('\n'.join(logmessage)))
        log.close()

        cmd = self.repository.command("-f", "-q", "ci", "-F", rontf.name)
        if not entries:
            entries = ['.']

        c = ExternalCommand(cwd=self.repository.basedir, command=cmd)
        c.execute(entries)

        if c.exit_status:
            raise ChangesetApplicationFailure("%s returned status %d" %
                                              (str(c), c.exit_status))

    def _removePathnames(self, names):
        """
        Remove some filesystem objects.
        """

        cmd = self.repository.command("-f", "-q", "remove")
        ExternalCommand(cwd=self.repository.basedir, command=cmd).execute(names)

    def _renamePathname(self, oldname, newname):
        """
        Rename a filesystem object.
        """

        self._removePathnames([oldname])
        self._addPathnames([newname])

    def _tag(self, tagname, date, author):
        """
        Apply a tag.
        """

        # Sanitize tagnames for CVS: start with [a-zA-z], only include letters,
        # numbers, '-' and '_'.
        # str.isalpha et al are locale-dependent
        def iscvsalpha(chr):
            return (chr >= 'a' and chr <= 'z') or (chr >= 'A' and chr <= 'Z')
        def iscvsdigit(chr):
            return chr >= '0' and chr <= '9'
        def iscvschar(chr):
            return iscvsalpha(chr) or iscvsdigit(chr) or chr == '-' or chr == '_'
        def cvstagify(chr):
            if iscvschar(chr):
                return chr
            else:
                return '_'

        tagname = ''.join([cvstagify(chr) for chr in tagname])
        if not iscvsalpha(tagname[0]):
            tagname = 'tag-' + tagname

        cmd = self.repository.command("-f", "tag")
        c = ExternalCommand(cwd=self.repository.basedir, command=cmd)
        c.execute(tagname)
        if c.exit_status:
            raise ChangesetApplicationFailure("%s returned status %d" %
                                              (str(c), c.exit_status))
