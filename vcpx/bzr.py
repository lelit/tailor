# -*- mode: python; coding: utf-8 -*-
# :Progetto: vcpx -- bazaar-ng support using the bzrlib instead of the frontend
# :Creato:   Fri Aug 19 01:06:08 CEST 2005
# :Autore:   Johan Rydberg <jrydberg@gnu.org>
#            Jelmer Vernooij <jelmer@samba.org>
#            Lalo Martins <lalo.martins@gmail.com>
#            Olaf Conradi <olaf@conradi.org>
# :Licenza:  GNU General Public License
#

"""
This module implements the backends for Bazaar-NG.
"""

__docformat__ = 'reStructuredText'

import os
from workdir import WorkingDir
from source import UpdatableSourceWorkingDir, ChangesetApplicationFailure
from target import SyncronizableTargetWorkingDir, TargetInitializationFailure
from bzrlib.bzrdir import BzrDir
from bzrlib.delta import compare_trees
from bzrlib import errors

class BzrWorkingDir(UpdatableSourceWorkingDir, SyncronizableTargetWorkingDir):
    def __init__(self, repository):
        WorkingDir.__init__(self, repository)
        # TODO: check if there is a "repository" in the configuration,
        # and use it as a bzr repository
        self._working_tree = None
        try:
            bzrdir = BzrDir.open(self.basedir)
            self._working_tree = bzrdir.open_workingtree()
        except errors.NotBranchError, errors.NoWorkingTree:
            pass

    #############################
    ## UpdatableSourceWorkingDir

    def _changesetFromRevision(self, branch, revision_id):
        """
        Generate changeset for the given Bzr revision
        """
        from changes import ChangesetEntry, Changeset
        from datetime import datetime

        revision = branch.repository.get_revision(revision_id)
        deltatree = branch.get_revision_delta(branch.revision_id_to_revno(revision_id))
        entries = []

        for delta in deltatree.added:
            e = ChangesetEntry(delta[0])
            e.action_kind = ChangesetEntry.ADDED
            entries.append(e)

        for delta in deltatree.removed:
            e = ChangesetEntry(delta[0])
            e.action_kind = ChangesetEntry.DELETED
            entries.append(e)

        for delta in deltatree.renamed:
            e = ChangesetEntry(delta[1])
            e.action_kind = ChangesetEntry.RENAMED
            e.old_name = delta[0]
            entries.append(e)

        for delta in deltatree.modified:
            e = ChangesetEntry(delta[0])
            e.action_kind = ChangesetEntry.UPDATED
            entries.append(e)

        return Changeset(revision.revision_id,
                         datetime.fromtimestamp(revision.timestamp),
                         revision.committer,
                         revision.message,
                         entries)

    def _getUpstreamChangesets(self, sincerev):
        """
        See what other revisions exist upstream and return them
        """
        parent_branch = BzrDir.open(self.repository.repository).open_branch()
        branch = self._working_tree.branch
        revisions = branch.missing_revisions(parent_branch)
        branch.fetch(parent_branch)

        for revision_id in revisions:
            yield self._changesetFromRevision(parent_branch, revision_id)

    def _applyChangeset(self, changeset):
        """
        Apply the given changeset to the working tree
        """
        parent_branch = BzrDir.open(self.repository.repository).open_branch()
        self._working_tree.lock_write()
        self.log.info('Updating to "%s"', changeset.revision)
        try:
            count = self._working_tree.pull(parent_branch,
                                            stop_revision=changeset.revision)
            conflicts = self._working_tree.update()
        finally:
            self._working_tree.unlock()
        self.log.debug("%s updated to %s",
                       ', '.join([e.name for e in changeset.entries]),
                       changeset.revision)
        if (count != 1) or conflicts:
            raise ChangesetApplicationFailure('unknown reason')
        return [] # No conflict handling yet

    def _checkoutUpstreamRevision(self, revision):
        """
        Initial checkout of upstream branch, equivalent of 'bzr branch -r',
        and return the last changeset.
        """
        parent_bzrdir = BzrDir.open(self.repository.repository)
        parent_branch = parent_bzrdir.open_branch()

        if revision == "INITIAL":
            revid = parent_branch.get_rev_id(1)
        elif revision == "HEAD":
            revid = None
        else:
            revid = revision

        self.log.info('Extracting %s out of "%s" in "%s"...',
                      revid, parent_bzrdir.root_transport.base, self.basedir)
        bzrdir = parent_bzrdir.sprout(self.basedir, revid)
        self._working_tree = bzrdir.open_workingtree()

        return self._changesetFromRevision(parent_branch, revid)

    #################################
    ## SynchronizableTargetWorkingDir

    def _addPathnames(self, entries):
        """
        Add entries to working tree.

        This method may get invoked several times with the same files
        (entries). Bzrlib complains if you try to add a file which is already
        versioned. This method filters these out. A file might already been
        marked to be added in this changeset, or might be a target in a rename
        operation. Remove those entries too.

        This method does not catch any errors from the adding through bzrlib,
        since they are **real** errors.
        """
        last_revision = self._working_tree.branch.last_revision()
        if last_revision is None:
            # initial revision
            new_entries = entries
        else:
            new_entries = []
            basis_tree = self._working_tree.branch.basis_tree()
            inv = basis_tree.inventory
            diff = compare_trees(basis_tree, self._working_tree)
            added = ([new[0] for new in diff.added] +
                     [renamed[1] for renamed in diff.renamed])

            def parent_was_copied(n):
                for p in added:
                    if n.startswith(p+'/'):
                        return True
                return False

            for e in entries:
                if (not inv.has_filename(e)
                    and not e in added
                    and not parent_was_copied(e)):
                    new_entries.append(e)
                else:
                    self.log.debug('"%s" already in inventory, skipping', e)

        if len(new_entries) == 0:
            return

        self.log.info('Adding "%s"...', ', '.join(new_entries))
        self._working_tree.add(new_entries)

    def _commit(self, date, author, patchname, changelog=None, entries=None):
        """
        Commit the changeset.
        """
        from time import mktime
        from binascii import hexlify
        from re import search
        from bzrlib.osutils import compact_date, rand_bytes

        logmessage = []
        if patchname:
            logmessage.append(patchname)
        if changelog:
            logmessage.append(changelog)
        if logmessage:
            self.log.info('Committing "%s"...', logmessage[0])
            logmessage = '\n'.join(logmessage)
        else:
            self.log.info('Committing...')
            logmessage = "Empty changelog"
        timestamp = int(mktime(date.timetuple()))

        # Guess sane email address
        email = search("<(.*@.*)>", author)
        if email:
            email = email.group(1)
        else:
            email = author

        revision_id = "%s-%s-%s" % (email, compact_date(timestamp),
                                    hexlify(rand_bytes(8)))
        self._working_tree.commit(logmessage, committer=author,
                                  specific_files=entries, rev_id=revision_id,
                                  verbose=self.repository.projectref().verbose,
                                  timestamp=timestamp)

    def _removePathnames(self, entries):
        """
        Remove entries from the tree.
        """
        self.log.info('Removing %s...', ', '.join(entries))
        self._working_tree.remove(entries)

    def _renamePathname(self, oldentry, newentry):
        """
        Rename a file from oldentry to newentry.
        """
        from os import rename
        from os.path import join

        # bzr does the rename itself as well
        self.log.debug('Renaming "%s" back to "%s"', newentry, oldentry)
        rename(join(self.basedir, newentry), join(self.basedir, oldentry))

        self.log.info('Renaming "%s" to "%s"...', oldentry, newentry)
        self._working_tree.rename_one(oldentry, newentry)

    def _prepareTargetRepository(self):
        """
        Create a branch with a working tree at the base directory. If the base
        directory is inside a Bazaar-NG style "shared repository", it will use
        that to create a branch and working tree (make sure it allows working
        trees).
        """
        from os.path import join, exists, split
        from bzrlib import IGNORE_FILENAME

        if self._working_tree is None:
            ignored = []

            # Omit our own log...
            logfile = self.repository.projectref().logfile
            dir, file = split(logfile)
            if dir == self.basedir:
                ignored.append(file)

            # ... and state file
            sfname = self.repository.projectref().state_file.filename
            dir, file = split(sfname)
            if dir == self.basedir:
                ignored.append(file)
                ignored.append(file+'.old')
                ignored.append(file+'.journal')

            if ignored:
                bzrignore = open(join(self.basedir, IGNORE_FILENAME), 'wU')
                bzrignore.write('\n'.join(ignored))

            self.log.info('Initializing new repository in "%s"...',
                          self.basedir)
            try:
                bzrdir = BzrDir.open(self.basedir)
            except errors.NotBranchError:
                # really a NotBzrDir error...
                branch = BzrDir.create_branch_convenience(self.basedir,
                                                          force_new_tree=True)
                self._working_tree = branch.bzrdir.open_workingtree()
            else:
                bzrdir.create_branch()
                self._working_tree = bzrdir.create_workingtree()
