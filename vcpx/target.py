# -*- mode: python; coding: utf-8 -*-
# :Progetto: vcpx -- Syncable targets
# :Creato:   ven 04 giu 2004 00:27:07 CEST
# :Autore:   Lele Gaifax <lele@nautilus.homeip.net>
# :Licenza:  GNU General Public License
#

"""
Syncronizable targets are the simplest abstract wrappers around a
working directory under two different version control systems.
"""

__docformat__ = 'reStructuredText'

import socket

HOST = socket.getfqdn()
AUTHOR = "tailor"
BOOTSTRAP_PATCHNAME = 'Tailorization of %s'
BOOTSTRAP_CHANGELOG = """\
Import of the upstream sources from

  Repository: %(source_repository)s
  Module:     %(source_module)s
  Revision:   %(revision)s
"""

class TargetInitializationFailure(Exception):
    "Failure initializing the target VCS"

class SyncronizableTargetWorkingDir(object):
    """
    This is an abstract working dir usable as a *shadow* of another
    kind of VC, sharing the same working directory.

    Most interesting entry points are:

    replayChangeset
        to replay an already applied changeset, to mimic the actions
        performed by the upstream VC system on the tree such as
        renames, deletions and adds.  This is an useful argument to
        feed as ``replay`` to ``applyUpstreamChangesets``

    initializeNewWorkingDir
        to initialize a pristine working directory tree under this VC
        system, possibly extracted under a different kind of VC

    Subclasses MUST override at least the _underscoredMethods.
    """

    PATCH_NAME_FORMAT = '%(module)s: changeset %(revision)s'
    """
    The format string used to compute the patch name, used by underlying VCS.
    """

    REMOVE_FIRST_LOG_LINE = False
    """
    When true, remove the first line from the upstream changelog.
    """

    def replayChangeset(self, root, module, changeset, logger=None):
        """
        Do whatever is needed to replay the changes under the target
        VC, to register the already applied (under the other VC)
        changeset.
        """

        try:
            self._replayChangeset(root, changeset, logger)
        except:
            if logger: logger.critical(str(changeset))
            raise

        if changeset.log == '':
            firstlogline = 'Empty log message'
            remaininglog = ''
        else:
            loglines = changeset.log.split('\n')
            if len(loglines)>1:
                firstlogline = loglines[0]
                remaininglog = '\n'.join(loglines[1:])
            else:
                firstlogline = changeset.log
                remaininglog = ''

        patchname = self.PATCH_NAME_FORMAT % {
            'revision': changeset.revision,
            'author': changeset.author,
            'date': changeset.date,
            'firstlogline': firstlogline,
            'remaininglog': remaininglog}
        if self.REMOVE_FIRST_LOG_LINE:
            changelog = remaininglog
        else:
            changelog = changeset.log
        entries = self._getCommitEntries(changeset)
        self._commit(root, changeset.date, changeset.author,
                     patchname, changelog, entries)

    def _getCommitEntries(self, changeset):
        """
        Extract the names of the entries for the commit phase.
        """

        return [e.name for e in changeset.entries]

    def _replayChangeset(self, root, changeset, logger):
        """
        Replicate the actions performed by the changeset on the tree of
        files.
        """

        from os.path import join, isdir

        added = changeset.addedEntries()
        renamed = changeset.renamedEntries()
        removed = changeset.removedEntries()

        # Sort added entries, to be sure that /root/addedDir/ comes
        # before /root/addedDir/addedSubdir
        added.sort(lambda x,y: cmp(x.name, y.name))

        # Sort removes in reverse order, to delete directories after
        # their contents.
        removed.sort(lambda x,y: cmp(y.name, x.name))

        # Replay the actions

        if renamed: self._renameEntries(root, renamed)
        if removed: self._removeEntries(root, removed)
        if added: self._addEntries(root, added)

        # Finally, deal with "copied" directories. The simple way is
        # executing an _addSubtree on each of them, evenif this may
        # cause "warnings" on items just moved/added above...

        while added:
            subdir = added.pop(0).name
            if isdir(join(root, subdir)):
                self._addSubtree(root, subdir)
                added = [e for e in added if not e.name.startswith(subdir)]

    def _addEntries(self, root, entries):
        """
        Add a sequence of entries
        """

        self._addPathnames(root, [e.name for e in entries])

    def _addPathnames(self, root, names):
        """
        Add some new filesystem objects.
        """

        raise "%s should override this method" % self.__class__

    def _addSubtree(self, root, subdir):
        """
        Add a whole subtree.

        This implementation crawl down the whole subtree, adding
        entries (subdirs, skipping the usual VC-specific control
        directories such as ``.svn``, ``_darcs`` or ``CVS``, and
        files).

        Subclasses may use a better way, if the backend implements
        a recursive add that skips the various metadata directories.
        """

        from os.path import join
        from os import walk
        from dualwd import IGNORED_METADIRS

        if subdir<>'.':
            self._addPathnames(root, [subdir])

        for dir, subdirs, files in walk(join(root, subdir)):
            for excd in IGNORED_METADIRS:
                if excd in subdirs:
                    subdirs.remove(excd)

            # Uhm, is this really desiderable?
            for excf in ['tailor.info', 'tailor.log']:
                if excf in files:
                    files.remove(excf)

            if subdirs or files:
                self._addPathnames(dir, subdirs + files)

    def _commit(self, root, date, author, patchname,
                changelog=None, entries=None):
        """
        Commit the changeset.
        """

        raise "%s should override this method" % self.__class__

    def _removeEntries(self, root, entries):
        """
        Remove a sequence of entries.
        """

        self._removePathnames(root, [e.name for e in entries])

    def _removePathnames(self, root, names):
        """
        Remove some filesystem object.
        """

        raise "%s should override this method" % self.__class__

    def _renameEntries(self, root, entries):
        """
        Rename a sequence of entries, adding all the parent directories
        of each entry.
        """

        from os.path import split

        added = []
        for e in entries:
            parents = []
            parent = split(e.name)[0]
            while parent:
                if not parent in added:
                    parents.append(parent)
                    added.append(parent)
                parent = split(parent)[0]
            if parents:
                parents.reverse()
                self._addPathnames(root, parents)

            self._renamePathname(root, e.old_name, e.name)

    def _renamePathname(self, root, oldname, newname):
        """
        Rename a filesystem object to some other name/location.
        """

        raise "%s should override this method" % self.__class__

    def prepareWorkingDirectory(self, root, target_repository, target_module):
        """
        Do anything required to setup the hosting working directory.
        """

        if target_repository:
            self._prepareTargetRepository(root, target_repository,
                                          target_module)
            self._prepareWorkingDirectory(root, target_repository,
                                          target_module)

    def _prepareTargetRepository(self, root, target_repository, target_module):
        """
        Possibly create the repository, when overriden by subclasses.
        """

    def _prepareWorkingDirectory(self, root, target_repository, target_module):
        """
        Possibly checkout a working copy of the target VC, that will host the
        upstream source tree, when overriden by subclasses.
        """

    def initializeNewWorkingDir(self, root, source_repository,
                                source_module, subdir, changeset, initial):
        """
        Initialize a new working directory, just extracted from
        some other VC system, importing everything's there.
        """

        self._initializeWorkingDir(root, source_repository, source_module,
                                   subdir)
        revision = changeset.revision
        if initial:
            author = changeset.author
            patchname = changeset.log
            log = None
        else:
            author = "%s@%s" % (AUTHOR, HOST)
            patchname = BOOTSTRAP_PATCHNAME % source_module
            log = BOOTSTRAP_CHANGELOG % locals()
        self._commit(root, changeset.date, author, patchname, log,
                     entries=[subdir])

    def _initializeWorkingDir(self, root, source_repository, source_module,
                              subdir):
        """
        Assuming the ``root`` directory contains a working copy ``module``
        extracted from some VC repository, add it and all its content
        to the target repository.

        This implementation recursively add every file in the subtree.
        Subclasses should override this method doing whatever is
        appropriate for the backend.
        """

        self._addSubtree(root, subdir)
