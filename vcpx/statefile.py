# -*- mode: python; coding: utf-8 -*-
# :Progetto: vcpx -- Persistent information details
# :Creato:   ven 19 ago 2005 22:53:18 CEST
# :Autore:   Lele Gaifax <lele@nautilus.homeip.net>
# :Licenza:  GNU General Public License
#

"""
Tailor needs a generic way to remember which was the last migrated
revision between the two repositories.  For some backends it could
derive such information directly from the working dir/repository,
others have no such capability.

Moreover, since fetching and digesting the history to produce a
sequence of ChangeSets it's time and bandwidth consuming, the state
file helps keeping a cache of pending changes.
"""

__docformat__ = 'reStructuredText'

from cPickle import load, dump
from signal import signal, SIGINT, SIG_IGN

class StateFile(object):
    """
    State file that stores current revision and pending changesets.

    It behaves as an iterator, and source backends loop over not yet
    applied changesets, calling .applied() after each one: that writes
    the applied changeset in a *journal* file, much more atomic than
    rewriting the whole archive each time.

    When the source backend finishes it's job, either because there
    are no more pending changeset or stopped by an error, it calls
    .finalize(), that in presence of a journal file adjust the
    archive filtering out already applied changesets.

    Should an hard error prevent .finalize() call, it will happen
    automatically next time the state file is loaded.
    """

    def __init__(self, fname, config):
        """
        Initialize a new instance, logging to `tailor.statefile`.
        """

        from logging import getLogger

        self.filename = fname
        self.archive = None
        self.last_applied = None
        self.current = None
        self.log = getLogger('tailor.statefile')

    def _load(self):
        """
        Open the pickle file and load the last applied changeset.
        The second pickled object is ignored for backward compatibility.
        """

        # Take care of the journal file, if present.
        self.finalize()

        self.current = None
        try:
            self.archive = open(self.filename)
            self.last_applied = load(self.archive)
            # compatibility dummity: there was the queuelen here
            load(self.archive)
        except IOError:
            self.archive = None
            self.last_applied = None

    def _write(self, changesets):
        """
        Write the state file, that is dump last applied changeset,
        a dummy None, then one changeset at a time.
        """

        count = 0
        previous = signal(SIGINT, SIG_IGN)
        try:
            sf = open(self.filename, 'w')
            dump(self.last_applied, sf)
            dump(None, sf)
            for cs in changesets:
                dump(cs, sf)
                count += 1
            sf.close()
        finally:
            signal(SIGINT, previous)
        self.log.info('Cached information about %d pending changesets', count)

    def __str__(self):
        return self.filename

    def __iter__(self):
        return self

    def next(self):
        if not self.archive:
            raise StopIteration
        try:
            self.current = load(self.archive)
        except EOFError:
            self.archive.close()
            self.archive = None
            raise StopIteration
        return self.current

    def pending(self):
        """
        Verify if there's at least one changeset still pending.
        """

        if self.archive is None:
            self._load()
        if self.archive is None:
            return False

        pos = self.archive.tell()
        try:
            next = load(self.archive)
        except EOFError:
            next = None
        self.archive.seek(pos)
        return next is not None

    def applied(self, current=None):
        """
        Write the applied changeset to the journal file.
        """

        previous = signal(SIGINT, SIG_IGN)
        try:
            self.last_applied = current or self.current
            journal = open(self.filename + '.journal', 'w')
            dump(self.last_applied, journal)
            journal.close()
        finally:
            signal(SIGINT, previous)

    def finalize(self):
        """
        If there is a journal file, adjust the archive accordingly,
        dropping already applied changesets.
        """

        from os.path import exists
        from os import unlink, rename

        previous = signal(SIGINT, SIG_IGN)
        try:
            if self.archive is not None:
                self.archive.close()
                self.archive = None

            if exists(self.filename + '.journal'):
                self.log.debug('Adjusting the state accordingly to journal')
                # Load last applied changeset from the journal
                journal = open(self.filename + '.journal')
                last_applied = load(journal)
                journal.close()

                # If there is an actual archive (ie, this is not
                # bootstrap time) load the changesets from there,
                # skipping the changesets until the last_applied one,
                # then transfer the remaining to the new archive.
                if exists(self.filename):
                    old = open(self.filename)
                    load(old) # last applied
                    load(old) # dummy queuelen
                    try:
                        cs = load(old)
                        # Skip already applied changesets
                        while cs <> last_applied:
                            cs = load(old)
                    except EOFError:
                        cs = None
                    sf = open(self.filename + '.new', 'w')
                    dump(last_applied, sf)
                    dump(None, sf)
                    if cs is not None:
                        count = 0
                        while True:
                            try:
                                cs = load(old)
                            except EOFError:
                                break
                            dump(cs, sf)
                            count += 1
                        self.log.info('%d pending changesets in state file',
                                       count)
                    sf.close()
                    old.close()

                    oldname = self.filename + '.old'
                    if exists(oldname):
                        unlink(oldname)
                    rename(self.filename, oldname)
                    rename(sf.name, self.filename)
                else:
                    sf = open(self.filename, 'w')
                    dump(last_applied, sf)
                    dump(None, sf)
                    sf.close()

                unlink(journal.name)
        finally:
            signal(SIGINT, previous)

    def lastAppliedChangeset(self):
        """
        Return the last applied changeset, if any, None otherwise.
        """

        if self.archive is None:
            self._load()
        return self.last_applied

    def setPendingChangesets(self, changesets):
        """
        Write pending changesets to the state file.
        """

        if self.archive is not None:
            self.archive.close()
            self.archive = None

        self._write(changesets)
        self._load()
