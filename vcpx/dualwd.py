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
from svn import SvnWorkingDir
from cvs import CvsWorkingDir
from cvsps import CvspsWorkingDir
from darcs import DarcsWorkingDir
from monotone import MonotoneWorkingDir
from cdv import CdvWorkingDir
from bzr import BzrWorkingDir
from hg import HgWorkingDir

IGNORED_METADIRS = ['.svn', '_darcs', 'CVS', '.cdv', 'MT', '.hg', '.bzr']

class DualWorkingDir(UpdatableSourceWorkingDir, SyncronizableTargetWorkingDir):
    """
    Dual working directory, one that is under two different VC systems at
    the same time.

    This class reimplements the two interfaces, dispatching the right method
    to the right backend.
    """

    def __init__(self, source_kind, target_kind):
        globs = globals()

        try:
            self.source = globs[source_kind.capitalize() + 'WorkingDir']()
        except KeyError, exp:
            raise InvocationError("Unhandled source VCS kind: " + source_kind)

        try:
            self.target = globs[target_kind.capitalize() + 'WorkingDir']()
        except KeyError, exp:
            raise InvocationError("Unhandled target VCS kind: " + target_kind)

        # UpdatableSourceWorkingDir

        self.getPendingChangesets = self.source.getPendingChangesets
        self.checkoutUpstreamRevision = self.source.checkoutUpstreamRevision

        # SyncronizableTargetWorkingDir

        self.prepareWorkingDirectory = self.target.prepareWorkingDirectory
        self.initializeNewWorkingDir = self.target.initializeNewWorkingDir
        self.commitDelayedChangesets = self.target.commitDelayedChangesets
        self.replayChangeset = self.target.replayChangeset

    def applyPendingChangesets(self, root, module, applyable=None,
                                replay=None, applied=None, logger=None,
                                delayed_commit=False):
        return self.source.applyPendingChangesets(root, module,
                                                  replay=self.replayChangeset,
                                                  applyable=applyable,
                                                  applied=applied,
                                                  logger=logger,
                                                  delayed_commit=delayed_commit)
