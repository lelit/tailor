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
        sources since last sync, returning a sequence of Changesets
        instances.
        """

        return self._getUpstreamChangesets(self, root)
        
    def applyUpstreamChangesets(self, root, changesets, replay=None):
        """
        Apply the collected upstream changes.

        Loop over the collected changesets, doing whatever is needed
        to apply each one to the working dir and if the changes do
        not raise conflicts call the `replay` function to mirror the
        changes on the target.

        Return a sequence (potentially empty!) of conflicts.
        """

        conflicts = []
        for c in changesets:
            res = self._applyChangeset(root, c)
            if res:
                conflicts.append((c, res))
            else:
                if replay:
                    replay(root, c)
                    
        return conflicts
        
    def checkoutUpstreamRevision(self, root, repository, revision):
        """
        Extract a working copy from a repository.
        """

        from os.path import split

        basedir,module = split(root)
        
        self._checkoutUpstreamRevision(basedir, repository, module, revision)
        
    def _checkoutUpstreamRevision(self, basedir, repository, module, revision):
        """
        Concretely do the checkout of the upstream revision.
        """
        
        raise "%s should override this method" % self.__class__
