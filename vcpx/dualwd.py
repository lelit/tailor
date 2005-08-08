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

This module implements `DualWorkingDir`, which instances have a
`source` and `target` properties offering the right capabilities to do
the job.
"""

__docformat__ = 'reStructuredText'

from source import UpdatableSourceWorkingDir, InvocationError
from target import SyncronizableTargetWorkingDir

IGNORED_METADIRS = []

class DualWorkingDir(UpdatableSourceWorkingDir, SyncronizableTargetWorkingDir):
    """
    Dual working directory, one that is under two different VC systems at
    the same time.

    This class reimplements the two interfaces, dispatching the right method
    to the right backend.
    """

    def __init__(self, source_repo, target_repo):
        global IGNORED_METADIRS

        self.source = source_repo.workingDir()
        self.target = target_repo.workingDir()

        IGNORED_METADIRS = [source_repo.METADIR, target_repo.METADIR]

        # UpdatableSourceWorkingDir

        self.setStateFile = self.source.setStateFile
        self.getPendingChangesets = self.source.getPendingChangesets
        self.checkoutUpstreamRevision = self.source.checkoutUpstreamRevision

        # SyncronizableTargetWorkingDir

        self.prepareWorkingDirectory = self.target.prepareWorkingDirectory
        self.initializeNewWorkingDir = self.target.initializeNewWorkingDir
        self.replayChangeset = self.target.replayChangeset

    def applyPendingChangesets(self, applyable=None, replay=None, applied=None):
        return self.source.applyPendingChangesets(replay=self.replayChangeset,
                                                  applyable=applyable,
                                                  applied=applied)
