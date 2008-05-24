# -*- mode: python; coding: utf-8 -*-
# :Progetto: vcpx -- Updatable VC working directory
# :Creato:   mer 09 giu 2004 13:55:35 CEST
# :Autore:   Lele Gaifax <lele@nautilus.homeip.net>
# :Licenza:  GNU General Public License
#

"""
Updatable sources are the simplest abstract wrappers around a working
directory under some kind of version control system.
"""

__docformat__ = 'reStructuredText'

from vcpx import TailorBug, TailorException
from vcpx.workdir import WorkingDir


CONFLICTS_PROMPT = """
The changeset

%s

caused conflicts on the following files:

 * %s

This is quite unusual, and most probably it means someone else has
changed the working dir, beyond tailor control, or maybe a tailor bug
is showing up.

Either abort the session with Ctrl-C, or manually correct the situation
with a Ctrl-Z, explore and correct, and coming back from the shell with
'fg'.

What would you like to do?
"""


class GetUpstreamChangesetsFailure(TailorException):
    "Failure getting upstream changes"


class ChangesetApplicationFailure(TailorException):
    "Failure applying upstream changes"


class InvocationError(TailorException):
    "Bad invocation, use --help for details"


class UpdatableSourceWorkingDir(WorkingDir):
    """
    This is an abstract working dir able to follow an upstream
    source of ``changesets``.

    It has three main functionalities:

    getPendingChangesets
        to query the upstream server about new changesets

    applyPendingChangesets
        to apply them to the working directory

    checkoutUpstreamRevision
        to extract a new copy of the sources, actually initializing
        the mechanism.

    Subclasses MUST override at least the _underscoredMethods.
    """

    def applyPendingChangesets(self, applyable=None, replayable=None,
                               replay=None, applied=None):
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

        from time import sleep

        c = None
        last = None
        conflicts = []

        try:
            i = 0
            for c in self.state_file:
                i += 1
                self.log.info('Changeset #%d', i)
                # Give the opportunity to subclasses to stop the application
                # of the queue, before the application of the patch by the
                # source backend.
                if not self._willApplyChangeset(c, applyable):
                    self.log.info('Stopping application, %r remains pending',
                                  c.revision)
                    break

                # Sometime is better to wait a little while before each
                # changeset, to avoid upstream server stress.
                if self.repository.delay_before_apply:
                    sleep(self.repository.delay_before_apply)

                try:
                    res = self._applyChangeset(c)
                except TailorException, e:
                    self.log.critical("Couldn't apply changeset: %s", e)
                    self.log.debug("Changeset: %s", c)
                    raise
                except KeyboardInterrupt:
                    self.log.warning("INTERRUPTED BY THE USER!")
                    raise

                if res:
                    # We have a conflict.  Give the user a chance of fixing
                    # the situation, or abort with Ctrl-C, or whatever the
                    # subclasses decide.
                    try:
                        self._handleConflict(c, conflicts, res)
                    except KeyboardInterrupt:
                        self.log.warning("INTERRUPTED BY THE USER!")
                        break

                # Give the opportunity to subclasses to skip the commit on
                # the target backend.
                if self._didApplyChangeset(c, replayable):
                    if replay:
                        try:
                            replay(c)
                        except Exception, e:
                            self.log.critical("Couldn't replay changeset: %s", e)
                            self.log.debug("Changeset: %s", c)
                            raise

                # Remember it for the finally clause and notify the state
                # file so that it gets removed from the queue
                last = c
                self.state_file.applied()

                # Another hook (last==c here)
                if applied:
                    applied(last)
        finally:
            # For whatever reason we exit the loop, save the last state
            self.state_file.finalize()

        return last, conflicts

    def _willApplyChangeset(self, changeset, applyable=None):
        """
        This gets called just before applying each changeset.  The whole
        process will be stopped if this returns False.

        Subclasses may use this to stop the process on some conditions,
        or to do whatever before application.
        """

        if applyable:
            return applyable(changeset)
        else:
            return True

    def _didApplyChangeset(self, changeset, replayable=None):
        """
        This gets called right after changeset application.  The final
        commit on the target system won't be carried out if this
        returns False.

        Subclasses may use this to alter the changeset in any way, before
        committing its changes to the target system.
        """

        if replayable:
            return replayable(changeset)
        else:
            return True

    def _handleConflict(self, changeset, conflicts, conflict):
        """
        Handle the conflict raised by the application of the upstream changeset.

        This implementation just append a (changeset, conflict) to the
        list of all conflicts, and present a prompt to the user that
        may abort with Ctrl-C (that in turn generates a KeyboardInterrupt).
        """

        conflicts.append((changeset, conflict))
        raw_input(CONFLICTS_PROMPT % (str(changeset), '\n * '.join(conflict)))

    def getPendingChangesets(self, sincerev=None):
        """
        Load the pending changesets from the state file, or query the
        upstream repository if there's none. Return an iterator over
        pending changesets.
        """

        if not self.state_file.pending():
            last = self.state_file.lastAppliedChangeset()
            if last:
                revision = last.revision
            else:
                revision = sincerev
            changesets = self._getUpstreamChangesets(revision)
            self.state_file.setPendingChangesets(changesets)
        return self.state_file

    def _getUpstreamChangesets(self, sincerev):
        """
        Query the upstream repository about what happened on the
        sources since last sync, returning a sequence of Changesets
        instances.

        This method must be overridden by subclasses.
        """

        raise TailorBug("%s should override this method!" % self.__class__)

    def _applyChangeset(self, changeset):
        """
        Do the actual work of applying the changeset to the working copy.

        Subclasses should reimplement this method performing the
        necessary steps to *merge* given `changeset`, returning a list
        with the conflicts, if any.
        """

        raise TailorBug("%s should override this method!" % self.__class__)

    def checkoutUpstreamRevision(self, revision):
        """
        Extract a working copy of the given revision from a repository.

        Return the last applied changeset.
        """

        last = self._checkoutUpstreamRevision(revision)
        # Notify the state file about latest applied changeset
        self.state_file.applied(last)
        self.state_file.finalize()
        return last

    def _checkoutUpstreamRevision(self, revision):
        """
        Concretely do the checkout of the upstream revision.
        """

        raise TailorBug("%s should override this method!" % self.__class__)

    def prepareSourceRepository(self):
        """
        Do whatever is needed to setup or connect to the source
        repository.
        """

        self._prepareSourceRepository()

    def _prepareSourceRepository(self):
        """
        Possibly connect to the source repository, when overriden
        by subclasses.
        """
