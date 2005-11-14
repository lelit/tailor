# -*- mode: python; coding: utf-8 -*-
# :Progetto: vcpx -- Git target (using git-core)
# :Creato:   Thu  1 Sep 2005 04:01:37 EDT
# :Autore:   Todd Mokros <tmokros@tmokros.net>
# :Licenza:  GNU General Public License
#

"""
This module implements the backend for Git using git-core.
"""

__docformat__ = 'reStructuredText'

from shwrap import ExternalCommand, ReopenableNamedTemporaryFile, PIPE
from target import SyncronizableTargetWorkingDir, TargetInitializationFailure
from source import ChangesetApplicationFailure

class GitWorkingDir(SyncronizableTargetWorkingDir):

    ## SyncronizableTargetWorkingDir

    def _addPathnames(self, names):
        """
        Add some new filesystem objects.
        """

        from os.path import join, isdir

        # Currently git does not handle directories at all, so filter
        # them out.

        notdirs = [n for n in names if not isdir(join(self.basedir, n))]
        if notdirs:
            cmd = self.repository.command("add")
            ExternalCommand(cwd=self.basedir, command=cmd).execute(notdirs)

    def __parse_author(self, author):
        """
        Parse the author field, returning (name, email)
        """
        from email.Utils import parseaddr
        from target import AUTHOR, HOST

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

        from time import mktime
        from os import environ

        logmessage = []
        if patchname:
            logmessage.append(patchname)
        if changelog:
            logmessage.append(changelog)

        env = {}
        env.update(environ)

        (name, email) = self.__parse_author(author)
        if name:
            env['GIT_AUTHOR_NAME']=name
            env['GIT_COMMITTER_NAME']=name
        if email:
            env['GIT_AUTHOR_EMAIL']=email
            env['GIT_COMMITTER_EMAIL']=email
        if date:
            env['GIT_AUTHOR_DATE']=date.strftime("%Y-%m-%d %H:%M:%S")
            env['GIT_COMMITTER_DATE']=env['GIT_AUTHOR_DATE']
        # '-f' flag means we can get empty commits, which
        # shouldn't be a problem.
        cmd = self.repository.command("commit", "-a", "-F", "-")
        c = ExternalCommand(cwd=self.basedir, command=cmd)

        logmessage = '\n'.join(logmessage)
        if not logmessage.endswith('\n'):
            logmessage += '\n'
        (out, _) = c.execute(stdout=PIPE, env=env, input=logmessage)
        if c.exit_status:
            if out is None or out.readline().strip() != 'nothing to commit':
                raise ChangesetApplicationFailure("%s returned status %d" %
                                                  (str(c), c.exit_status))
            else:
                # empty changeset, which git-core doesn't support
                pass

    def _removePathnames(self, names):
        """
        Remove some filesystem object.
        git commit -a will automatically handle files deleted on the
        filesystem, which should have already been done by the source
        or rsync.
        """
        pass

    def _renamePathname(self, oldname, newname):
        """
        Rename a filesystem object.
        """
        # In the future, we may want to switch to using
        # git rename, in case renames ever get more support
        # in git.  It currently just does and add and remove.
        from os.path import join, isdir
        from os import walk
        from dualwd import IGNORED_METADIRS

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
        Execute ``git init-db``.
        """

        from os.path import join, exists

        if not exists(join(self.basedir, self.repository.METADIR)):
            init = ExternalCommand(cwd=self.basedir,
                                   command=self.repository.command("init-db"))
            init.execute()

            if init.exit_status:
                raise TargetInitializationFailure(
                    "%s returned status %s" % (str(init), init.exit_status))

    def _prepareWorkingDirectory(self, source_repo):
        """
        Create the .git/info/exclude.
        """

        from os.path import join
        from re import escape
        from dualwd import IGNORED_METADIRS

        # Create the .git/info/exclude file, that contains an
        # fnmatch per line with metadirs to be skipped.
        ignore = open(join(self.basedir, self.repository.METADIR,
                           'info', 'exclude'), 'a')
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

