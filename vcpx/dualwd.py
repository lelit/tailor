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

class DualWorkingDir(UpdatableSourceWorkingDir, SyncronizableTargetWorkingDir):
    """
    Dual working directory, one that is under two different VC systems at
    the same time.

    This class reimplements the two interfaces, dispatching the right method
    to the right instance.
    """

    def __init__(self, source_kind, target_kind):
        self.source_kind = source_kind
        self.target_kind = target_kind

        ## XXX these need class registering machinery!
        
        self.source = source.get(source_kind.capitalize() + 'WorkingDir')()
        self.target = target.get(source_kind.capitalize() + 'WorkingDir')()

    ## UpdatableSourceWorkingDir
        
    def collectUpstreamChangesets(self, root):
        return self.source._getUpstreamChangesets(self, root)

    def applyUpstreamChangesets(self, root, changesets, replay=None):
        return self.source.applyUpstreamChangesets(root, changesets,
                                                   self.replayChangeset)
        
    def checkoutUpstreamRevision(self, root, repository, revision):
        return self.source.checkoutUpstreamRevision(root, repository, revision)

    ## SyncronizableTargetWorkingDir
    
    def initializeNewWorkingDir(self, root, repository, revision):
        self.target.initializeNewWorkingDir(root, repository, revision)
        
    def commitChangeset(self, root, changeset):
        self.target.commitChangeset(root, changeset)
        
    def replayChangeset(self, root, changeset):
        self.target.replayChangeset(root, changeset)
        self.target.commitChangeset(root, changeset)
        
