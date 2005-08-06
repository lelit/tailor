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

from shwrap import ExternalCommand, PIPE
from target import SyncronizableTargetWorkingDir, TargetInitializationFailure

class CdvWorkingDir(SyncronizableTargetWorkingDir):

    ## SyncronizableTargetWorkingDir

    def _addPathnames(self, root, names):
        """
        Add some new filesystem objects.
        """

        cmd = [self.repository.CDV_CMD, "add"]
        ExternalCommand(cwd=root, command=cmd).execute(names)

    def _commit(self,root, date, author, patchname, changelog=None, entries=None):
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
        logmessage.append('')

        cmd = [self.repository.CDV_CMD, "-u", author.encode(encoding), "commit",
               "-m", '\n'.join(logmessage),
               "-D", date.strftime('%Y/%m/%d %H:%M:%S UTC')]

        if not entries:
            entries = ['.']

        ExternalCommand(cwd=root, command=cmd).execute(entries)

    def _removePathnames(self, root, names):
        """
        Remove some filesystem object.
        """

        cmd = [self.repository.CDV_CMD, "remove"]
        ExternalCommand(cwd=root, command=cmd).execute(names)

    def _renamePathname(self, root, oldname, newname):
        """
        Rename a filesystem object.
        """

        cmd = [self.repository.CDV_CMD, "rename"]
        ExternalCommand(cwd=root, command=cmd).execute(oldname, newname)

    def initializeNewWorkingDir(self, root, source_repository, source_module,
                                subdir, changeset, initial):
        """
        Initialize a new working directory, just extracted from
        some other VC system, importing everything's there.
        """

        from target import AUTHOR, HOST, BOOTSTRAP_PATCHNAME, \
             BOOTSTRAP_CHANGELOG

        self._initializeWorkingDir(root, source_repository, source_module,
                                   subdir)
        revision = changeset.revision
        if initial:
            author = changeset.author
            patchname = changeset.log
            log = None
        else:
            author = "%s@%s" % (AUTHOR, HOST)
            patchname = BOOTSTRAP_PATCHNAME % source_module
            log = BOOTSTRAP_CHANGELOG % locals()
        self._commit(root, changeset.date, author, patchname, log,
                     entries=[subdir, '%s/...' % subdir])

    def _initializeWorkingDir(self, root, source_repository, source_module,
                              subdir):
        """
        Execute ``cdv init``.
        """

        from os import getenv
        from os.path import join

        init = ExternalCommand(cwd=root, command=[self.repository.CDV_CMD, "init"])
        init.execute()

        if init.exit_status:
            raise TargetInitializationFailure(
                "%s returned status %s" % (str(init), init.exit_status))

        cmd = [self.repository.CDV_CMD, "set", "user"]
        user = getenv('CDV_USER') or getenv('LOGNAME')
        ExternalCommand(cwd=root, command=cmd).execute(user)

        SyncronizableTargetWorkingDir._initializeWorkingDir(self, root,
                                                            source_repository,
                                                            source_module,
                                                            subdir)
