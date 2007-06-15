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
from vcpx.source import ChangesetApplicationFailure
from vcpx.target import SynchronizableTargetWorkingDir
from vcpx.tzinfo import UTC


MOTD = """\
Tailorized equivalent of
%s
"""


class DarcsTargetWorkingDir(SynchronizableTargetWorkingDir):
    """
    A target working directory under ``darcs``.
    """

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
        ExternalCommand(cwd=self.repository.basedir, command=cmd).execute(subdir)

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
        if changelog:
            logmessage.append(changelog)
        if not patchname and not changelog:
            logmessage.append('Unnamed patch')

        cmd = self.repository.command("record", "--all", "--pipe")
        if not entries:
            entries = ['.']

        record = ExternalCommand(cwd=self.repository.basedir, command=cmd)
        record.execute(input=self.repository.encode('\n'.join(logmessage)))

        if record.exit_status:
            raise ChangesetApplicationFailure(
                "%s returned status %d" % (str(record), record.exit_status))

    def _removePathnames(self, names):
        """
        Remove some filesystem object.
        """

        from os.path import join, exists

        # darcs raises status 512 when it does not find the entry,
        # removed by source. Since sometime a directory is left there
        # because it's not empty, darcs fails. So, do an explicit
        # remove on items that are still there.

        c = ExternalCommand(cwd=self.repository.basedir,
                            command=self.repository.command("remove"))
        existing = [n for n in names if exists(join(self.repository.basedir, n))]
        if existing:
            c.execute(existing)

    def _renamePathname(self, oldname, newname):
        """
        Rename a filesystem object.
        """

        cmd = self.repository.command("mv")
        ExternalCommand(cwd=self.repository.basedir, command=cmd).execute(oldname, newname)

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
            raise ChangesetApplicationFailure(
                "%s returned status %d saying\n%s" %
                (str(changes), changes.exit_status, output.read()))

        tags = []
        for cs in changesets_from_darcschanges_unsafe(output):
            for tag in cs.tags:
                if tag not in tags:
                    tags.append(tag)
        return tags
