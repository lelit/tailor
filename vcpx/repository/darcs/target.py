# -*- mode: python; coding: utf-8 -*-
# :Progetto: Tailor -- Darcs peculiarities when used as a target
# :Creato:   lun 10 lug 2006 00:12:15 CEST
# :Autore:   Lele Gaifax <lele@nautilus.homeip.net>
# :Licenza:  GNU General Public License
#

"""
This module contains the target specific bits of the darcs backend.
"""

__docformat__ = 'reStructuredText'

import re

from vcpx.shwrap import ExternalCommand, PIPE, STDOUT
from vcpx.target import ChangesetReplayFailure, SynchronizableTargetWorkingDir, \
                        PostCommitCheckFailure
from vcpx.tzinfo import UTC


MOTD = """\
Tailorized equivalent of
%s
"""


class DarcsTargetWorkingDir(SynchronizableTargetWorkingDir):
    """
    A target working directory under ``darcs``.
    """

    def importFirstRevision(self, source_repo, changeset, initial):
        from os import walk, sep
        from os.path import join
        from vcpx.dualwd import IGNORED_METADIRS

        if not self.repository.split_initial_import_level:
            super(DarcsTargetWorkingDir, self).importFirstRevision(
                source_repo, changeset, initial)
        else:
            cmd = self.repository.command("add", "--case-ok", "--quiet")
            add = ExternalCommand(cwd=self.repository.basedir, command=cmd)
            cmd = self.repository.command("add", "--case-ok", "--recursive",
                                          "--quiet")
            addrecurs = ExternalCommand(cwd=self.repository.basedir, command=cmd)
            for root, dirs, files in walk(self.repository.basedir):
                subtree = root[len(self.repository.basedir)+1:]
                if subtree:
                    log = "Import of subtree %s" % subtree
                    level = len(subtree.split(sep))
                else:
                    log = "Import of first level"
                    level = 0
                for excd in IGNORED_METADIRS:
                    if excd in dirs:
                        dirs.remove(excd)
                if level>self.repository.split_initial_import_level:
                    while dirs:
                        d = dirs.pop(0)
                        addrecurs.execute(join(subtree, d))
                    filenames = [join(subtree, f) for f in files]
                    if filenames:
                        add.execute(*filenames)
                else:
                    dirnames = [join(subtree, d) for d in dirs]
                    if dirnames:
                        add.execute(*dirnames)
                    filenames = [join(subtree, f) for f in files]
                    if filenames:
                        add.execute(*filenames)
                self._commit(changeset.date, "tailor", "Initial import",
                             log, isinitialcommit=initial)

            cmd = self.repository.command("tag", "--author", "tailor")
            ExternalCommand(cwd=self.repository.basedir, command=cmd).execute(
                "Initial import from %s" % source_repo.repository)

    def _addPathnames(self, names):
        """
        Add some new filesystem objects.
        """

        cmd = self.repository.command("add", "--case-ok", "--not-recursive",
                                      "--quiet")
        ExternalCommand(cwd=self.repository.basedir, command=cmd).execute(names)

    def _addSubtree(self, subdir):
        """
        Use the --recursive variant of ``darcs add`` to add a subtree.
        """

        cmd = self.repository.command("add", "--case-ok", "--recursive",
                                      "--quiet")
        add = ExternalCommand(cwd=self.repository.basedir, command=cmd,
                              ok_status=(0,2))
        output = add.execute(subdir, stdout=PIPE, stderr=STDOUT)[0]
        if add.exit_status and add.exit_status!=2:
            self.log.warning("%s returned status %d, saying %s",
                             str(add), add.exit_status, output.read())

    def _commit(self, date, author, patchname, changelog=None, entries=None,
                tags = [], isinitialcommit = False):
        """
        Commit the changeset.
        """

        logmessage = []

        logmessage.append(date.astimezone(UTC).strftime('%Y/%m/%d %H:%M:%S UTC'))
        logmessage.append(author)
        if patchname:
            logmessage.append(patchname)
        else:
            # This is possibile also when REMOVE_FIRST_LOG_LINE is in
            # effect and the changelog starts with newlines: discard
            # those, otherwise darcs will complain about invalid patch
            # name
            if changelog and changelog.startswith('\n'):
                while changelog.startswith('\n'):
                    changelog = changelog[1:]
        if changelog:
            logmessage.append(changelog)

        if not logmessage:
            logmessage.append('Unnamed patch')

        cmd = self.repository.command("record", "--all", "--pipe")
        if not entries:
            entries = ['.']

        record = ExternalCommand(cwd=self.repository.basedir, command=cmd)
        output = record.execute(input=self.repository.encode('\n'.join(logmessage)),
                                stdout=PIPE, stderr=STDOUT)[0]

        if record.exit_status:
            raise ChangesetReplayFailure(
                "%s returned status %d, saying: %s" % (str(record),
                                                       record.exit_status,
                                                       output.read()))

    def _postCommitCheck(self):
        cmd = self.repository.command("whatsnew", "--summary", "--look-for-add")
        whatsnew = ExternalCommand(cwd=self.repository.basedir, command=cmd, ok_status=(1,))
        output = whatsnew.execute(stdout=PIPE, stderr=STDOUT)[0]
        if not whatsnew.exit_status:
            raise PostCommitCheckFailure(
                "Changes left in working dir after commit:\n%s" % output.read())

    def _replayChangeset(self, changeset):
        """
        Instead of using the "darcs mv" command, manually add
        the rename to the pending file: this is a dirty trick, that
        allows darcs to handle the case when the source changeset
        is something like::
          $ bzr mv A B
          $ touch A
          $ bzr add A
        where A is actually replaced, and old A is now B. Since by the
        time the changeset gets replayed, the source has already replaced
        A with its new content, darcs would move the *wrong* A to B...
        """

        from os.path import join, exists

        # The "_darcs/patches/pending" file is basically a patch containing
        # only the changes (hunks, adds...) not yet recorded by darcs: it does
        # contain either a single change (that is, exactly one line), or a
        # collection of changes, with opening and closing curl braces.
        # Filenames must begin with "./", and eventual spaces replaced by '\32\'.
        # Order is significant!

        pending = join(self.repository.basedir, '_darcs', 'patches', 'pending')
        if exists(pending):
            p = open(pending).readlines()
            if p[0] != '{\n':
                p.insert(0, '{\n')
                p.append('}\n')
        else:
            p = [ '{\n', '}\n' ]

        entries = []

        while changeset.entries:
            e = changeset.entries.pop(0)
            if e.action_kind == e.DELETED:
                elide = False
                for j,oe in enumerate(changeset.entries):
                    if oe.action_kind == oe.ADDED and e.name == oe.name:
                        self.log.debug('Collapsing a %s and a %s on %s, assuming '
                                       'an upstream "replacement"',
                                       e.action_kind, oe.action_kind, oe.name)
                        del changeset.entries[j]
                        elide = True
                        break
                if not elide:
                    entries.append(e)
            elif e.action_kind == e.ADDED:
                elide = False
                for j,oe in enumerate(changeset.entries):
                    if oe.action_kind == oe.DELETED and e.name == oe.name:
                        self.log.debug('Collapsing a %s and a %s on %s, assuming '
                                       'an upstream "replacement"',
                                       e.action_kind, oe.action_kind, oe.name)
                        del changeset.entries[j]
                        elide = True
                        break
                if not elide:
                    entries.append(e)
            else:
                entries.append(e)

        changed = False
        for e in entries:
            if e.action_kind == e.RENAMED:
                self.log.debug('Mimicing "darcs mv %s %s"',
                               e.old_name, e.name)
                oname = e.old_name.replace(' ', '\\32\\')
                nname = e.name.replace(' ', '\\32\\')
                p.insert(-1, 'move ./%s ./%s\n' % (oname, nname))
                changed = True
            elif e.action_kind == e.ADDED:
                self.log.debug('Mimicing "darcs add %s"', e.name)
                name = e.name.replace(' ', '\\32\\')
                if e.is_directory:
                    p.insert(-1, 'adddir ./%s\n' % name)
                else:
                    p.insert(-1, 'addfile ./%s\n' % name)
                changed = True
            elif e.action_kind == e.DELETED:
                self.log.debug('Mimicing "darcs rm %s"', e.name)
                name = e.name.replace(' ', '\\32\\')
                if e.is_directory:
                    p.insert(-1, 'rmdir ./%s\n' % name)
                else:
                    p.insert(-1, 'rmfile ./%s\n' % name)
                changed = True
        if changed:
            open(pending, 'w').writelines(p)
        return True

    def _prepareTargetRepository(self):
        """
        Create the base directory if it doesn't exist, and execute
        ``darcs initialize`` if needed.
        """

        from os.path import join, exists

        metadir = join(self.repository.basedir, '_darcs')

        if not exists(metadir):
            self.repository.create()

        prefsdir = join(metadir, 'prefs')
        prefsname = join(prefsdir, 'prefs')
        boringname = join(prefsdir, 'boring')
        if exists(prefsname):
            for pref in open(prefsname, 'rU'):
                if pref:
                    pname, pvalue = pref.split(' ', 1)
                    if pname == 'boringfile':
                        boringname = join(self.repository.basedir, pvalue[:-1])

        boring = open(boringname, 'rU')
        ignored = boring.read().rstrip().split('\n')
        boring.close()

        # Build a list of compiled regular expressions, that will be
        # used later to filter the entries.
        self.__unwanted_entries = [re.compile(rx) for rx in ignored
                                   if rx and not rx.startswith('#')]

    def _prepareWorkingDirectory(self, source_repo):
        """
        Tweak the default settings of the repository.
        """

        from os.path import join

        motd = open(join(self.repository.basedir, '_darcs/prefs/motd'), 'w')
        motd.write(MOTD % str(source_repo))
        motd.close()

    def _adaptEntries(self, changeset):
        """
        Filter out boring files.
        """

        from copy import copy

        adapted = SynchronizableTargetWorkingDir._adaptEntries(self, changeset)

        # If there are no entries or no rules, there's nothing to do
        if not adapted or not adapted.entries or not self.__unwanted_entries:
            return adapted

        entries = []
        skipped = False
        for e in adapted.entries:
            skip = False
            for rx in self.__unwanted_entries:
                if rx.search(e.name):
                    skip = True
                    break
            if skip:
                self.log.info('Entry "%s" skipped per boring rules', e.name)
                skipped = True
            else:
                entries.append(e)

        # All entries are gone, don't commit this changeset
        if not entries:
            self.log.info('All entries ignored, skipping whole '
                          'changeset "%s"', changeset.revision)
            return None

        if skipped:
            adapted = copy(adapted)
            adapted.entries = entries

        return adapted

    def _tag(self, tag, date, author):
        """
        Apply the given tag to the repository, unless it has already
        been applied to the current state. (If it has been applied to
        an earlier state, do apply it; the later tag overrides the
        earlier one.
        """
        if tag not in self._currentTags():
            cmd = self.repository.command("tag", "--author", "Unknown tagger")
            ExternalCommand(cwd=self.repository.basedir, command=cmd).execute(tag)

    def _currentTags(self):
        """
        Return a list of tags that refer to the repository's current
        state.  Does not consider tags themselves to be part of the
        state, so if the repo was tagged with T1 and then T2, then
        both T1 and T2 are considered to refer to the current state,
        even though 'darcs get --tag=T1' and 'darcs get --tag=T2'
        would have different results (the latter creates a repo that
        contains tag T2, but the former does not).

        This function assumes that a tag depends on all patches that
        precede it in the "darcs changes" list.  This assumption is
        valid if tags only come into the repository via tailor; if the
        user applies a tag by hand in the hybrid repository, or pulls
        in a tag from another darcs repository, then the assumption
        could be violated and mistagging could result.
        """

        from vcpx.repository.darcs.source import changesets_from_darcschanges_unsafe

        cmd = self.repository.command("changes",
                                      "--from-match", "not name ^TAG",
                                      "--xml-output", "--reverse")
        changes =  ExternalCommand(cwd=self.repository.basedir, command=cmd)
        output = changes.execute(stdout=PIPE, stderr=STDOUT)[0]
        if changes.exit_status:
            raise ChangesetReplayFailure(
                "%s returned status %d saying\n%s" %
                (str(changes), changes.exit_status, output.read()))

        tags = []
        for cs in changesets_from_darcschanges_unsafe(output):
            for tag in cs.tags:
                if tag not in tags:
                    tags.append(tag)
        return tags
