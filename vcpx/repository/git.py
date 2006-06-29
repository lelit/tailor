# -*- mode: python; coding: utf-8 -*-
# :Progetto: vcpx -- Git target (using git-core)
# :Creato:   Thu  1 Sep 2005 04:01:37 EDT
# :Autore:   Todd Mokros <tmokros@tmokros.net>
#            Brendan Cully <brendan@kublai.com>
#            Yann Dirson <ydirson@altern.org>
# :Licenza:  GNU General Public License
#

"""
This module implements the backend for Git using git-core.
"""

__docformat__ = 'reStructuredText'

from vcpx.repository import Repository
from vcpx.shwrap import ExternalCommand, PIPE
from vcpx.config import ConfigurationError
from vcpx.source import UpdatableSourceWorkingDir, GetUpstreamChangesetsFailure
from vcpx.source import ChangesetApplicationFailure
from vcpx.target import SynchronizableTargetWorkingDir, TargetInitializationFailure


    ## generic stuff

class GitRepository(Repository):
    METADIR = '.git'

    def _load(self, project):
        Repository._load(self, project)
        self.EXECUTABLE = project.config.get(self.name, 'git-command', 'git')
        self.PARENT_REPO = project.config.get(self.name, 'parent-repo')
        self.BRANCHPOINT = project.config.get(self.name, 'branchpoint', 'HEAD')
        self.BRANCHNAME = project.config.get(self.name, 'branch')
        if self.BRANCHNAME:
            self.BRANCHNAME = 'refs/heads/' + self.BRANCHNAME

        if self.repository and self.PARENT_REPO:
            self.log.critical('Cannot make sense of both "repository" and "parent-repo" parameters')
            raise ConfigurationError ('Must specify only one of "repository" and "parent-repo"')

        if self.BRANCHNAME and not self.repository:
            self.log.critical('Cannot make sense of "branch" if "repository" is not set')
            raise ConfigurationError ('Missing "repository" to make use o "branch"')

        self.env = {}

        if self.repository:
            self.storagedir = self.repository
            self.env['GIT_DIR'] = self.storagedir
            self.env['GIT_INDEX_FILE'] = self.METADIR + '/index'
        else:
            self.storagedir = self.METADIR

class GitExternalCommand(ExternalCommand):
    def __init__(self, repo, command=None, cwd=None):
        """
        Initialize an ExternalCommand instance tied to a GitRepository
        from which it inherits a set of environment variables to use
        for each execute().
        """

        self.repo = repo
        return ExternalCommand.__init__(self, command, cwd)

    def execute(self, *args, **kwargs):
        """Execute the command, with controlled environment."""

        if not kwargs.has_key('env'):
            kwargs['env'] = {}

        kwargs['env'].update(self.repo.env)

        return ExternalCommand.execute(self, *args, **kwargs)

class GitWorkingDir(UpdatableSourceWorkingDir, SynchronizableTargetWorkingDir):

    def _tryCommand(self, cmd, exception=Exception, pipe=True):
        c = GitExternalCommand(self.repository,
                               command = self.repository.command(*cmd), cwd = self.basedir)
        if pipe:
            output = c.execute(stdout=PIPE)[0]
        else:
            c.execute()
        if c.exit_status:
            raise exception(str(c) + ' failed')
        if pipe:
            return output.read().split('\n')

    ## UpdatableSourceWorkingDir

    def _checkoutUpstreamRevision(self, revision):
        """ git clone """
        from os import rename, rmdir
        from os.path import join

        # Right now we clone the entire repository and just check out to the
        # current rev because it makes revision parsing easier. We can't
        # easily check out arbitrary revisions anyway, but we could probably
        # handle HEAD (master) as a special case...
        # git clone won't checkout into an existing directory
        target = join(self.basedir, '.gittmp')
        # might want -s if we can determine that the path is local. Then again,
        # that makes it a little unsafe to do git write actions here
        self._tryCommand(['clone', '-n', self.repository.repository, target],
                         ChangesetApplicationFailure, False)

        rename(join(target, '.git'), join(self.basedir, '.git'))
        rmdir(target)

        rev = self._getRev(revision)
        if rev != revision:
            self.log.info('Checking out revision %s (%s)' % (rev, revision))
        else:
            self.log.info('Checking out revision ' + rev)
        self._tryCommand(['reset', '--hard', rev], ChangesetApplicationFailure, False)

        return self._changesetForRevision(rev)

    def _getUpstreamChangesets(self, since):
        self._tryCommand(['fetch'], GetUpstreamChangesetsFailure, False)

        revs = self._tryCommand(['rev-list', '^' + since, 'origin'],
                                GetUpstreamChangesetsFailure)[:-1]
        revs.reverse()
        for rev in revs:
            self.log.info('Updating to revision ' + rev)
            yield self._changesetForRevision(rev)

    def _applyChangeset(self, changeset):
        out = self._tryCommand(['merge', '-n', '--no-commit', 'fastforward',
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
        lines = self._tryCommand(['rev-list', '--pretty=raw', '--max-count=1', revision],
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
                tzsecs = (tz / 100 * 60 + tz % 100) * 60
                if tz < 0:
                    tzsecs = -tzsecs
                date = datetime.utcfromtimestamp(dt + tzsecs)
            if line.startswith('    '):
                loglines.append(line.lstrip('    '))

        message = '\n'.join(loglines)
        entries = []
        cmd = ['diff-tree', '--root', '-r', '-M', '--name-status']
        # haven't thought about merges yet...
        if parents:
            cmd.append(parents[0])
        cmd.append(revision)
        files = self._tryCommand(cmd, GetUpstreamChangesetsFailure)[:-1]
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

        # Brute-force tag search
        from os.path import join
        from os import listdir

        tags = []
        tagdir = join(self.basedir, '.git', 'refs', 'tags')
        try:
            for tag in listdir(tagdir):
                # Consider caching stat info per tailor run
                tagrev = self._tryCommand(['rev-list', '--max-count=1', tag])[0]
                if (tagrev == revision):
                    tags.append(tag)
        except OSError:
            # No tag dir
            pass

        return Changeset(revision, date, user, message, entries, tags=tags)

    def _getRev(self, revision):
        """ Return the git object corresponding to the symbolic revision """
        if revision == 'INITIAL':
            return self._tryCommand(['rev-list', 'HEAD'], GetUpstreamChangesetsFailure)[-2]

        return self._tryCommand(['rev-parse', '--verify', revision], GetUpstreamChangesetsFailure)[0]

    ## SynchronizableTargetWorkingDir

    def _addPathnames(self, names):
        """
        Add some new filesystem objects.
        """

        from os.path import join, isdir

        # Currently git does not handle directories at all, so filter
        # them out.

        notdirs = [n for n in names if not isdir(join(self.basedir, n))]
        if notdirs:
            self._tryCommand(['update-index', '--add'] + notdirs)

    def _editPathnames(self, names):
        """
        Records a sequence of filesystem objects as updated.
        """

        # can we assume we don't have directories in the list ?
        self._tryCommand(['update-index'] + names)

    def __parse_author(self, author):
        """
        Parse the author field, returning (name, email)
        """
        from email.Utils import parseaddr
        from vcpx.target import AUTHOR, HOST

        if author.find('@') > -1:
            name, email = parseaddr(author)
        else:
            name, email = author, ''
        name = name.strip()
        email = email.strip()
        if not name:
            name = AUTHOR
        if not email:
            email = "%s@%s" % (AUTHOR, HOST)
        return (name, email)

    def _commit(self, date, author, patchname, changelog=None, entries=None):
        """
        Commit the changeset.
        """

        from os import environ

        encode = self.repository.encode

        logmessage = []
        if patchname:
            logmessage.append(patchname)
        if changelog:
            logmessage.append(changelog)

        env = {}
        env.update(environ)

        treeid = self._tryCommand(['write-tree'])[0]

        # in single-repository mode, only update the relevant branch
        if self.repository.BRANCHNAME:
            refname = self.repository.BRANCHNAME
        else:
            refname = 'HEAD'

        # find the previous commit on the branch if any
        c = GitExternalCommand(self.repository, cwd=self.basedir,
                               command=self.repository.command('rev-parse', refname))
        (out, err) = c.execute(stdout=PIPE, stderr=PIPE)
        if c.exit_status:
            # Do we need to check err to be sure there was no error ?
            self.log.info("Doing initial commit")
            parent = False
        else:
            # FIXME: I'd prefer to avoid all those "if parent"
            parent = out.read().split('\n')[0]

        (name, email) = self.__parse_author(author)
        if name:
            env['GIT_AUTHOR_NAME'] = encode(name)
            env['GIT_COMMITTER_NAME'] = encode(name)
        if email:
            env['GIT_AUTHOR_EMAIL']=email
            env['GIT_COMMITTER_EMAIL']=email
        if date:
            env['GIT_AUTHOR_DATE']=date.strftime("%Y-%m-%d %H:%M:%S")
            env['GIT_COMMITTER_DATE']=env['GIT_AUTHOR_DATE']
        if parent:
            cmd = self.repository.command('commit-tree', treeid, '-p', parent)
        else:
            cmd = self.repository.command('commit-tree', treeid)
        c = GitExternalCommand(self.repository, cwd=self.basedir, command=cmd)

        logmessage = encode('\n'.join(logmessage))
        if not logmessage:
            logmessage = 'No commit message\n'
        if not logmessage.endswith('\n'):
            logmessage += '\n'
        (out, _) = c.execute(stdout=PIPE, env=env, input=logmessage)
        if c.exit_status:
            failed = True
            if out:
                for line in [x.strip() for x in out if x[0] != '#']:
                    if line == 'nothing to commit':
                        failed = False
            if failed:
                raise ChangesetApplicationFailure("%s returned status %d" %
                                                  (str(c), c.exit_status))
        else:
            commitid=out.read().split('\n')[0]

            if parent:
                self._tryCommand(['update-ref', refname, commitid, parent])
            else:
                self._tryCommand(['update-ref', refname, commitid])

    def _tag(self, tag):
        # Allow a new tag to overwrite an older one with -f
        cmd = self.repository.command("tag", "-f", tag)
        c = GitExternalCommand(self.repository, cwd=self.basedir, command=cmd)
        c.execute()

        if c.exit_status:
            raise ChangesetApplicationFailure("%s returned status %d" %
                                              (str(c), c.exit_status))

    def _removePathnames(self, names):
        """
        Remove some filesystem object.
        """

        from os.path import join, isdir

        # Currently git does not handle directories at all, so filter
        # them out.

        notdirs = [n for n in names if not isdir(join(self.basedir, n))]
        if notdirs:
            self._tryCommand(['update-index', '--remove'] + notdirs)

    def _renamePathname(self, oldname, newname):
        """
        Rename a filesystem object.
        """
        # In the future, we may want to switch to using
        # git rename, in case renames ever get more support
        # in git.  It currently just does and add and remove.
        from os.path import join, isdir
        from os import walk
        from vcpx.dualwd import IGNORED_METADIRS

        if isdir(join(self.basedir, newname)):
            # Given lack of support for directories in current Git,
            # loop over all files under the new directory and
            # do a add/remove on them.
            skip = len(self.basedir)+len(newname)+2
            for dir, subdirs, files in walk(join(self.basedir, newname)):
                prefix = dir[skip:]

                for excd in IGNORED_METADIRS:
                    if excd in subdirs:
                        subdirs.remove(excd)

                for f in files:
                    self._removePathnames([join(oldname, prefix, f)])
                    self._addPathnames([join(newname, prefix, f)])
        else:
            self._removePathnames([oldname])
            self._addPathnames([newname])

    def _prepareTargetRepository(self):
        """
        Initialize .git through ``git init-db`` or ``git-clone``.
        """

        from os import renames, mkdir
        from os.path import join, exists

        if not exists(join(self.basedir, self.repository.METADIR)):
            if self.repository.PARENT_REPO:
                cmd = self.repository.command("clone", "--shared", "-n",
                                              self.repository.PARENT_REPO, 'tmp')
                clone = GitExternalCommand(self.repository, cwd=self.basedir, command=cmd)
                clone.execute()
                if clone.exit_status:
                    raise TargetInitializationFailure(
                        "%s returned status %s" % (str(clone), clone.exit_status))

                renames('%s/%s/tmp/.git' % (self.repository.rootdir, self.repository.subdir),
                        '%s/%s/.git' % (self.repository.rootdir, self.repository.subdir))
                
                cmd = self.repository.command("reset", "--soft", self.repository.BRANCHPOINT)
                reset = GitExternalCommand(self.repository, cwd=self.basedir, command=cmd)
                reset.execute()
                if reset.exit_status:
                    raise TargetInitializationFailure(
                        "%s returned status %s" % (str(reset), reset.exit_status))

            elif self.repository.repository and self.repository.BRANCHNAME:
                # ...and exists(self.repository.storagedir) ?

                # initialization of a new branch in single-repository mode
                mkdir(join(self.basedir, self.repository.METADIR))

                bp = self._tryCommand(['rev-parse', self.repository.BRANCHPOINT])[0]
                self._tryCommand(['read-tree', bp])
                self._tryCommand(['update-ref', self.repository.BRANCHNAME, bp])
                #self._tryCommand(['checkout-index'])

            else:
                self._tryCommand(['init-db'])
                if self.repository.repository:
                    # in this mode, the db is not stored in working dir, so we
                    # have to create .git ourselves
                    mkdir(join(self.basedir, self.repository.METADIR))

    def _prepareWorkingDirectory(self, source_repo):
        """
        Create the .git/info/exclude.
        """

        from os.path import join, exists
        from os import mkdir
        from vcpx.dualwd import IGNORED_METADIRS

        # create info/excludes in storagedir
        infodir = join(self.basedir, self.repository.storagedir, 'info')
        if not exists(infodir):
            mkdir(infodir)

        # Create the .git/info/exclude file, that contains an
        # fnmatch per line with metadirs to be skipped.
        ignore = open(join(infodir, 'exclude'), 'a')
        ignore.write('\n')
        ignore.write('\n'.join(['%s' % md
                                for md in IGNORED_METADIRS]))
        ignore.write('\n')
        if self.logfile.startswith(self.basedir):
            ignore.write(self.logfile[len(self.basedir)+1:])
            ignore.write('\n')
        if self.state_file.filename.startswith(self.basedir):
            sfrelname = self.state_file.filename[len(self.basedir)+1:]
            ignore.write(sfrelname)
            ignore.write('\n')
            ignore.write(sfrelname+'.old')
            ignore.write('\n')
            ignore.write(sfrelname+'.journal')
            ignore.write('\n')
        ignore.close()

    def importFirstRevision(self, source_repo, changeset, initial):
        # If we have a parent repository, always track from INITIAL
        SynchronizableTargetWorkingDir.importFirstRevision(
            self, source_repo, changeset,
            initial or self.repository.PARENT_REPO)
