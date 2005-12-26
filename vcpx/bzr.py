# -*- mode: python; coding: utf-8 -*-
# :Progetto: vcpx -- bazaar-ng support using the bzrlib instead of the frontend
# :Creato:   Fri Aug 19 01:06:08 CEST 2005
# :Autore:   Johan Rydberg <jrydberg@gnu.org>
#            Jelmer Vernooij <jelmer@samba.org>
# :Licenza:  GNU General Public License
#

"""
This module implements the backends for Bazaar-NG.
"""

__docformat__ = 'reStructuredText'

from source import UpdatableSourceWorkingDir
from target import SyncronizableTargetWorkingDir, TargetInitializationFailure
from bzrlib.branch import Branch
from bzrlib.delta import compare_trees

class BzrWorkingDir(UpdatableSourceWorkingDir, SyncronizableTargetWorkingDir):
    ## UpdatableSourceWorkingDir

    def _changesetFromRevision(self, parent, revision):
        """
        Generate changeset for the given Bzr revision
        """
        from changes import ChangesetEntry, Changeset
        from datetime import datetime
        r = parent.get_revision(revision)

        deltatree = parent.get_revision_delta(parent.revision_id_to_revno(revision))
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

        return Changeset(r.revision_id,
                              datetime.fromtimestamp(r.timestamp),
                              r.committer,
                              r.message,
                              entries)

    def _getUpstreamChangesets(self, sincerev):
        """
        See what other revisions exist upstream and return them
        """
        from bzrlib import fetch

        parent = Branch.open(self.repository.repository)
        repo = self._getRepo()

        revisions = repo.missing_revisions(parent)
        fetch.greedy_fetch(repo, parent)

        for ri in revisions:
            yield self._changesetFromRevision(parent, ri)

    def _applyChangeset(self, changeset):
        """
        Apply given remote revision to workingdir
        """
        from bzrlib.merge import merge

        repo = self._getRepo()
        parent = Branch.open(self.repository.repository)

        oldrevno = repo.revno()
        self.log.info('Applying "%s" to current r%s', changeset.revision,
                      oldrevno)
        repo.append_revision(changeset.revision)
        merge((self.basedir, -1), (self.basedir, oldrevno),
              check_clean=False, this_dir=self.basedir)
        self.log.debug("%s updated to %s",
                       ', '.join([e.name for e in changeset.entries]),
                       changeset.revision)
        return [] # No conflicts for now

    def _checkoutUpstreamRevision(self, revision):
        """
        Initial checkout, equivalent of 'bzr branch -r ... '
        """
        from bzrlib.clone import copy_branch

        parent = Branch.open(self.repository.repository)

        if revision == "INITIAL":
            revid = parent.get_rev_id(1)
        elif revision == "HEAD":
            revid = None
        else:
            revid = revision

        self.log.info('Extracting r%s out of "%s" in "%s"...',
                      revid, parent, self.basedir)
        self._b = copy_branch(parent, self.basedir, revid)

        return self._changesetFromRevision(parent, revid)

    ## SyncronizableTargetWorkingDir

    def _addPathnames(self, entries):
        # This method may get invoked several times with the same
        # entries; and Branch.add complains if a file is already
        # versioned.  So go through the list and sort out entries that
        # is already versioned, since there is no need to add them.  A
        # file can also already have been marked to be added in this
        # changeset, or may be a target of a rename operation. Remove
        # those files too. Do not try to catch any errors from
        # Branch.add, since the they are _real_ errors.
        last_revision = self._b.last_revision()
        if last_revision is None:
            # initial revision
            new_entries = entries
        else:
            new_entries = []
            inv = self._b.get_inventory(self._b.last_revision())
            diff = compare_trees(self._b.revision_tree(last_revision),
                                 self._b.working_tree())
            added = ([new[0] for new in diff.added] +
                     [renamed[1] for renamed in diff.renamed])
            for e in entries:
                if not inv.has_filename(e) and not e in added:
                    new_entries.extend([e])
                else:
                    self.log.debug('"%s" already in inventory, skipping', e)

        if len(new_entries) == 0:
            return

        self.log.info('Adding %s...', ', '.join(new_entries))
        self._b.working_tree().add(new_entries)

    def _commit(self, date, author, patchname, changelog=None, entries=None):
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
        self._b.working_tree().commit(logmessage, committer=author,
                       specific_files=entries, rev_id=revision_id,
                       verbose=self.repository.projectref().verbose,
                       timestamp=timestamp)

    def _removePathnames(self, entries):
        """Remove a sequence of entries"""

        self.log.info('Removing %s...', ', '.join(entries))
        self._b.working_tree().remove(entries)

    def _renamePathname(self, oldentry, newentry):
        """Rename an entry"""

        from os import rename
        from os.path import join

        # bzr does the rename itself as well
        self.log.debug('Renaming "%s" back to "%s"', newentry, oldentry)
        rename(join(self.basedir, newentry), join(self.basedir, oldentry))

        self.log.info('Renaming "%s" to "%s"...', oldentry, newentry)
        self._b.working_tree().rename_one(oldentry, newentry)

    def _prepareTargetRepository(self):
        """
        Create the base directory if it doesn't exist, and the
        repository as well in the new working directory.
        """

        from os.path import join, exists, split
        from bzrlib import IGNORE_FILENAME

        if not exists(join(self.basedir, self.repository.METADIR)):
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
            self._b = Branch.initialize(self.basedir)
        else:
            self._b = Branch.open(self.basedir)

    def _getRepo(self):
        try:
            return self._b
        except AttributeError:
            self._b = Branch.open(self.basedir)
            return self._b
