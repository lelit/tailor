#! /usr/bin/python
# -*- mode: python; coding: utf-8 -*-
# :Progetto: vcpx -- Dual working directory
# :Creato:   dom 20 giu 2004 11:02:01 CEST
# :Autore:   Lele Gaifax <lele@nautilus.homeip.net>
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

from source import UpdatableSourceWorkingDir
from target import SyncronizableTargetWorkingDir
from svn import SvnWorkingDir
from cvs import CvsWorkingDir
from cvsps import CvspsWorkingDir
from darcs import DarcsWorkingDir

class DualWorkingDir(UpdatableSourceWorkingDir, SyncronizableTargetWorkingDir):
    """
    Dual working directory, one that is under two different VC systems at
    the same time.

    This class reimplements the two interfaces, dispatching the right method
    to the right instance.
    """

    def __init__(self, source_kind, target_kind):
        globs = globals()
        
        self.source = globs[source_kind.capitalize() + 'WorkingDir']()
        self.target = globs[target_kind.capitalize() + 'WorkingDir']()

    ## UpdatableSourceWorkingDir

    def getUpstreamChangesets(self, root, sincerev):
        return self.source.getUpstreamChangesets(root, sincerev)
    
    def applyUpstreamChangesets(self, root, changesets,
                                replay=None, applied=None, logger=None,
                                delayed_commit=False):
        return self.source.applyUpstreamChangesets(root, changesets,
                                                   self.target.replayChangeset,
                                                   applied=applied,
                                                   logger=logger,
                                                   delayed_commit=delayed_commit)
        
    def checkoutUpstreamRevision(self, root, repository, module, revision,
                                 logger=None):
        return self.source.checkoutUpstreamRevision(root,
                                                    repository, module,
                                                    revision,
                                                    logger=logger)

    ## SyncronizableTargetWorkingDir
    
    def initializeNewWorkingDir(self, root, repository, module, revision):
        self.target.initializeNewWorkingDir(root, repository, module, revision)

    def commitDelayedChangesets(self, root, concatenate_logs):
        self.target.commitDelayedChangesets(root, concatenate_logs)
