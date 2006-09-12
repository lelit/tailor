# -*- mode: python; coding: utf-8 -*-
# :Progetto: vcpx -- mock source backend
# :Creato:   Sun Jul 16 02:50:04 CEST 2006
# :Autore:   Adeodato Simó <dato@net.com.org.es>
# :Licenza:  GNU General Public License
#

"""
This module implements a mock source backend to be used in tests.
"""

__docformat__ = 'reStructuredText'

import os
from shutil import rmtree
from datetime import datetime, timedelta

from vcpx.tzinfo import UTC
from vcpx import TailorBug
from vcpx.repository import Repository
from vcpx.source import UpdatableSourceWorkingDir
from vcpx.changes import Changeset, ChangesetEntry


class MockRepository(Repository):
    def create(self):
        if not os.path.isdir(self.basedir):
            os.makedirs(self.basedir)


class MockWorkingDir(UpdatableSourceWorkingDir):
    def __init__(self, *args, **kwargs):
        super(MockWorkingDir, self).__init__(*args, **kwargs)
        self.rev_offset = 0
        self.changesets = []

    def _getUpstreamChangesets(self, sincerev):
        return self.changesets[sincerev-self.rev_offset:]

    def _applyChangeset(self, changeset):
        for e in changeset.entries:
            e.apply(self.repository.basedir)

        return []

    def _checkoutUpstreamRevision(self, revision):
        if revision == 'INITIAL':
            cset = self.changesets[0]
            self.rev_offset = cset.revision - 1
            self._applyChangeset(cset)
            return cset
        else:
            raise TailorBug("Don't know what to do!")

    def _get_changesets(self):
        if not self.__changesets:
            raise TailorBug("Attempted to use empty MockWorkingDir!")
        return self.__changesets

    def _set_changesets(self, changesets):
        self.__changesets = changesets

    changesets = property(_get_changesets, _set_changesets)


class MockChangeset(Changeset):
    def __init__(self, log, entries):
        super(MockChangeset, self).__init__(MockChangeset.Rev.next(),
                MockChangeset.Date.next(), None, log, entries)

    def Rev():
        initial = 0

        while True:
            initial += 1
            yield initial

    def Date():
        initial = datetime.now(UTC)
        step = timedelta(seconds=1)

        while True:
            initial += step
            yield initial

    Rev  = Rev()
    Date = Date()


class MockChangesetEntry(ChangesetEntry):
    def __init__(self, action, name, old_name=None, contents=None):
        super(MockChangesetEntry, self).__init__(name)

        self.isdir       = False
        self.contents    = contents
        self.old_name    = old_name
        self.action_kind = action

        if self.name[-1] == '/':
            self.isdir = True
            self.name  = self.name[:-1]

    def apply(self, where):
        name = os.path.join(where, self.name)
        if self.action_kind == self.ADDED:
            if self.isdir:
                os.makedirs(name)
            else:
                dirname = os.path.dirname(name)
                if not os.path.exists(dirname):
                    os.makedirs(dirname)
                f = file(name, 'w')
                if self.contents is not None:
                    f.write(self.contents)
                f.close()
        elif self.action_kind == self.DELETED:
            if os.path.exists(name):
                if self.isdir:
                    rmtree(name)
                else:
                    os.unlink(name)
        elif self.action_kind == self.RENAMED:
            old_name = os.path.join(where, self.old_name)
            if os.path.exists(old_name):
                os.rename(old_name, name)
        elif self.action_kind == self.UPDATED:
            if self.contents is not None:
                f = file(name, 'w')
                f.write(self.contents)
            else: # update timestamp
                f = file(name, 'w+')
            f.close()
        else:
            raise TailorBug("Unknown ChangesetEntry.action_kind: %s" % str(self.action_kind))
