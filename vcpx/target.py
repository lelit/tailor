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
from signal import signal, SIGINT, SIG_IGN
from vcpx import TailorBug, TailorException
from vcpx.workdir import WorkingDir


HOST = socket.getfqdn()
AUTHOR = "tailor"
BOOTSTRAP_PATCHNAME = 'Tailorization'
BOOTSTRAP_CHANGELOG = """\
Import of the upstream sources from
%(source_repository)s
   Revision: %(revision)s
"""


class TargetInitializationFailure(TailorException):
    "Failure initializing the target VCS"


class ChangesetReplayFailure(TailorException):
    "Failure replaying the changeset on the target system"


class PostCommitCheckFailure(TailorException):
    "Most probably a tailor bug, not everything has been committed."


class SynchronizableTargetWorkingDir(WorkingDir):
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

    PATCH_NAME_FORMAT = '[%(project)s @ %(revision)s]'
    """
    The format string used to compute the patch name, used by underlying VCS.
    """

    REMOVE_FIRST_LOG_LINE = False
    """
    When true, remove the first line from the upstream changelog.
    """

    def __getPatchNameAndLog(self, changeset):
        """
        Return a tuple (patchname, changelog) interpolating changeset's
        information with the template above.
        """

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
            'project': self.repository.projectref().name,
            'revision': changeset.revision,
            'author': changeset.author,
            'date': changeset.date,
            'firstlogline': firstlogline,
            'remaininglog': remaininglog}
        if self.REMOVE_FIRST_LOG_LINE:
            changelog = remaininglog
        else:
            changelog = changeset.log
        return patchname, changelog

    def _prepareToReplayChangeset(self, changeset):
        """
        This is called **before** fetching and applying the source
        changeset. This implementation does nothing more than
        returning True. Subclasses may override it, for example to
        preexecute some entries such as moves.

        Returning False the changeset won't be applied and the
        process will stop.
        """

        return True

    def replayChangeset(self, changeset):
        """
        Do whatever is needed to replay the changes under the target
        VC, to register the already applied (under the other VC)
        changeset.
        """

        try:
            changeset = self._adaptChangeset(changeset)
        except:
            self.log.exception("Failure adapting: %s", str(changeset))
            raise

        if changeset is None:
            return

        try:
            self._replayChangeset(changeset)
        except:
            self.log.exception("Failure replaying: %s", str(changeset))
            raise
        patchname, log = self.__getPatchNameAndLog(changeset)
        entries = self._getCommitEntries(changeset)
        previous = signal(SIGINT, SIG_IGN)
        try:
            self._commit(changeset.date, changeset.author, patchname, log,
                         entries, tags = changeset.tags)
            if changeset.tags:
                for tag in changeset.tags:
                    self._tag(tag, changeset.date, changeset.author)
            if self.repository.post_commit_check:
                self._postCommitCheck()
        finally:
            signal(SIGINT, previous)

        try:
            self._dismissChangeset(changeset)
        except:
            self.log.exception("Failure dismissing: %s", str(changeset))
            raise

    def __getPrefixToSource(self):
        """
        Compute and return the "offset" between source and target basedirs,
        or None when not using shared directories, or there's no offset.
        """

        project = self.repository.projectref()
        ssubdir = project.source.subdir
        tsubdir = project.target.subdir
        if self.shared_basedirs and ssubdir <> tsubdir:
            if tsubdir == '.':
                prefix = ssubdir
            else:
                if not tsubdir.endswith('/'):
                    tsubdir += '/'
                prefix = ssubdir[len(tsubdir):]
            return prefix
        else:
            return None

    def _normalizeEntryPaths(self, entry):
        """
        Normalize the name and old_name of an entry.

        The ``name`` and ``old_name`` of an entry are pathnames coming
        from the upstream system, and is usually (although there is no
        guarantee it actually is) a UNIX style path with forward
        slashes "/" as separators.

        This implementation uses normpath to adapt the path to the
        actual OS convention, but subclasses may eventually override
        this to use their own canonicalization of ``name`` and
        ``old_name``.
        """

        from os.path import normpath

        entry.name = normpath(entry.name)
        if entry.old_name:
            entry.old_name = normpath(entry.old_name)

    def __adaptEntriesPath(self, changeset):
        """
        If the source basedir is a subdirectory of the target, adjust
        all the pathnames adding the prefix computed by difference.
        """

        from copy import deepcopy
        from os.path import join

        if not changeset.entries:
            return changeset

        prefix = self.__getPrefixToSource()
        adapted = deepcopy(changeset)
        for e in adapted.entries:
            if prefix:
                e.name = join(prefix, e.name)
                if e.old_name:
                    e.old_name = join(prefix, e.old_name)
            self._normalizeEntryPaths(e)
        return adapted

    def _adaptEntries(self, changeset):
        """
        Do whatever is needed to adapt entries to the target system.

        This implementation adds a prefix to each path if needed, when
        the target basedir *contains* the source basedir. Also, each
        path is normalized thru ``normpath()`` or whatever equivalent
        operation provided by the specific target. It operates on and
        returns a copy of the given changeset.

        Subclasses shall eventually extend this to exclude unwanted
        entries, eventually returning None when all entries were
        excluded, to avoid the commit on target of an empty changeset.
        """

        adapted = self.__adaptEntriesPath(changeset)
        return adapted

    def _adaptChangeset(self, changeset):
        """
        Do whatever needed before replay and return the adapted changeset.

        This implementation calls ``self._adaptEntries()``, then
        executes the adapters defined by before-commit on the project:
        each adapter is run in turn, and may return False to indicate
        that the changeset shouldn't be replayed at all. They are
        otherwise free to alter the changeset in any meaningful way.
        """

        from copy import copy

        adapted = self._adaptEntries(changeset)
        if adapted:
            project = self.repository.projectref()
            if project.before_commit:
                adapted = copy(adapted)

                for adapter in project.before_commit:
                    if not adapter(self, adapted):
                        return None
        return adapted

    def _dismissChangeset(self, changeset):
        """
        Do whatever needed after commit.

        This execute the adapters defined by after-commit on the project,
        for example tagging in some way the target repository upon some
        particular kind of changeset.
        """

        project = self.repository.projectref()
        if project.after_commit:
            for farewell in project.after_commit:
                farewell(self, changeset)

    def _getCommitEntries(self, changeset):
        """
        Extract the names of the entries for the commit phase.
        """

        # Since the commit may use cli tools to do its job, and the
        # machinery may split the list into smaller chunks to avoid
        # too long command lines, anticipates added stuff.  I think
        # this is needed only when coming from CVS (or HG or in
        # general from systems that don't handle directories): its
        # _applyChangeset *appends* to the entries a fake ADD for
        # each new subdir.

        entries = []
        added = 0
        for e in changeset.entries:
            if e.action_kind == e.ADDED:
                entries.insert(added, e.name)
                added += 1
            else:
                # Add also the name of the old file: for some systems
                # it may not be strictly needed, but it is for most.
                if e.action_kind == e.RENAMED:
                    entries.append(e.old_name)
                entries.append(e.name)
        return entries

    def _replayChangeset(self, changeset):
        """
        Replay each entry of the changeset, that is execute the action associated
        to each kind of change for each entry, possibly grouping consecutive entries
        of the same kind.
        """

        from changes import ChangesetEntry

        actions = { ChangesetEntry.ADDED: self._addEntries,
                    ChangesetEntry.DELETED: self._removeEntries,
                    ChangesetEntry.RENAMED: self._renameEntries,
                    ChangesetEntry.UPDATED: self._editEntries
                    }

        # Group the changes by kind and perform the corresponding action

        last = None
        group = []
        for e in changeset.entries:
            if last is None or last.action_kind == e.action_kind:
                last = e
                group.append(e)
            if last.action_kind != e.action_kind:
                action = actions.get(last.action_kind)
                if action is not None:
                    action(group)
                group = [e]
                last = e
        if group:
            action = actions.get(group[0].action_kind)
            if action is not None:
                action(group)

    def _addEntries(self, entries):
        """
        Add a sequence of entries
        """

        self._addPathnames([e.name for e in entries])

    def _addPathnames(self, names):
        """
        Add some new filesystem objects.
        """

        raise TailorBug("%s should override this method!" % self.__class__)

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

        if self.state_file.filename.startswith(self.repository.basedir):
            sfrelname = self.state_file.filename[len(self.repository.basedir)+1:]
            exclude.append(sfrelname)
            exclude.append(sfrelname+'.old')
            exclude.append(sfrelname+'.journal')

        if self.logfile.startswith(self.repository.basedir):
            exclude.append(self.logfile[len(self.repository.basedir)+1:])

        if subdir and subdir<>'.':
            self._addPathnames([subdir])

        for dir, subdirs, files in walk(join(self.repository.basedir, subdir)):
            for excd in IGNORED_METADIRS:
                if excd in subdirs:
                    subdirs.remove(excd)

            for excf in exclude:
                if excf in files:
                    files.remove(excf)

            if subdirs or files:
                self._addPathnames([join(dir, df)[len(self.repository.basedir)+1:]
                                    for df in subdirs + files])

    def _commit(self, date, author, patchname, changelog=None, entries=None,
                tags = [], isinitialcommit = False):
        """
        Commit the changeset.
        """

        raise TailorBug("%s should override this method!" % self.__class__)

    def _postCommitCheck(self):
        """
        Perform any safety-belt check to assert everything's ok. This
        implementation does nothing, subclasses should reimplement the
        method.
        """

    def _removeEntries(self, entries):
        """
        Remove a sequence of entries.
        """

        self._removePathnames([e.name for e in entries])

    def _removePathnames(self, names):
        """
        Remove some filesystem object.
        """

        raise TailorBug("%s should override this method!" % self.__class__)

    def _editEntries(self, entries):
        """
        Records a sequence of entries as updated.
        """

        self._editPathnames([e.name for e in entries])

    def _editPathnames(self, names):
        """
        Records a sequence of filesystem objects as updated.
        """

        pass

    def _renameEntries(self, entries):
        """
        Rename a sequence of entries, adding all the parent directories
        of each entry.
        """

        from os import rename, walk
        from shutil import rmtree
        from os.path import split, join, exists, isdir

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

            other = False
            if self.shared_basedirs:
                # Check to see if the oldentry is still there. If it is,
                # that probably means one thing: it's been moved and then
                # replaced, see svn 'R' event. In this case, rename the
                # existing old entry to something else to trick targets
                # (that will assume the move was already done manually) and
                # finally restore its name.

                absold = join(self.repository.basedir, e.old_name)
                renamed = exists(absold)
                if renamed:
                    rename(absold, absold + '-TAILOR-HACKED-TEMP-NAME')
            else:
                # With disjunct directories, old entries are *always*
                # there because we dropped the --delete option to rsync.
                # So, instead of renaming the old entry, we temporarily
                # rename the new one, perform the target system rename
                # and replace back the real content (it may be a
                # renamed+edited event).

                # Hide the real new file from rename
                absnew = join(self.repository.basedir, e.name)
                renamed = exists(absnew)
                if renamed:
                    rename(absnew, absnew + '-TAILOR-HACKED-TEMP-NAME')

                # If 'absold' exist, then the file was moved and replaced
                # with an other file. Hide the other file from rename.
                absold = join(self.repository.basedir, e.old_name)
                other = exists(absold)
                if other:
                    rename(absold, absold + '-TAILOR-HACKED-OTHER-NAME')

                # Restore the old file from backup.
                oldfile = exists(absold + '-TAILOR-HACKED-OLD-NAME')
                if oldfile:
                    rename(absold + '-TAILOR-HACKED-OLD-NAME', absold)

            try:
                self._renamePathname(e.old_name, e.name)
            finally:

                # Restore other NEW target
                if other:
                    rename(absold + '-TAILOR-HACKED-OTHER-NAME', absold)

                if renamed:
                    if self.shared_basedirs:
                        # it's possible that the target already handled
                        # this
                        if exists(absold + '-TAILOR-HACKED-TEMP-NAME'):
                            rename(absold + '-TAILOR-HACKED-TEMP-NAME', absold)
                    else:

                        # before rsync      after rsync      the HACK            after "svn mv"           result
                        # /basedir          /basedir         /basedir            /basedir                 /basedir
                        # |                 |                |                   |                        |
                        # +- /dirold        +- /dirold       +- /dirold          +- /dirnew        move   |
                        #    |              |  |             |  |                |  |~~~~~~        hack   |
                        #    +- /.svn       |  +- /.svn      |  +- /.svn         |  +- /.svn  >-------+   |
                        #    |              |  |             |  |                |  |                 |   |
                        #    +- /subdir     |  +- /subdir    |  +- /subdir       |  +- /subdir        v   |
                        #       |           |     |          |     |             |     |              |   |
                        #       +- /.svn    |     +- /.svn   |     +- /.svn      |     +- /.svn  >--+ |   |
                        #                   |                |                   |                  | |   |
                        #                   +- /dirnew       +- /dirnew-HACKED   +- /dirnew-HACKED  v |   +- /dirnew
                        #                      |~~~~~~          |      ~~~~~~~      |               | |      |
                        #                      |                |                   |               +-|--->  +- /.svn
                        #                      |                |                   |                 |      |   ~~~~
                        #                      +- /subdir       +- /subdir          +- /subdir        |      +- /subdir
                        #                          ~~~~~~                                             |        |
                        #                                                                             +----->  +- /.svn
                        #                                                                                          ~~~~

                        # Ticket #65, #125
                        # If the target reposity has files in subdirectory,
                        # then remove the complete dir.
                        # But keep the dir '.svn', '_CVS', or what ever
                        if isdir(absnew):
                            if self.repository.METADIR <> None:
                                for root, dirs, files in walk(absnew):
                                    if self.repository.METADIR in dirs:
                                        dirs.remove(self.repository.METADIR)  # don't visit SVN directories
                                        svnnew = join(root, self.repository.METADIR)
                                        hacked = join(absnew + '-TAILOR-HACKED-TEMP-NAME' + root[len(absnew):], self.repository.METADIR)
                                        rename(svnnew, hacked)

                            rmtree(absnew)

                        rename(absnew + '-TAILOR-HACKED-TEMP-NAME', absnew)

    def _renamePathname(self, oldname, newname):
        """
        Rename a filesystem object to some other name/location.
        """

        raise TailorBug("%s should override this method!" % self.__class__)

    def prepareWorkingDirectory(self, source_repo):
        """
        Do anything required to setup the hosting working directory.
        """

        self._prepareWorkingDirectory(source_repo)

    def _prepareWorkingDirectory(self, source_repo):
        """
        Possibly checkout a working copy of the target VC, that will host the
        upstream source tree, when overriden by subclasses.
        """

    def prepareTargetRepository(self):
        """
        Do anything required to host the target repository.
        """

        from os import makedirs
        from os.path import join, exists

        if not exists(self.repository.basedir):
            makedirs(self.repository.basedir)

        self._prepareTargetRepository()

        prefix = self.__getPrefixToSource()
        if prefix:
            if not exists(join(self.repository.basedir, prefix)):
                # At bootstrap time, we assume that if the user
                # extracted the source manually, she added
                # the subdir, before doing that.
                makedirs(join(self.repository.basedir, prefix))
                self._addPathnames([prefix])

    def _prepareTargetRepository(self):
        """
        Possibly create or connect to the repository, when overriden
        by subclasses.
        """

    def importFirstRevision(self, source_repo, changeset, initial):
        """
        Initialize a new working directory, just extracted from
        some other VC system, importing everything's there.
        """

        self._initializeWorkingDir()
        # Execute the precommit hooks, but ignore None results
        changeset = self._adaptChangeset(changeset) or changeset
        revision = changeset.revision
        source_repository = str(source_repo)
        if initial:
            author = changeset.author
            patchname, log = self.__getPatchNameAndLog(changeset)
        else:
            author = "%s@%s" % (AUTHOR, HOST)
            patchname = BOOTSTRAP_PATCHNAME
            log = BOOTSTRAP_CHANGELOG % locals()
        self._commit(changeset.date, author, patchname, log,
                     isinitialcommit = True)

        if changeset.tags:
            for tag in changeset.tags:
                self._tag(tag, changeset.date, author)

        self._dismissChangeset(changeset)

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

    def _tag(self, tagname, date, author):
        """
        Tag the current version, if the VC type supports it, otherwise
        do nothing.
        """
        pass
