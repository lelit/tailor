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

CONFLICTS_PROMPT = """
The changeset

%s
caused conflicts on the following files:

 * %s

Either abort the session with Ctrl-C, or manually correct the situation
with a Ctrl-Z and a few "svn resolved". What would you like to do?
"""

class ChangesetApplicationFailure(Exception):
    pass

class UpdatableSourceWorkingDir(object):
    """
    This is an abstract working dir able to follow an upstream
    source of `changesets`.

    It has two main functionalities:

    getUpstreamChangesets
        to query the upstream server about new changesets
    
    applyUpstreamChangesets
        to apply them to the working directory

    checkoutUpstreamRevision
        to extract a new copy of the sources, actually initializing
        the mechanism.
      
    Subclasses MUST override at least the _underscoredMethods.
    """

    def applyUpstreamChangesets(self, root, changesets, applyable=None,
                                replay=None, applied=None, logger=None,
                                delayed_commit=False):
        """
        Apply the collected upstream changes.

        Loop over the collected changesets, doing whatever is needed
        to apply each one to the working dir and if the changes do
        not raise conflicts call the `replay` function to mirror the
        changes on the target.

        Return a tuple of two elements:

        - the last applied changeset, if any
        - the sequence (potentially empty!) of conflicts.
        """

        c = None
        conflicts = []
        for c in changesets:
            if not self._willApplyChangeset(root, c, applyable):
                continue
            
            if logger:
                logger.info("Applying changeset %s", c.revision)

            try:
                res = self._applyChangeset(root, c, logger=logger)
            except:
                if logger:
                    logger.critical("Couldn't apply changeset %s",
                                    c.revision, exc_info=True)
                    logger.debug(str(c))
                raise
            
            if res:
                conflicts.append((c, res))
                try:
                    raw_input(CONFLICTS_PROMPT % (str(c), '\n * '.join(res)))
                except KeyboardInterrupt:
                    if logger: logger.info("INTERRUPTED BY THE USER!")
                    return c, conflicts

            if replay:
                replay(root, c, delayed_commit=delayed_commit, logger=logger)
            
            if applied:
                applied(root, c)
                
        return c, conflicts

    def _willApplyChangeset(self, root, changeset, applyable=None):
        """
        This gets called just before applying each changeset.  The action
        won't be carried out if this returns False.

        Subclasses may use this to skip some changeset, or to do whatever
        before application.
        """

        if applyable:
            return applyable(root, changeset)
        else:
            return True

    def getUpstreamChangesets(self, root, sincerev):
        """
        Query the upstream repository about what happened on the
        sources since last sync, returning a sequence of Changesets
        instances.
        
        This method must be overridden by subclasses.
        """

        raise "%s should override this method" % self.__class__
        
    def _applyChangeset(self, root, changeset, logger=None):
        """
        Do the actual work of applying the changeset to the working copy.

        Subclasses should reimplement this method performing the
        necessary steps to *merge* given `changeset`, returning a list
        with the conflicts, if any.
        """

        raise "%s should override this method" % self.__class__

    def checkoutUpstreamRevision(self, root, repository, module, revision,
                                 **kwargs):
        """
        Extract a working copy from a repository.

        :root: the name of the directory (that **must** exists)
               that will contain the working copy of the sources under the
               *module* subdirectory

        :repository: the address of the repository (the format depends on
                     the actual method used by the subclass)

        :module: the name of the module to extract
        
        :revision: extract that revision/branch

        Return the checked out revision.
        """

        return self._checkoutUpstreamRevision(root, repository,
                                              module, revision,
                                              **kwargs)
        
    def _checkoutUpstreamRevision(self, basedir, repository, module, revision,
                                  logger=None, **kwargs):
        """
        Concretely do the checkout of the upstream revision.
        """
        
        raise "%s should override this method" % self.__class__
