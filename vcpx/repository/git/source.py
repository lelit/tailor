# -*- mode: python; coding: utf-8 -*-
# :Progetto: vcpx -- Git target (using git-core)
# :Creato:   Thu  1 Sep 2005 04:01:37 EDT
# :Autore:   Todd Mokros <tmokros@tmokros.net>
#            Brendan Cully <brendan@kublai.com>
#            Yann Dirson <ydirson@altern.org>
# :Licenza:  GNU General Public License
#

"""
This module implements the source backend for Git using git-core.
"""

__docformat__ = 'reStructuredText'

from vcpx.shwrap import ExternalCommand, PIPE
from vcpx.config import ConfigurationError
from vcpx.source import UpdatableSourceWorkingDir, GetUpstreamChangesetsFailure
from vcpx.source import ChangesetApplicationFailure
from vcpx.tzinfo import FixedOffset

class GitSourceWorkingDir(UpdatableSourceWorkingDir):

    def _checkoutUpstreamRevision(self, revision):
        """ git clone """
        from os import rename, rmdir
        from os.path import join

        # Right now we clone the entire repository and just check out to the
        # current rev because it makes revision parsing easier. We can't
        # easily check out arbitrary revisions anyway, but we could probably
        # handle HEAD (master) as a special case...
        # git clone won't checkout into an existing directory
        target = join(self.repository.basedir, '.gittmp')
        # might want -s if we can determine that the path is local. Then again,
        # that makes it a little unsafe to do git write actions here
        self.repository.runCommand(['clone', '-n', self.repository.repository, target],
                                    ChangesetApplicationFailure, False)

        rename(join(target, '.git'), join(self.repository.basedir, '.git'))
        rmdir(target)

        rev = self._getRev(revision)
        if rev != revision:
            self.log.info('Checking out revision %s (%s)' % (rev, revision))
        else:
            self.log.info('Checking out revision ' + rev)
        self.repository.runCommand(['reset', '--hard', rev], ChangesetApplicationFailure, False)

        return self._changesetForRevision(rev)

    def _getUpstreamChangesets(self, since):
        # Brute-force tag search
        from os.path import join
        from os import listdir

        tags = {}
        tagdir = join(self.repository.basedir, '.git', 'refs', 'tags')
        try:
            for tag in listdir(tagdir):
                tagrev = self.repository.runCommand(['rev-list', '--max-count=1', tag])[0]
                tags.setdefault(tagrev, []).append(tag)
        except OSError:
            # No tag dir
            pass

        self.repository.runCommand(['fetch'], GetUpstreamChangesetsFailure, False)

        revs = self.repository.runCommand(['rev-list', '^' + since, 'origin'],
                                           GetUpstreamChangesetsFailure)[:-1]
        revs.reverse()
        for rev in revs:
            cs = self._changesetForRevision(rev)
            if rev in tags:
                cs.tags = tags[rev]
            yield cs

    def _applyChangeset(self, changeset):
        out = self.repository.runCommand(['merge', '-n', '--no-commit', 'fastforward',
                                           'HEAD', changeset.revision],
                                          ChangesetApplicationFailure)

        conflicts = []
        for line in out:
            if line.endswith(': needs update'):
                conflicts.append(line[:-14])

        if conflicts:
            self.log.warning("Conflict after 'git merge': %s", ' '.join(conflicts))

        return conflicts

    def _changesetForRevision(self, revision):
        from datetime import datetime
        from vcpx.changes import Changeset, ChangesetEntry

        action_map = {'A': ChangesetEntry.ADDED, 'D': ChangesetEntry.DELETED,
                      'M': ChangesetEntry.UPDATED, 'R': ChangesetEntry.RENAMED}

        # find parent
        lines = self.repository.runCommand(['rev-list', '--pretty=raw', '--max-count=1', revision],
                                            GetUpstreamChangesetsFailure)
        parents = []
        user = Changeset.ANONYMOUS_USER
        loglines = []
        date = None
        for line in lines:
            if line.startswith('parent'):
                parents.append(line.split(' ').pop())
            if line.startswith('author'):
                author_fields = line.split(' ')[1:]
                tz = int(author_fields.pop())
                dt = int(author_fields.pop())
                user = ' '.join(author_fields)
                tzsecs = abs(tz)
                tzsecs = (tzsecs / 100 * 60 + tzsecs % 100) * 60
                if tz < 0:
                    tzsecs = -tzsecs
                date = datetime.fromtimestamp(dt, FixedOffset(tzsecs/60))
            if line.startswith('    '):
                loglines.append(line.lstrip('    '))

        message = '\n'.join(loglines)
        entries = []
        cmd = ['diff-tree', '--root', '-r', '-M', '--name-status']
        # haven't thought about merges yet...
        if parents:
            cmd.append(parents[0])
        cmd.append(revision)
        files = self.repository.runCommand(cmd, GetUpstreamChangesetsFailure)[:-1]
        if not parents:
            # git lets us know what it's diffing against if we omit parent
            if len(files) > 0:
                files.pop(0)
        for line in files:
            fields = line.split('\t')
            state = fields.pop(0)
            name = fields.pop()
            e = ChangesetEntry(name)
            e.action_kind = action_map[state[0]]
            if e.action_kind == ChangesetEntry.RENAMED:
                e.old_name = fields.pop()

            entries.append(e)

        return Changeset(revision, date, user, message, entries)

    def _getRev(self, revision):
        """ Return the git object corresponding to the symbolic revision """
        if revision == 'INITIAL':
            return self.repository.runCommand(['rev-list', 'HEAD'], GetUpstreamChangesetsFailure)[-2]

        return self.repository.runCommand(['rev-parse', '--verify', revision], GetUpstreamChangesetsFailure)[0]
