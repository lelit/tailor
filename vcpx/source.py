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
    """This is an abstract working dir. Subclasses MUST override at least
       the _underscoredMethods."""

    def _getUpstreamChangesets(self, root):
        """
        Do the actual work of fetching the upstream changeset.
        
        This method must be overridden by subclasses.
        """

        raise "%s should override this method" % self.__class__
        
    def _applyChangeset(self, root, changeset):
        """
        Do the actual work of applying the changeset to the working copy.
        """

        raise "%s should override this method" % self.__class__

    def collectUpstreamChangesets(self, root):
        """
        Query the upstream repository about what happened on the
        sources since last sync, collecting a sequence of Changesets
        instances in the `changesets` slot.
        """

        self._getUpstreamChangesets(self, root)
        
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
        
