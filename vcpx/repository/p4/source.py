# -*- mode: python; coding: utf-8 -*-
# :Progetto: vcpx -- p4 source
# :Creato:   Fri Mar 16 23:06:43 PDT 2007
# :Autore:   Dustin Sallings <dustin@spy.net>
# :Licenza:  GNU General Public License
#

"""
This module implements the source backend for p4.
"""

__docformat__ = 'reStructuredText'

from vcpx.shwrap import ExternalCommand, PIPE
from vcpx.config import ConfigurationError
from vcpx.source import UpdatableSourceWorkingDir, GetUpstreamChangesetsFailure
from vcpx.source import ChangesetApplicationFailure
from vcpx.changes import Changeset
from vcpx.tzinfo import UTC

from datetime import datetime
import exceptions
import string
import time
import os

import p4lib

P4_DATE_FMT="%Y/%m/%d %H:%M:%S"

class NotForMe(exceptions.Exception):
    def __init__(self, s):
        self.s=s
    def __repr__(self):
        "<NotForMe:  " + self.s + ">"
    __str__=__repr__

class P4SourceWorkingDir(UpdatableSourceWorkingDir):
    def __getP4(self):
        p4=self.repository.EXECUTABLE
        args={}
        if self.repository.p4client is not None:
            args['client']=self.repository.p4client
        if self.repository.p4port is not None:
            args['port']=self.repository.p4port
        return p4lib.P4(p4=p4, **args)

    def __getNativeChanges(self, sincerev):
        changes=self.__getP4().changes(self.repository.depo_path + "...")
        changes.reverse()
        # Get rid of changes that are too low
        changes=filter(lambda c: int(c['change']) > sincerev, changes)
        return changes

    def __parseDate(self, d):
        return datetime.fromtimestamp(time.mktime(
            time.strptime(d, P4_DATE_FMT)), UTC)

    def __adaptChanges(self, changes):
        p4=self.__getP4()
        descrs=[p4.describe(c['change'], shortForm=True) for c in changes]
        return [Changeset(d['change'], self.__parseDate(d['date']), \
            d['user'], d['description']) for d in descrs]

    def _getUpstreamChangesets(self, sincerev):
        return self.__adaptChanges(self.__getNativeChanges(sincerev))

    def __getLocalFilename(self, f, dp=None):
        if dp is None:
            dp=self.repository.depo_path
        trans=string.maketrans(" ", "_")
        fn=f['depotFile']
        rv=fn
        if fn.startswith(dp):
            rv=fn[len(dp):]
            if rv[0]=='/':
                rv=rv[1:]
        else:
            raise NotForMe(f)
        return rv

    def _applyChangeset(self, changeset):
        p4=self.__getP4()
        desc=p4.describe(changeset.revision, shortForm=True)
        p4.sync('@' + str(changeset.revision))
        for f in desc['files']:
            try:
                e=changeset.addEntry(self.__getLocalFilename(f),
                    changeset.revision)
                k=f['action']
                self.log.debug("action on file: %s", str(f))
                if k in ['add', 'branch']:
                    e.action_kind = e.ADDED
                elif k == 'delete':
                    e.action_kind = e.DELETED
                elif k in ['edit', 'integrate']:
                    e.action_kind = e.UPDATED
                else:
                    assert False
            except NotForMe:
                pass
        return []

    def _checkoutUpstreamRevision(self, revision):
        if revision == 'INITIAL':
            revision = self.__getNativeChanges(-1)[0]['change']
        p4=self.__getP4()
        desc=p4.describe(revision, shortForm=True)

        p4.sync('@' + str(revision))

        ts=self.__parseDate(desc['date'])

        return Changeset(revision, ts, desc['user'], desc['description'])
