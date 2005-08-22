# -*- mode: python; coding: utf-8 -*-
# :Progetto: vcpx -- bazaar-ng support using the bzrlib instead of the frontend
# :Creato:   Fri Aug 19 01:06:08 CEST 2005
# :Autore:   Johan Rydberg <jrydberg@gnu.org>
# :Licenza:  GNU General Public License
#

"""
This module implements the backends for Bazaar-NG.
"""

__docformat__ = 'reStructuredText'

from target import SyncronizableTargetWorkingDir, TargetInitializationFailure
from bzrlib.branch import Branch
from bzrlib.errors import BzrError

class BzrngWorkingDir(SyncronizableTargetWorkingDir):
    def _addPathnames(self, entries):
        # This method may get invoked several times with the same
        # entries; and Branch.add complains if a file is already
        # versioned.  So go through the list and sort out entries that
        # is already versioned, since there is no need to add them.
        # Do not try to catch any errors from Branch.add, since the
        # they are _real_ errors.
        new_entries = []
        for e in entries:
            if not self._b.inventory.has_filename(e):
                new_entries.extend([e])

        if len(new_entries) == 0:
            return
        self._b.add(new_entries)

    def _commit(self, date, author, patchname, changelog=None, entries=None):
        from time import mktime

        # FIXME: maybe we should construct the revision id here instead?
        #revision_id = "%s-%d" % (author, timestamp)
        logmessage = []
        if patchname:
            logmessage.append(patchname)
        if changelog:
            logmessage.append(changelog)
        timestamp = int(mktime(date.timetuple()))
        self._b.commit('\n'.join(logmessage), committer=author,
                       specific_files=entries,
                       verbose=self.repository.project.verbose,
                       timestamp=timestamp)

    def _removePathnames(self, entries):
        """Remove a sequence of entries"""

        self._b.remove(entries)

    def _renamePathname(self, oldentry, newentry):
        """Rename an entry"""

        self._b.rename_one(oldentry, newentry)

    def _prepareTargetRepository(self):
        """
        Create the base directory if it doesn't exist, and the
        repository as well in the new working directory.
        """

        from os.path import join, exists
        from os import makedirs

        if not exists(self.basedir):
            makedirs(self.basedir)

        if not exists(join(self.basedir, self.repository.METADIR)):
            self._b = Branch(self.basedir, init=True, find_root=False)
        else:
            self._b = Branch(self.basedir, init=False, find_root=True)
