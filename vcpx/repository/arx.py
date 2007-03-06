# -*- mode: python; coding: utf-8 -*-
# :Progetto: vcpx -- ArX stuff
# :Creato:   ven 24 giu 2005 20:42:46 CEST
# :Autore:   Lele Gaifax <lele@nautilus.homeip.net>
# :Licenza:  GNU General Public License
#
# Modified 2005 by Walter Landry for ArX

"""
This module implements the backends for ArX.
"""

__docformat__ = 'reStructuredText'

from vcpx.repository import Repository
from vcpx.shwrap import ExternalCommand
from vcpx.target import SynchronizableTargetWorkingDir, TargetInitializationFailure
from vcpx.source import ChangesetApplicationFailure


class ArxRepository(Repository):
    METADIR = '_arx'

    def _load(self, project):
        Repository._load(self, project)
        self.EXECUTABLE = project.config.get(self.name, 'arx-command', 'arx')


class ArxWorkingDir(SynchronizableTargetWorkingDir):

    ## SynchronizableTargetWorkingDir

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

        cmd = self.repository.command("commit",
                                      "-s", encode('\n'.join(logmessage)),
                                      "--author", encode(author),
                                      "--date", date.isoformat())
        c = ExternalCommand(cwd=self.repository.basedir, command=cmd)
        c.execute()

        if c.exit_status:
            raise ChangesetApplicationFailure("%s returned status %d" %
                                              (str(c), c.exit_status))

    def _removePathnames(self, names):
        """
        Remove some filesystem object.
        """

        cmd = self.repository.command("rm")
        ExternalCommand(cwd=self.repository.basedir, command=cmd).execute(names)

    def _renamePathname(self, oldname, newname):
        """
        Rename a filesystem object.
        """

        cmd = self.repository.command("copy")
        rename = ExternalCommand(cwd=self.repository.basedir, command=cmd)
        rename.execute(oldname, newname)

    def _initializeWorkingDir(self):
        """
        Setup the ArX working copy

        The user must setup a ArX working directory himself. Then
        we simply use 'arx commit', without having to specify an archive
        or branch. ArX looks up the archive and branch in it's _arx
        directory.
        """

        from os.path import exists, join

        if not exists(join(self.repository.basedir, '_arx')):
            raise TargetInitializationFailure("Please setup '%s' as an ArX working directory" % self.repository.basedir)

        SynchronizableTargetWorkingDir._initializeWorkingDir(self)
