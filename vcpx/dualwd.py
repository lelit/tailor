# -*- mode: python; coding: utf-8 -*-
# :Progetto: vcpx -- Dual working directory
# :Creato:   dom 20 giu 2004 11:02:01 CEST
# :Autore:   Lele Gaifax <lele@nautilus.homeip.net>
# :Licenza:  GNU General Public License
#

"""
The easiest way to propagate changes from one VC control system to one
of an another kind is having a single directory containing a live
working copy shared between the two VC systems.

In a slightly more elaborated way, the source and the target system may
use separate directories, that gets rsynced when needed.

This module implements `DualWorkingDir`, which instances have a
`source` and `target` properties offering the right capabilities to do
the job.
"""

__docformat__ = 'reStructuredText'

from source import UpdatableSourceWorkingDir, InvocationError
from target import SynchronizableTargetWorkingDir
from shwrap import ExternalCommand
from datetime import datetime

IGNORED_METADIRS = []

class DualWorkingDir(UpdatableSourceWorkingDir, SynchronizableTargetWorkingDir):
    """
    Dual working directory, one that is under two different VC systems at
    the same time.

    This class reimplements the two interfaces, dispatching the right method
    to the right backend.
    """

    def __init__(self, source_repo, target_repo):
        global IGNORED_METADIRS
        from os.path import sep

        self.source = source_repo.workingDir()
        self.target = target_repo.workingDir()

        sbdir = self.source.repository.basedir.rstrip(sep)+sep
        tbdir = self.target.repository.basedir.rstrip(sep)+sep
        if sbdir == tbdir:
            shared = True
        elif tbdir.startswith(sbdir):
            raise InvocationError('Target base directory "%s" cannot be a '
                                  'subdirectory of source directory "%s"' %(
                (tbdir, sbdir)))
        elif sbdir.startswith(tbdir):
            shared = True
        else:
            shared = False
        self.shared_basedirs = shared
        self.source.shared_basedirs = shared
        self.target.shared_basedirs = shared

        IGNORED_METADIRS = filter(None, [source_repo.METADIR,
                                         target_repo.METADIR])
        IGNORED_METADIRS.extend(source_repo.EXTRA_METADIRS)
        IGNORED_METADIRS.extend(target_repo.EXTRA_METADIRS)

        self.source.prepareSourceRepository()
        self.target.prepareTargetRepository()

        # UpdatableSourceWorkingDir

        self.getPendingChangesets = self.source.getPendingChangesets
        self.checkoutUpstreamRevision = self.source.checkoutUpstreamRevision

        # SynchronizableTargetWorkingDir

        self.prepareWorkingDirectory = self.target.prepareWorkingDirectory

    def setStateFile(self, state_file):
        """
        Set the state file used to store the revision and pending changesets.
        """

        self.source.setStateFile(state_file)
        self.target.setStateFile(state_file)

    def setLogfile(self, logfile):
        """
        Set the name of the logfile, just to ignore it.
        """

        self.target.logfile = logfile

    def applyPendingChangesets(self, applyable=None, replay=None, applied=None):
        def pre_replay(changeset):
            if applyable and not applyable(changeset):
                return
            return self.target._prepareToReplayChangeset(changeset)

        return self.source.applyPendingChangesets(replay=self.replayChangeset,
                                                  applyable=pre_replay,
                                                  applied=applied)

    def importFirstRevision(self, source_repo, changeset, initial):
        if not self.shared_basedirs:
            self._syncTargetWithSource()
        self.target.importFirstRevision(source_repo, changeset, initial)

    def replayChangeset(self, changeset):
        if not self.shared_basedirs:
            self._saveRenamedTargets(changeset)
            self._syncTargetWithSource()
        self.target.replayChangeset(changeset)

    def _syncTargetWithSource(self):
        cmd = ['rsync', '--archive']
        now = datetime.now()
        if hasattr(self, '_last_rsync'):
            last = self._last_rsync
            if not (now-last).seconds:
                cmd.append('--ignore-times')
        self._last_rsync = now
        for M in IGNORED_METADIRS:
            cmd.extend(['--exclude', M])

        rsync = ExternalCommand(command=cmd)
        rsync.execute(self.source.repository.basedir+'/', self.target.repository.basedir)

    def _saveRenamedTargets(self, changeset):
        """
        Save old names from `rename`, before rsync replace it with new file.
        """

        from os.path import join, exists
        from os import rename

        for e in changeset.entries:
            if e.action_kind == e.RENAMED:
                absold = join(self.target.repository.basedir, e.old_name)
                if exists(absold):
                    rename(absold, absold + '-TAILOR-HACKED-OLD-NAME')
