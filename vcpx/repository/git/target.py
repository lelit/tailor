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

from vcpx import TailorException
from vcpx.config import ConfigurationError
from vcpx.repository.git import GitExternalCommand, PIPE
from vcpx.source import ChangesetApplicationFailure
from vcpx.target import SynchronizableTargetWorkingDir, TargetInitializationFailure
from vcpx.tzinfo import FixedOffset


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

        from os.path import join, isdir

        # can we assume we don't have directories in the list ?  Nope.

        notdirs = [n for n in names if not isdir(join(self.repository.basedir, n))]
        if notdirs:
            self.repository.runCommand(['update-index'] + notdirs)

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
            email = "%s@%s" % (name, HOST)
        return (name, email)

    def _commit(self, date, author, patchname, changelog=None, entries=None,
                tags=[], isinitialcommit=False):
        """
        Commit the changeset.
        """

        from os import environ

        try:
            self.repository.runCommand(['status'])
        except Exception, e:
            self.log.info("git-status returned an error---assuming nothing to do")
            return

        encode = self.repository.encode

        logmessage = []
        if patchname:
            logmessage.append(patchname)
        if changelog:
            logmessage.append(changelog)

        env = {}
        env.update(environ)

        # update the index
        self.repository.runCommand(['add', '-u'])
        treeid = self.repository.runCommand(['write-tree'])[0]

        # in single-repository mode, only update the relevant branch
        if self.repository.branch_name:
            refname = self.repository.branch_name
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

    def _tag(self, tag, date, author):

        # in single-repository mode, only update the relevant branch
        if self.repository.branch_name:
            refname = self.repository.branch_name
        else:
            refname = 'HEAD'

        # Allow a new tag to overwrite an older one with -f
        args = ["tag", "-a",]
        if self.repository.overwrite_tags:
                args.append("-f")

        # Escape the tag name for git
        import re
        tag_git = re.sub('_*$', '', re.sub('__', '_', re.sub('[^A-Za-z0-9_-]', '_', tag)))

        args += ["-m", tag, tag_git, refname]
        cmd = self.repository.command(*args)
        c = GitExternalCommand(self.repository, cwd=self.repository.basedir, command=cmd)
        from os import environ
        env = {}
        env.update(environ)
        (name, email) = self.__parse_author(author)
        if name:
            env['GIT_AUTHOR_NAME'] = self.repository.encode(name)
            env['GIT_COMMITTER_NAME'] = self.repository.encode(name)
        if email:
            env['GIT_AUTHOR_EMAIL']=email
            env['GIT_COMMITTER_EMAIL']=email
        if date:
            env['GIT_AUTHOR_DATE']=date.strftime("%Y-%m-%d %H:%M:%S %z")
            env['GIT_COMMITTER_DATE']=env['GIT_AUTHOR_DATE']
        c.execute(env=env)

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

        # Git does not seem to allow
        #   $ mv a.txt b.txt
        #   $ git mv a.txt b.txt
        # Here we are in this situation, since upstream VCS already
        # moved the item.

        from os import mkdir, rename, rmdir, listdir
        from os.path import join, exists, isdir

        oldpath = join(self.repository.basedir, oldname)
        newpath = join(self.repository.basedir, newname)

        # Git does not track empty directories, so if there is only an
        # empty dir, we have nothing to do.
        if isdir(newpath) and not len(listdir(newpath)):
            return

        # rename() won't work for rename(a/b, a)
        if newpath.startswith(oldpath+"/"):
            oldpathtmp = oldpath+"-TAILOR-HACKED-TEMP-NAME"
            oldnametmp = oldname+"-TAILOR-HACKED-TEMP-NAME"
            if exists(oldpathtmp):
                rename(oldpathtmp, oldpath)
            rename(newpath, oldpathtmp)
            rmdir(oldpath)
            rename(oldpathtmp, oldpath)
            mkdir(oldpathtmp)
            self.repository.runCommand(['mv', oldname, newname.replace(oldname, oldnametmp, 1)])
            self.repository.runCommand(['mv', oldnametmp, oldname])
        else:
            # we can just add the new path, commit will detect the
            # deleted ones automatically
            self.repository.runCommand(['add', newname])

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
            initial or self.repository.branch_point)
