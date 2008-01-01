# -*- mode: python; coding: utf-8 -*-
# :Progetto: vcpx -- Git target (using git-core)
# :Creato:   Thu  1 Sep 2005 04:01:37 EDT
# :Autore:   Todd Mokros <tmokros@tmokros.net>
#            Brendan Cully <brendan@kublai.com>
#            Yann Dirson <ydirson@altern.org>
# :Licenza:  GNU General Public License
#

"""
This module implements the parts of the backend for Git using git-core,
common to source and target modules.
"""

__docformat__ = 'reStructuredText'

from vcpx.config import ConfigurationError
from vcpx.repository import Repository
from vcpx.shwrap import ExternalCommand, PIPE
from vcpx.target import TargetInitializationFailure


class GitRepository(Repository):
    METADIR = '.git'

    def _load(self, project):
        Repository._load(self, project)
        self.EXECUTABLE = project.config.get(self.name, 'git-command', 'git')
        self.overwrite_tags = project.config.get(self.name, 'overwrite-tags', False)
        self.parent_repo = project.config.get(self.name, 'parent-repo')
        self.branch_point = project.config.get(self.name, 'branchpoint', 'HEAD')
        self.branch_name = project.config.get(self.name, 'branch')
        if self.branch_name:
            self.branch_name = 'refs/heads/' + self.branch_name

        if self.repository and self.parent_repo:
            self.log.critical('Cannot make sense of both "repository" and "parent-repo" parameters')
            raise ConfigurationError ('Must specify only one of "repository" and "parent-repo"')

        if self.branch_name and not self.repository:
            self.log.critical('Cannot make sense of "branch" if "repository" is not set')
            raise ConfigurationError ('Missing "repository" to make use o "branch"')

        self.env = {}

        # XXX: this seems plain wrong to me [who does not know git at
        # all!]: why storagedir gets set to repository here? and why
        # the need for the GIT_DIR envvar? I fail to see when
        # storagedir should be different from '.git', the default,
        # given how it's being used by this class! The same with
        # GIT_INDEX_FILE, that accordingly with the man page defaults
        # to ".git/index" anyway...
        #
        self.storagedir = self.METADIR
        if self.repository:
            from os.path import join

            #self.storagedir = self.repository
            #self.env['GIT_DIR'] = self.storagedir
            self.env['GIT_DIR'] = join(self.basedir, self.METADIR)
            self.env['GIT_INDEX_FILE'] = self.METADIR + '/index'
        #else:
        #    self.storagedir = self.METADIR

    def runCommand(self, cmd, exception=Exception, pipe=True):
        """
        Facility to run a git command in a controlled context.
        """

        c = GitExternalCommand(self,
                               command = self.command(*cmd), cwd = self.basedir)
        if pipe:
            output = c.execute(stdout=PIPE)[0]
        else:
            c.execute()
        if c.exit_status:
            raise exception(str(c) + ' failed')
        if pipe:
            return output.read().split('\n')

    def create(self):
        """
        Initialize .git through ``git init-db`` or ``git-clone``.
        """

        from os import renames, mkdir
        from os.path import join, exists

        if exists(join(self.basedir, self.METADIR)):
            return

        if self.parent_repo:
            cmd = self.command("clone", "--shared", "-n", self.parent_repo, 'tmp')
            clone = GitExternalCommand(self, cwd=self.basedir, command=cmd)
            clone.execute()
            if clone.exit_status:
                raise TargetInitializationFailure(
                    "%s returned status %s" % (str(clone), clone.exit_status))

            renames(join(self.basedir, 'tmp', '.git'), join(self.basedir, '.git'))

            cmd = self.command("reset", "--soft", self.branch_point)
            reset = GitExternalCommand(self, cwd=self.basedir, command=cmd)
            reset.execute()
            if reset.exit_status:
                raise TargetInitializationFailure(
                    "%s returned status %s" % (str(reset), reset.exit_status))

        elif self.repository and self.branch_name:
            # ...and exists(self.storagedir) ?

            # initialization of a new branch in single-repository mode
            mkdir(join(self.basedir, self.METADIR))

            bp = self.runCommand(['rev-parse', self.branch_point])[0]
            self.runCommand(['read-tree', bp])
            self.runCommand(['update-ref', self.branch_name, bp])
            #self.runCommand(['checkout-index'])

        else:
            if exists(join(self.basedir, self.storagedir)):
                raise TargetInitializationFailure(
                    "Repository %s already exists - "
                    "did you forget to set \"branch\" parameter ?" % self.storagedir)

            self.runCommand(['init-db'])
            if self.repository:
                # in this mode, the db is not stored in working dir, so we
                # may have to create .git ourselves
                try:
                    mkdir(join(self.basedir, self.METADIR))
                except OSError:
                    # if it's already there, that's not a no problem
                    pass


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
