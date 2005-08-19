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
from workdir import WorkingDir

HOST = socket.getfqdn()
AUTHOR = "tailor"
BOOTSTRAP_PATCHNAME = 'Tailorization'
BOOTSTRAP_CHANGELOG = """\
Import of the upstream sources from

  Repository: %(source_repository)s%(source_module)s
  Revision:   %(revision)s
"""

class TargetInitializationFailure(Exception):
    "Failure initializing the target VCS"

class SyncronizableTargetWorkingDir(WorkingDir):
    """
    This is an abstract working dir usable as a *shadow* of another
    kind of VC, sharing the same working directory.

    Most interesting entry points are:

    replayChangeset
        to replay an already applied changeset, to mimic the actions
        performed by the upstream VC system on the tree such as
        renames, deletions and adds.  This is an useful argument to
        feed as ``replay`` to ``applyUpstreamChangesets``

    importFirstRevision
        to initialize a pristine working directory tree under this VC
        system, possibly extracted under a different kind of VC

    Subclasses MUST override at least the _underscoredMethods.
    """

    PATCH_NAME_FORMAT = 'Tailorized "%(revision)s"'
    """
    The format string used to compute the patch name, used by underlying VCS.
    """

    REMOVE_FIRST_LOG_LINE = False
    """
    When true, remove the first line from the upstream changelog.
    """

    def replayChangeset(self, changeset):
        """
        Do whatever is needed to replay the changes under the target
        VC, to register the already applied (under the other VC)
        changeset.
        """

        try:
            self._replayChangeset(changeset)
        except:
            self.log_error(str(changeset), exc=True)
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
        self._commit(changeset.date, changeset.author,
                     patchname, changelog, entries)

    def _getCommitEntries(self, changeset):
        """
        Extract the names of the entries for the commit phase.
        """

        return [e.name for e in changeset.entries]

    def _replayChangeset(self, changeset):
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

        if renamed: self._renameEntries(renamed)
        if removed: self._removeEntries(removed)
        if added: self._addEntries(added)

        # Finally, deal with "copied" directories. The simple way is
        # executing an _addSubtree on each of them, evenif this may
        # cause "warnings" on items just moved/added above...

        while added:
            subdir = added.pop(0).name
            if isdir(join(self.basedir, subdir)):
                self._addSubtree(subdir)
                added = [e for e in added if not e.name.startswith(subdir)]

    def _addEntries(self, entries):
        """
        Add a sequence of entries
        """

        self._addPathnames([e.name for e in entries])

    def _addPathnames(self, names):
        """
        Add some new filesystem objects.
        """

        raise "%s should override this method" % self.__class__

    def _addSubtree(self, subdir):
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

        exclude = []

        if self.state_file.filename.startswith(self.basedir):
            sfrelname = self.state_file.filename[len(self.basedir)+1:]
            exclude.append(sfrelname)
            exclude.append(sfrelname+'.journal')

        if self.logfile.startswith(self.basedir):
            exclude.append(self.logfile[len(self.basedir)+1:])

        if subdir and subdir<>'.':
            self._addPathnames([subdir])

        for dir, subdirs, files in walk(join(self.basedir, subdir)):
            for excd in IGNORED_METADIRS:
                if excd in subdirs:
                    subdirs.remove(excd)

            for excf in exclude:
                if excf in files:
                    files.remove(excf)

            if subdirs or files:
                self._addPathnames([join(dir, df)[len(self.basedir)+1:]
                                    for df in subdirs + files])

    def _commit(self, date, author, patchname, changelog=None, entries=None):
        """
        Commit the changeset.
        """

        raise "%s should override this method" % self.__class__

    def _removeEntries(self, entries):
        """
        Remove a sequence of entries.
        """

        self._removePathnames([e.name for e in entries])

    def _removePathnames(self, names):
        """
        Remove some filesystem object.
        """

        raise "%s should override this method" % self.__class__

    def _renameEntries(self, entries):
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
                self._addPathnames(parents)

            self._renamePathname(e.old_name, e.name)

    def _renamePathname(self, oldname, newname):
        """
        Rename a filesystem object to some other name/location.
        """

        raise "%s should override this method" % self.__class__

    def prepareWorkingDirectory(self, source_repo):
        """
        Do anything required to setup the hosting working directory.
        """

        self._prepareWorkingDirectory(source_repo)

    def _prepareTargetRepository(self):
        """
        Possibly create or connect to the repository, when overriden
        by subclasses.
        """

    def _prepareWorkingDirectory(self, source_repo):
        """
        Possibly checkout a working copy of the target VC, that will host the
        upstream source tree, when overriden by subclasses.
        """

    def importFirstRevision(self, source_repo, changeset, initial):
        """
        Initialize a new working directory, just extracted from
        some other VC system, importing everything's there.
        """

        self._initializeWorkingDir()
        revision = changeset.revision
        source_repository = source_repo.repository
        source_module = source_repo.module or ''
        if initial:
            author = changeset.author
            patchname = changeset.log
            log = None
        else:
            author = "%s@%s" % (AUTHOR, HOST)
            patchname = BOOTSTRAP_PATCHNAME
            log = BOOTSTRAP_CHANGELOG % locals()
        self._commit(changeset.date, author, patchname, log)

    def _initializeWorkingDir(self):
        """
        Assuming the ``basedir`` directory contains a working copy ``module``
        extracted from some VC repository, add it and all its content
        to the target repository.

        This implementation recursively add every file in the subtree.
        Subclasses should override this method doing whatever is
        appropriate for the backend.
        """

        self._addSubtree('.')
