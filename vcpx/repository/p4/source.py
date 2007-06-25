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
import re

import p4lib

P4_DATE_FMT="%Y/%m/%d %H:%M:%S"

class P4SourceWorkingDir(UpdatableSourceWorkingDir):
    branchRE = re.compile(r'^branch from (?P<path>//.*?)#')

    def __getP4(self):
        p4=self.repository.EXECUTABLE
        args={}
        if self.repository.p4client is not None:
            args['client']=self.repository.p4client
        if self.repository.p4port is not None:
            args['port']=self.repository.p4port
        return p4lib.P4(p4=p4, **args)

    def __getNativeChanges(self, sincerev):
        changes=self.__getP4().changes(self.repository.depot_path + "...")
        changes.reverse()
        # Get rid of changes that are too low
        sincerev = int(sincerev)
        changes = [c for c in changes if int(c['change']) > sincerev]
        return changes

    def __parseDate(self, d):
        return datetime.fromtimestamp(time.mktime(
            time.strptime(d, P4_DATE_FMT)), UTC)

    def __adaptChanges(self, changes):
        # most of the info about a changeset is filled in later
        return [Changeset(str(c['change']), None, c['user'], None)
                for c in changes]

    def _getUpstreamChangesets(self, sincerev):
        return self.__adaptChanges(self.__getNativeChanges(sincerev))

    def _localFilename(self, f, dp=None):
        if dp is None:
            dp=self.repository.depot_path
        trans=string.maketrans(" ", "_")
        fn=f['depotFile']
        rv=fn
        if not fn.startswith(dp): return None

        rv=fn[len(dp):]
        if rv[0]=='/':
            rv=rv[1:]
        return rv

    def _applyChangeset(self, changeset):
        p4 = self.__getP4()
        desc = p4.describe(changeset.revision, shortForm=True)

        changeset.author = desc['user']
        changeset.date = self.__parseDate(desc['date'])
        changeset.log = desc['description']

        desc['files'] = [f for f in desc['files']
                         if self._localFilename(f) is not None]

        # check for added dirs
        for f in desc['files']:
            if f['action'] in ['add', 'branch']:
                name = self._localFilename(f)
                self._addParents(name, changeset)

        p4.sync('@' + str(changeset.revision))

        # dict of {path:str -> e:ChangesetEntry}
        branched = dict()
        for f in desc['files']:
            name = self._localFilename(f)
            path = f['depotFile']
            act = f['action']

            if act == 'branch':
                e = changeset.addEntry(name, changeset.revision)
                e.action_kind = e.ADDED

                log = p4.filelog(path+'#'+str(f['rev']), maxRevs=1)
                note = log[0]['revs'][0]['notes'][0]
                m = self.branchRE.match(note)
                if m:
                    old = m.group('path')
                    branched[old] = e
                    self.log.info('Branch %r to %r' % (old, name))

        for f in desc['files']:
            name = self._localFilename(f)
            path = f['depotFile']
            act = f['action']

            # branches were already handled
            if act == 'branch':
                continue

            # deletes might be renames
            if act == 'delete' and path in branched:
                e = branched[path]
                e.action_kind = e.RENAMED
                e.old_name = name
                self.log.info('Rename %r to %r' % (name, e.name))
                continue

            e = changeset.addEntry(name, changeset.revision)
            if act == 'add':
                e.action_kind = e.ADDED
            elif act == 'delete':
                e.action_kind = e.DELETED
            elif act in ['edit', 'integrate']:
                e.action_kind = e.UPDATED
            else:
                assert False

        # check for removed dirs
        for f in desc['files']:
            if f['action'] == 'delete':
                name = self._localFilename(f)
                self._delParents(name, changeset)

        changes = ','.join([repr(e.name) for e in changeset.entries])
        self.log.info('Updated %s', changes)

        return []

    # Perforce doesn't track directories, so we have to notice
    # when a file add implies a directory add.  Otherwise targets
    # like svn will barf.
    # xxx This is a little fragile, because it depends on having
    # a clean p4 workdir with sequential updates.  It might make
    # more sense for the svn target to notice missing dir adds.
    def _addParents(self, name, changeset):
        parent = os.path.dirname(name)
        if parent == '': return

        path = os.path.join(self.repository.basedir, parent)
        if os.path.exists(path): return

        self._addParents(parent, changeset)

        self.log.info('Adding dir %r' % parent)
        e = changeset.addEntry(parent, changeset.revision)
        e.action_kind = e.ADDED
        os.mkdir(path)

    # Try to guess when a directory should be removed.
    # xxx This is also kind of fragile
    def _delParents(self, name, changeset):
        parent = os.path.dirname(name)
        if parent == '': return

        path = os.path.join(self.repository.basedir, parent)
        if not os.path.exists(path): return
        if len(os.listdir(path)) > 0: return

        self.log.info('Removing dir %r' % parent)
        e = changeset.addEntry(parent, changeset.revision)
        e.action_kind = e.DELETED
        os.rmdir(path)

        self._delParents(parent, changeset)


    def _checkoutUpstreamRevision(self, revision):
        force=False
        if revision == 'INITIAL':
            revision = self.__getNativeChanges(-1)[0]['change']
            force=True
        p4=self.__getP4()
        desc=p4.describe(revision, shortForm=True)

        p4.sync('@' + str(revision), force=force)

        ts=self.__parseDate(desc['date'])

        return Changeset(revision, ts, desc['user'], desc['description'])
