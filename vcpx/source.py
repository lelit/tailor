#! /usr/bin/python
# -*- mode: python; coding: utf-8 -*-
# :Progetto: vcpx -- Updatable VC working directory
# :Creato:   mer 09 giu 2004 13:55:35 CEST
# :Autore:   Lele Gaifax <lele@nautilus.homeip.net>
#

"""
Updatable sources are the simplest abstract wrappers around a working
directory under some kind of version control system.
"""

__docformat__ = 'reStructuredText'


class UpdatableSourceWorkingDir(object):
    """This is an abstract working dir. Subclasses MUST override ALL
       these methods."""

    def _getLastSyncedRevision(self, root):
        """
        Return the last synced revision.

        Since this info must be stored somewhere, it's up to the target
        storage how/where it best fits; as such, this method must be
        overridden by subclasses.
        """

        raise "SubclassResponsibility"

    def _setLastSyncedRevision(self, root, revision):
        """
        Record the last synced revision.

        Since this info must be stored somewhere, it's up to the target
        storage how/where it best fits; as such, this method must be
        overridden by subclasses.
        """

        raise "SubclassResponsibility"

    def _getUpstreamChangesets(self, root, startfrom_rev=None):
        """
        Do the actual work of fetching the upstream changeset.
        
        This method must be overridden by subclasses.
        """

        raise "SubclassResponsibility"
        
    def _applyChangeset(self, root, changeset):
        """
        Do the actual work of applying the changeset to the workink copy.
        """

        raise "SubclassResponsibility"

    def collectUpstreamChangesets(self, root):
        """
        Query the upstream repository about what happened on the
        sources since last sync, collecting a sequence of Changesets
        instances in the `changesets` slot.
        """

        lastrev = self._getLastSyncedRevision(root)
        return self._getUpstreamChangesets(self, root, startfrom_rev=lastrev)
        
    def applyUpstreamChangesets(self, root, changesets):
        """
        Apply the collected upstream changes.

        Loop over the collected changesets, doing whatever is needed
        to apply each one to the working dir.

        Return a sequence (potentially emtpy!) of conflicts.
        """

        conflicts = []
        for c in self.changesets:
            res = self._applyChangeset(root, c)
            if res:
                conflicts.append((c, res))

        return conflicts
        
