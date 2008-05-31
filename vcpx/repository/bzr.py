# -*- mode: python; coding: utf-8 -*-
# :Progetto: vcpx -- Bazaar support using the bzrlib instead of the frontend
# :Creato:   Fri Aug 19 01:06:08 CEST 2005
# :Autore:   Johan Rydberg <jrydberg@gnu.org>
#            Jelmer Vernooij <jelmer@samba.org>
#            Lalo Martins <lalo.martins@gmail.com>
#            Olaf Conradi <olaf@conradi.org>
# :Licenza:  GNU General Public License
#

"""
This module implements the backends for Bazaar.
"""

__docformat__ = 'reStructuredText'


from sys import version_info
assert version_info >= (2,4), "Bazaar backend requires Python 2.4"
del version_info

from bzrlib import errors
from bzrlib.branch import Branch
from bzrlib.bzrdir import BzrDir
from bzrlib.errors import NoSuchRevision
from bzrlib.missing import find_unmerged
from bzrlib.osutils import normpath, pathjoin
from bzrlib.plugin import load_plugins

from vcpx.changes import Changeset, ChangesetEntry
from vcpx.repository import Repository
from vcpx.source import UpdatableSourceWorkingDir, ChangesetApplicationFailure
from vcpx.target import SynchronizableTargetWorkingDir
from vcpx.workdir import WorkingDir


class BzrChangeset(Changeset):
    """
    Manage the particular reordering of the entries.

    Apparently TreeDelta doesn't expose the entries in a sensible order,
    they are grouped by kind.
    """

    def __init__(self, revision, date, author, log, entries=None, **other):
        """
        Initialize a new BzrChangeset, inserting the entries in a sensible order.
        """

        from os.path import split, join

        super(BzrChangeset, self).__init__(revision, date, author, log, entries=None, **other)
        if entries is not None:
            for e in entries:
                self.addEntry(e, revision)

            # Adjust old_name on renamed entries: bzr tell us the *original*
            # name of the rename...
            # Consider this:
            #
            #     $ bzr mv newnamedir/subdir/a newnamedir/subdir/b
            #     newnamedir/subdir/a => newnamedir/subdir/b
            #     $ bzr mv newnamedir/subdir newnamedir/newsubdir
            #     newnamedir/subdir => newnamedir/newsubdir
            #     $ bzr mv newnamedir dir
            #     newnamedir => dir
            #     $ bzr st
            #     renamed:
            #       newnamedir => dir
            #       newnamedir/subdir => dir/newsubdir
            #       newnamedir/subdir/a => dir/newsubdir/b

            renames = {}
            for e in self.entries:
                if e.action_kind == e.RENAMED:
                    renames[e.old_name] = e.name
                    d,f = split(e.old_name)
                    while d:
                        if d in renames:
                            e.old_name = join(renames[d], e.old_name[len(d)+1:])
                            break
                        d,f = split(d)

    def addEntry(self, entry, revision):
        """
        Fixup the ordering of the entries, by giving precedence to directories
        """

        if entry.action_kind in (entry.ADDED, entry.RENAMED) and entry.is_directory:
            dirname = entry.name + '/' # does bzr on windows use this too?
            for i,e in enumerate(self.entries):
                if e.name.startswith(dirname):
                    self.entries.insert(i, entry)
                    return
        elif entry.action_kind == entry.DELETED:
            for i,e in enumerate(self.entries):
                if e.action_kind == e.RENAMED and e.name == entry.name:
                    # This is the following case:
                    #  $ bzr rm A
                    #  $ bzr mv B A
                    self.entries.insert(i, entry)
                    return
                elif (e.action_kind == e.DELETED
                      and e.is_directory
                      and entry.name.startswith(e.name)):
                    # Remove dir contents before dir itself
                    self.entries.insert(i, entry)
                    return
                elif (e.action_kind == e.ADDED and e.name == entry.name):
                    # put replacement (rm+add) in the right order
                    self.entries.insert(i, entry)
                    return

        self.entries.append(entry)


class BzrRepository(Repository):
    METADIR = '.bzr'

    def _load(self, project):
        Repository._load(self, project)
        ppath = project.config.get(self.name, 'python-path')
        if ppath:
            from sys import path

            if ppath not in path:
                path.insert(0, ppath)

    def create(self):
        """
        Create a branch with a working tree at the base directory. If the base
        directory is inside a Bazaar style "shared repository", it will use
        that to create a branch and working tree (make sure it allows working
        trees).
        """

        self.log.info('Initializing new repository in %r...', self.basedir)
        try:
            bzrdir = BzrDir.open(self.basedir)
        except errors.NotBranchError:
            # really a NotBzrDir error...
            branch = BzrDir.create_branch_convenience(self.basedir, force_new_tree=True)
            wtree = branch.bzrdir.open_workingtree()
        else:
            bzrdir.create_branch()
            wtree = bzrdir.create_workingtree()

        return wtree


class BzrWorkingDir(UpdatableSourceWorkingDir, SynchronizableTargetWorkingDir):
    def __init__(self, repository):
        from os.path import split
        from bzrlib import version_info, IGNORE_FILENAME

        if version_info > (0,9):
            from bzrlib.ignores import add_runtime_ignores, parse_ignore_file
        else:
            from bzrlib import DEFAULT_IGNORE

        WorkingDir.__init__(self, repository)
        # TODO: check if there is a "repository" in the configuration,
        # and use it as a bzr repository
        self.ignored = []
        self._working_tree = None

        # The bzr repository may have some plugins that needs to be activated
        load_plugins()

        try:
            bzrdir = BzrDir.open(self.repository.basedir)
            wt = self._working_tree = bzrdir.open_workingtree()

            # read .bzrignore for _addSubtree()
            if wt.has_filename(IGNORE_FILENAME):
                f = wt.get_file_byname(IGNORE_FILENAME)
                if version_info > (0,9):
                    self.ignored.extend(parse_ignore_file(f))
                else:
                    self.ignored.extend([ line.rstrip("\n\r") for line in f.readlines() ])
                f.close()
        except (errors.NotBranchError, errors.NoWorkingTree):
            pass

        # Omit our own log...
        logfile = self.repository.projectref().logfile
        dir, file = split(logfile)
        if dir == self.repository.basedir:
            self.ignored.append(file)

        # ... and state file
        sfname = self.repository.projectref().state_file.filename
        dir, file = split(sfname)
        if dir == self.repository.basedir:
            self.ignored.append(file)
            self.ignored.append(file+'.old')
            self.ignored.append(file+'.journal')

        if version_info > (0,9):
            add_runtime_ignores(self.ignored)
        else:
            DEFAULT_IGNORE.extend(self.ignored)


    #############################
    ## UpdatableSourceWorkingDir

    def _changesetFromRevision(self, branch, revision_id):
        """
        Generate changeset for the given Bzr revision
        """
        from datetime import datetime
        from vcpx.tzinfo import FixedOffset, UTC

        revision = branch.repository.get_revision(revision_id)
        deltatree = branch.get_revision_delta(branch.revision_id_to_revno(revision_id))
        entries = []

        for delta in deltatree.renamed:
            e = ChangesetEntry(delta[1])
            e.action_kind = ChangesetEntry.RENAMED
            e.old_name = delta[0]
            e.is_directory = delta[3] == 'directory'
            entries.append(e)

        for delta in deltatree.added:
            e = ChangesetEntry(delta[0])
            e.action_kind = ChangesetEntry.ADDED
            e.is_directory = delta[2] == 'directory'
            entries.append(e)

        for delta in deltatree.removed:
            e = ChangesetEntry(delta[0])
            e.action_kind = ChangesetEntry.DELETED
            e.is_directory = delta[2] == 'directory'
            entries.append(e)

        for delta in deltatree.modified:
            e = ChangesetEntry(delta[0])
            e.action_kind = ChangesetEntry.UPDATED
            entries.append(e)

        if revision.timezone is not None:
            timezone = FixedOffset(revision.timezone / 60)
        else:
            timezone = UTC

        return BzrChangeset(revision.revision_id,
                            datetime.fromtimestamp(revision.timestamp, timezone),
                            revision.committer,
                            revision.message,
                            entries)

    def _getUpstreamChangesets(self, sincerev):
        """
        See what other revisions exist upstream and return them
        """

        from bzrlib import version_info

        parent_branch = Branch.open(self.repository.repository)

        branch = self._working_tree.branch
        branch.lock_read()
        try:
            parent_branch.lock_read()
            try:
                if version_info > (1, 6):
                    revisions = find_unmerged(branch, parent_branch, 'remote')[1]
                else:
                    revisions = find_unmerged(branch, parent_branch)[1]

                self.log.info("Collecting %d missing changesets", len(revisions))

                for id, revision in revisions:
                    yield self._changesetFromRevision(parent_branch, revision)
            finally:
                parent_branch.unlock()
        finally:
            branch.unlock()

        self.log.info("Fetching concrete changesets")
        branch.lock_write()
        try:
            branch.fetch(parent_branch)
        finally:
            branch.unlock()

    def _applyChangeset(self, changeset):
        """
        Apply the given changeset to the working tree
        """
        parent_branch = BzrDir.open(self.repository.repository).open_branch()
        self._working_tree.lock_write()
        try:
            count = self._working_tree.pull(parent_branch,
                                            stop_revision=changeset.revision)
            # XXX: this does not seem to return a true value on conflicts!
            conflicts = self._working_tree.update()
        finally:
            self._working_tree.unlock()
        try:
            pulled_revnos = count.new_revno - count.old_revno
        except AttributeError:
            # Prior to 0.15 pull returned a simple integer instead of a result object
            pulled_revnos = count
        self.log.info('Updated to %r, applied %d changesets', changeset.revision, count)
        if conflicts:
            # No conflict handling yet
            raise ChangesetApplicationFailure('Unsupported: conflicts')
        return []

    def _checkoutUpstreamRevision(self, revision):
        """
        Initial checkout of upstream branch, equivalent of 'bzr branch -r',
        and return the last changeset.
        """
        parent_bzrdir = BzrDir.open(self.repository.repository)
        parent_branch = parent_bzrdir.open_branch()

        if revision == "INITIAL":
            try:
                revid = parent_branch.get_rev_id(1)
            except NoSuchRevision:
                return None
        elif revision == "HEAD":
            revid = None
        else:
            revid = revision

        self.log.info('Extracting %r out of %r in %r...',
                      revid, parent_bzrdir.root_transport.base, self.repository.basedir)
        bzrdir = parent_bzrdir.sprout(self.repository.basedir, revid)
        self._working_tree = bzrdir.open_workingtree()

        return self._changesetFromRevision(parent_branch, revid)

    #################################
    ## SynchronizableTargetWorkingDir

    def _addPathnames(self, names):
        if len(names):
            names = [ pathjoin(self.repository.basedir, n) for n in names ]
            self._working_tree.smart_add(names, recurse=False)

    def _addSubtree(self, subdir):
        subdir = pathjoin(self.repository.basedir, subdir)
        added, ignored = self._working_tree.smart_add([subdir], recurse=True)

        from vcpx.dualwd import IGNORED_METADIRS

        for meta in IGNORED_METADIRS + self.ignored:
            if ignored.has_key(meta):
                del ignored[meta]

        if len(ignored):
            f = []
            map(f.extend, ignored.values())
            self._addPathnames(f)

    def _commit(self, date, author, patchname, changelog=None, entries=None,
                tags = [], isinitialcommit = False):
        """
        Commit the changeset.
        """
        from calendar import timegm  # like mktime(), but returns UTC timestamp
        from binascii import hexlify
        from re import search

        logmessage = []
        if patchname:
            logmessage.append(patchname)
        if changelog:
            logmessage.append(changelog)
        if logmessage:
            self.log.info('Committing %r...', logmessage[0])
            logmessage = '\n'.join(logmessage)
        else:
            self.log.info('Committing...')
            logmessage = "Empty changelog"

        timestamp = timegm(date.utctimetuple())
        timezone  = date.utcoffset().seconds + date.utcoffset().days * 24 * 3600

        # Normalize file names
        if entries:
            entries = [normpath(entry) for entry in entries]

        self._working_tree.commit(logmessage, committer=author,
                                  specific_files=entries,
                                  verbose=self.repository.projectref().verbose,
                                  timestamp=timestamp, timezone=timezone)

    def _removePathnames(self, names):
        """
        Remove files from the tree.
        """
        self.log.info('Removing %s...', ', '.join(names))
        names.sort(reverse=True) # remove files before the dir they're in
        self._working_tree.remove(names)

    def _renamePathname(self, oldname, newname):
        """
        Rename a file from oldname to newname.
        """
        self.log.info('Renaming %r to %r...', oldname, newname)
        self._working_tree.rename_one(oldname, newname)

    def _prepareTargetRepository(self):
        from bzrlib import version_info
        from vcpx.dualwd import IGNORED_METADIRS

        if self._working_tree is None:
            self._working_tree = self.repository.create()

        if version_info > (0,9):
            from bzrlib.ignores import add_runtime_ignores
            add_runtime_ignores(IGNORED_METADIRS)
        else:
            from bzrlib import DEFAULT_IGNORE
            DEFAULT_IGNORE.extend(IGNORED_METADIRS)
