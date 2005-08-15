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

from workdir import WorkingDir

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

class GetUpstreamChangesetsFailure(Exception):
    "Failure getting upstream changes"

class ChangesetApplicationFailure(Exception):
    "Failure applying upstream changes"

class InvocationError(Exception):
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

        c = None
        last = None
        conflicts = []

        if not self.pending:
            return last, conflicts

        remaining = self.pending[:]
        for c in self.pending:
            if not self._willApplyChangeset(c, applyable):
                break

            self.log_info("Applying changeset %s" % c.revision)

            try:
                res = self._applyChangeset(c)
            except:
                self.log_error("Couldn't apply changeset %s" % c.revision,
                               exc=True)
                raise

            if res:
                conflicts.append((c, res))
                try:
                    raw_input(CONFLICTS_PROMPT % (str(c), '\n * '.join(res)))
                except KeyboardInterrupt:
                    self.log_info("INTERRUPTED BY THE USER!")
                    return last, conflicts

            if not self._didApplyChangeset(c, replayable):
                continue

            if replay:
                replay(c)

            remaining.remove(c)
            self.state_file.write(c.revision, remaining)

            if applied:
                applied(c)

            last = c

        self.pending = remaining
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

    def getPendingChangesets(self, sincerev=None):
        """
        Load the pending changesets from the state file, or query the
        upstream repository if there's none.
        """

        revision, self.pending = self.state_file.load()
        if not self.pending:
            self.pending = self._getUpstreamChangesets(revision or sincerev)
        return self.pending

    def _getUpstreamChangesets(self, sincerev):
        """
        Query the upstream repository about what happened on the
        sources since last sync, returning a sequence of Changesets
        instances.

        This method must be overridden by subclasses.
        """

        raise "%s should override this method" % self.__class__

    def _applyChangeset(self, changeset):
        """
        Do the actual work of applying the changeset to the working copy.

        Subclasses should reimplement this method performing the
        necessary steps to *merge* given `changeset`, returning a list
        with the conflicts, if any.
        """

        raise "%s should override this method" % self.__class__

    def checkoutUpstreamRevision(self, revision):
        """
        Extract a working copy of the given revision from a repository.

        Return the last applied changeset.
        """

        last = self._checkoutUpstreamRevision(revision)
        self.state_file.write(last.revision, self.pending)
        return last

    def _checkoutUpstreamRevision(self, revision):
        """
        Concretely do the checkout of the upstream revision.
        """

        raise "%s should override this method" % self.__class__
