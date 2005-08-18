# -*- mode: python; coding: utf-8 -*-
# :Progetto: vcpx -- bazaar-ng support
# :Creato:   ven 20 mag 2005 08:15:02 CEST
# :Autore:   Johan Rydberg <jrydberg@gnu.org>
# :Licenza:  GNU General Public License
#

"""
This module implements the backends for Bazaar-NG.
"""

__docformat__ = 'reStructuredText'

from target import SyncronizableTargetWorkingDir, TargetInitializationFailure
from source import ChangesetApplicationFailure
from shwrap import ExternalCommand, ReopenableNamedTemporaryFile

class BzrWorkingDir(SyncronizableTargetWorkingDir):

    ## SyncronizableTargetWorkingDir

    def _addPathnames(self, names):
        """
        Add some new filesystem objects.
        """

        cmd = [self.repository.BZR_CMD, "add"]
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
        logmessage.append('')
        logmessage.append('Original author: %s' % author.encode(encoding))
        logmessage.append('Date: %s' % date)
        logmessage.append('')

        rontf = ReopenableNamedTemporaryFile('bzr', 'tailor')
        log = open(rontf.name, "w")
        log.write('\n'.join(logmessage))
        log.close()

        cmd = [self.repository.BZR_CMD, "commit", "--unchanged",
               "--file", rontf.name]
        if not entries:
            entries = ['.']

        c = ExternalCommand(cwd=self.basedir, command=cmd)
        c.execute(entries)

        if c.exit_status:
            raise ChangesetApplicationFailure("%s returned status %d" %
                                              (str(c), c.exit_status))

    def _removePathnames(self, names):
        """
        Remove some filesystem objects.
        """

        cmd = [self.repository.BZR_CMD, "remove"]
        ExternalCommand(cwd=self.basedir, command=cmd).execute(names)

    def _renamePathname(self, oldname, newname):
        """
        Rename a filesystem object to some other name/location.
        """

        cmd = [self.repository.BZR_CMD, "rename"]
        ExternalCommand(cwd=self.basedir, command=cmd).execute(oldname, newname)

    def _prepareTargetRepository(self):
        """
        Create the base directory if it doesn't exist, and the
        repository as well in the new working directory, executing
        ``bzr init``.
        """

        from os.path import join, exists
        from os import makedirs

        if not exists(self.basedir):
            makedirs(self.basedir)

        if not exists(join(self.basedir, self.repository.METADIR)):
            cmd = [self.repository.BZR_CMD, "init"]
            init = ExternalCommand(cwd=self.basedir, command=cmd)
            init.execute()

            if init.exit_status:
                raise TargetInitializationFailure(
                    "%s returned status %s" % (str(init), init.exit_status))

    def _prepareWorkingDirectory(self, source_repo):
        """
        Create the .bzrignore.
        """

        from os.path import join
        from dualwd import IGNORED_METADIRS

        # Create the .bzrignore file, that contains a glob per line,
        # with all known VCs metadirs to be skipped.
        ignore = open(join(self.basedir, '.bzrignore'), 'w')
        ignore.write('\n'.join(['(^|/)%s($|/)' % md
                                for md in IGNORED_METADIRS]))
        ignore.write('\n')
        if self.logfile.startswith(self.basedir):
            ignore.write('^')
            ignore.write(self.logfile[len(self.basedir)+1:])
            ignore.write('$\n')
        if self.state_file.filename.startswith(self.basedir):
            ignore.write('^')
            ignore.write(self.state_file.filename[len(self.basedir)+1:])
            ignore.write('\n')
        ignore.close()
