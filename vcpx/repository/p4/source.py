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
    def __getNativeChanges(self, sincerev):
        changes=p4lib.P4().changes(self.repository.repo_path + "...")
        changes.reverse()
        # Get rid of changes that are too low
        changes=filter(lambda c: int(c['change']) > sincerev, changes)
        return changes

    def __parseDate(self, d):
        return datetime.fromtimestamp(time.mktime(
            time.strptime(d, P4_DATE_FMT)), UTC)

    def __adaptChanges(self, changes):
        p4=p4lib.P4()
        descrs=[p4.describe(c['change'], shortForm=True) for c in changes]
        return [Changeset(d['change'], self.__parseDate(d['date']), \
            d['user'], d['description']) for d in descrs]

    def _getUpstreamChangesets(self, sincerev):
        return self.__adaptChanges(self.__getNativeChanges(sincerev))

    def __getLocalFilename(self, f, dp):
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

    def __ensureDirFor(self, lf):
        rv=False
        d=os.path.dirname(lf)
        if d != '' and not os.path.exists(d):
            rv=True
            os.makedirs(d)
        return rv

    def __getFiles(self, desc):
        p4=p4lib.P4()
        stuff={'add':[], 'delete':[], 'edit':[], 'integrate':[]}
        for f in desc['files']:
            lf=self.__getLocalFilename(f, self.repository.repo_path)
            fqlf=os.path.join(self.repository.basedir, lf)
            self.__ensureDirFor(fqlf)
            if f['action'] == 'delete':
                os.unlink(fqlf)
            else:
                p4.print_([f['depotFile'] + "#" + `f['rev']`], localFile=fqlf)
                assert os.path.exists(fqlf)
            stuff[f['action']].append(lf)
            self.log.debug("%s -> %s", str(f), str(lf))
        return stuff

    def _applyChangeset(self, changeset):
        stuff=self.__getFiles(p4lib.P4().describe(
            changeset.revision, shortForm=True))
        for k,v in stuff.iteritems():
            for f in v:
                e=changeset.addEntry(f, changeset.revision)
                if k == 'add':
                    e.action_kind = e.ADDED
                elif k == 'delete':
                    e.action_kind = e.DELETED
                elif k in ['edit', 'integrate']:
                    e.action_kind = e.UPDATED
                else:
                    assert False
        return []

    def _checkoutUpstreamRevision(self, revision):
        if revision == 'INITIAL':
            revision = self.__getNativeChanges(-1)[0]['change']
        p4=p4lib.P4()
        desc=p4.describe(revision, shortForm=True)

        self.__getFiles(desc)

        ts=self.__parseDate(desc['date'])

        return Changeset(revision, ts, desc['user'], desc['description'])
