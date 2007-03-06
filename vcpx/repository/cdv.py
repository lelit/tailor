# -*- mode: python; coding: utf-8 -*-
# :Progetto: vcpx -- Codeville details
# :Creato:   gio 05 mag 2005 23:47:45 CEST
# :Autore:   Lele Gaifax <lele@nautilus.homeip.net>
# :Licenza:  GNU General Public License
#

"""
This module implements the backends for Codeville.
"""

__docformat__ = 'reStructuredText'

from vcpx.repository import Repository
from vcpx.shwrap import ExternalCommand
from vcpx.target import SynchronizableTargetWorkingDir, TargetInitializationFailure
from vcpx.source import ChangesetApplicationFailure
from vcpx.tzinfo import UTC


class CdvRepository(Repository):
    METADIR = '.cdv'

    def _load(self, project):
        Repository._load(self, project)
        self.EXECUTABLE = project.config.get(self.name, 'cdv-command', 'cdv')

    def create(self):
        """
        Create the base directory if it doesn't exist, and the
        repository as well in the new working directory, executing
        a ``cdv init`` there.
        """

        from os.path import join, normpath, exists

        if exists(join(self.basedir, self.METADIR)):
            return

        init = ExternalCommand(cwd=self.basedir, command=self.command("init"))
        init.execute()

        if init.exit_status:
            raise TargetInitializationFailure(
                "%s returned status %s" % (str(init), init.exit_status))

class CdvWorkingDir(SynchronizableTargetWorkingDir):

    ## SynchronizableTargetWorkingDir

    def _replayChangeset(self, changeset):
        """
        Under Codeville, it's safer to explicitly edit modified items.
        """

        SynchronizableTargetWorkingDir._replayChangeset(self, changeset)

        names = [e.name for e in changeset.modifiedEntries()]
        cmd = self.repository.command("edit")
        ExternalCommand(cwd=self.repository.basedir, command=cmd).execute(names)

    def _addPathnames(self, names):
        """
        Add some new filesystem objects.
        """

        cmd = self.repository.command("add")
        ExternalCommand(cwd=self.repository.basedir, command=cmd).execute(names)

    def _commit(self, date, author, patchname, changelog=None, entries=None,
                tags = [], isinitialcommit = False):
        """
        Commit the changeset.
        """

        encode = self.repository.encode

        logmessage = []
        if patchname:
            logmessage.append(patchname)
        if changelog:
            logmessage.append(changelog.replace('%', '%%'))

        cmd = self.repository.command("-u", encode(author), "commit",
                                      "-m", encode('\n'.join(logmessage)),
                                      "-D", date.astimezone(UTC).strftime('%Y/%m/%d %H:%M:%S UTC'))

        if not entries:
            entries = ['...']

        c = ExternalCommand(cwd=self.repository.basedir, command=cmd)
        c.execute(entries)

        if c.exit_status:
            raise ChangesetApplicationFailure("%s returned status %d" %
                                              (str(c), c.exit_status))

    def _removePathnames(self, names):
        """
        Remove some filesystem object.
        """

        cmd = self.repository.command("remove")
        ExternalCommand(cwd=self.repository.basedir, command=cmd).execute(names)

    def _renamePathname(self, oldname, newname):
        """
        Rename a filesystem object.
        """

        cmd = self.repository.command("rename")
        ExternalCommand(cwd=self.repository.basedir, command=cmd).execute(oldname, newname)

    def _prepareTargetRepository(self):
        self.repository.create()

    def _prepareWorkingDirectory(self, source_repo):
        """
        Set the user on the repository.
        """

        from os import getenv

        cmd = self.repository.command("set", "user")
        user = getenv('CDV_USER') or getenv('LOGNAME')
        ExternalCommand(cwd=self.repository.basedir, command=cmd).execute(user)
