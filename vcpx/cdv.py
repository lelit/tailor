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

from shwrap import ExternalCommand
from target import SyncronizableTargetWorkingDir, TargetInitializationFailure
from source import ChangesetApplicationFailure

class CdvWorkingDir(SyncronizableTargetWorkingDir):

    ## SyncronizableTargetWorkingDir

    def _replayChangeset(self, changeset):
        """
        Under Codeville, it's safer to explicitly edit modified items.
        """

        SyncronizableTargetWorkingDir._replayChangeset(self, changeset)

        names = [e.name for e in changeset.modifiedEntries()]
        cmd = [self.repository.CDV_CMD, "edit"]
        ExternalCommand(cwd=self.basedir, command=cmd).execute(names)

    def _addPathnames(self, names):
        """
        Add some new filesystem objects.
        """

        cmd = [self.repository.CDV_CMD, "add"]
        ExternalCommand(cwd=self.basedir, command=cmd).execute(names)

    def _commit(self, date, author, patchname, changelog=None, entries=None):
        """
        Commit the changeset.
        """

        from sys import getdefaultencoding

        encoding = ExternalCommand.FORCE_ENCODING or getdefaultencoding()

        logmessage = []
        if patchname:
            logmessage.append(patchname.encode(encoding))
        if changelog:
            logmessage.append(changelog.replace('%', '%%').encode(encoding))

        cmd = [self.repository.CDV_CMD, "-u", author.encode(encoding), "commit",
               "-m", '\n'.join(logmessage),
               "-D", date.strftime('%Y/%m/%d %H:%M:%S UTC')]

        if not entries:
            entries = ['...']

        c = ExternalCommand(cwd=self.basedir, command=cmd)
        c.execute(entries)

        if c.exit_status:
            raise ChangesetApplicationFailure("%s returned status %d" %
                                              (str(c), c.exit_status))

    def _removePathnames(self, names):
        """
        Remove some filesystem object.
        """

        cmd = [self.repository.CDV_CMD, "remove"]
        ExternalCommand(cwd=self.basedir, command=cmd).execute(names)

    def _renamePathname(self, oldname, newname):
        """
        Rename a filesystem object.
        """

        cmd = [self.repository.CDV_CMD, "rename"]
        ExternalCommand(cwd=self.basedir, command=cmd).execute(oldname, newname)

    def _prepareTargetRepository(self):
        """
        Create the base directory if it doesn't exist, and the
        repository as well in the new working directory, executing
        a ``cdv init`` there.
        """

        from os.path import join, exists
        from os import makedirs

        if not exists(self.basedir):
            makedirs(self.basedir)

        if not exists(self.basedir, self.repository.METADIR):
            init = ExternalCommand(cwd=self.basedir,
                                   command=[self.repository.CDV_CMD, "init"])
            init.execute()

            if init.exit_status:
                raise TargetInitializationFailure(
                    "%s returned status %s" % (str(init), init.exit_status))

    def _prepareWorkingDirectory(self, source_repo):
        """
        Set the user on the repository.
        """

        from os import getenv
        from os.path import join

        cmd = [self.repository.CDV_CMD, "set", "user"]
        user = getenv('CDV_USER') or getenv('LOGNAME')
        ExternalCommand(cwd=self.basedir, command=cmd).execute(user)
