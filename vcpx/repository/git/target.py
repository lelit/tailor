# -*- mode: python; coding: utf-8 -*-
# :Progetto: vcpx -- Git target (using git-core)
# :Creato:   Thu  1 Sep 2005 04:01:37 EDT
# :Autore:   Todd Mokros <tmokros@tmokros.net>
#            Brendan Cully <brendan@kublai.com>
#            Yann Dirson <ydirson@altern.org>
# :Licenza:  GNU General Public License
#

"""
This module implements the target backend for Git using git-core.
"""

__docformat__ = 'reStructuredText'

from vcpx.repository.git import GitExternalCommand, PIPE
from vcpx.config import ConfigurationError
from vcpx.target import SynchronizableTargetWorkingDir, TargetInitializationFailure
from vcpx.tzinfo import FixedOffset
from vcpx import TailorException


class BranchpointFailure(TailorException):
    "Specified branchpoint not found in parent branch"


class GitTargetWorkingDir(SynchronizableTargetWorkingDir):

    def _addPathnames(self, names):
        """
        Add some new filesystem objects.
        """

        from os.path import join, isdir

        # Currently git does not handle directories at all, so filter
        # them out.

        notdirs = [n for n in names if not isdir(join(self.repository.basedir, n))]
        if notdirs:
            self.repository.runCommand(['update-index', '--add'] + notdirs)

    def _editPathnames(self, names):
        """
        Records a sequence of filesystem objects as updated.
        """

        # can we assume we don't have directories in the list ?
        self.repository.runCommand(['update-index'] + names)

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

        treeid = self.repository.runCommand(['write-tree'])[0]

        # in single-repository mode, only update the relevant branch
        if self.repository.BRANCHNAME:
            refname = self.repository.BRANCHNAME
        else:
            refname = 'HEAD'

        # find the previous commit on the branch if any
        c = GitExternalCommand(self.repository, cwd=self.repository.basedir,
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
            env['GIT_AUTHOR_DATE']=date.strftime("%Y-%m-%d %H:%M:%S %z")
            env['GIT_COMMITTER_DATE']=env['GIT_AUTHOR_DATE']
        if parent:
            cmd = self.repository.command('commit-tree', treeid, '-p', parent)
        else:
            cmd = self.repository.command('commit-tree', treeid)
        c = GitExternalCommand(self.repository, cwd=self.repository.basedir, command=cmd)

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
                self.repository.runCommand(['update-ref', refname, commitid, parent])
            else:
                self.repository.runCommand(['update-ref', refname, commitid])

    def _tag(self, tag):
        # Allow a new tag to overwrite an older one with -f
        cmd = self.repository.command("tag", "-f", tag)
        c = GitExternalCommand(self.repository, cwd=self.repository.basedir, command=cmd)
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

        notdirs = [n for n in names if not isdir(join(self.repository.basedir, n))]
        if notdirs:
            self.repository.runCommand(['update-index', '--remove'] + notdirs)

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

        if isdir(join(self.repository.basedir, newname)):
            # Given lack of support for directories in current Git,
            # loop over all files under the new directory and
            # do a add/remove on them.
            skip = len(self.repository.basedir)+len(newname)+2
            for dir, subdirs, files in walk(join(self.repository.basedir, newname)):
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
        self.repository.create()

    def _prepareWorkingDirectory(self, source_repo):
        """
        Create the .git/info/exclude.
        """

        from os.path import join, exists
        from os import mkdir
        from vcpx.dualwd import IGNORED_METADIRS

        # create info/excludes in storagedir
        infodir = join(self.repository.basedir, self.repository.storagedir, 'info')
        if not exists(infodir):
            mkdir(infodir)

        # Create the .git/info/exclude file, that contains an
        # fnmatch per line with metadirs to be skipped.
        ignore = open(join(infodir, 'exclude'), 'a')
        ignore.write('\n')
        ignore.write('\n'.join(['%s' % md
                                for md in IGNORED_METADIRS]))
        ignore.write('\n')
        if self.logfile.startswith(self.repository.basedir):
            ignore.write(self.logfile[len(self.repository.basedir)+1:])
            ignore.write('\n')
        if self.state_file.filename.startswith(self.repository.basedir):
            sfrelname = self.state_file.filename[len(self.repository.basedir)+1:]
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
            initial or self.repository.BRANCHPOINT)
