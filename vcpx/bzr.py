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
from shwrap import ExternalCommand

class BzrWorkingDir(SyncronizableTargetWorkingDir):

    ## SyncronizableTargetWorkingDir

    def _addEntries(self, entries):
        """
        Add a sequence of entries.
        """

        cmd = [self.repository.BZR_CMD, "add"]
        ExternalCommand(cwd=self.basedir, command=cmd).execute(entries)

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

        cmd = [self.repository.BZR_CMD, "commit", "-m", '\n'.join(logmessage)]
        if not entries:
            entries = ['.']

        ExternalCommand(cwd=self.basedir, command=cmd).execute(entries)

    def _removeEntries(self, entries):
        """
        Remove a sequence of entries.
        """

        cmd = [self.repository.BZR_CMD, "remove"]
        ExternalCommand(cwd=self.basedir, command=cmd).execute(entries)

    def _renameEntry(self, oldentry, newentry):
        """
        Rename an entry.
        """

        cmd = [self.repository.BZR_CMD, "rename"]
        ExternalCommand(cwd=self.basedir, command=cmd).execute(old, new)

    def initializeNewWorkingDir(self, source_repo, changeset, initial):
        """
        Initialize a new working directory, just extracted from
        some other VC system, importing everything's there.
        """

        from target import AUTHOR, HOST, BOOTSTRAP_PATCHNAME, \
             BOOTSTRAP_CHANGELOG

        self._initializeWorkingDir()
        revision = changeset.revision
        source_repository = source_repo.repository
        source_module = source_repo.module
        if initial:
            author = changeset.author
            patchname = changeset.log
            log = None
        else:
            author = "%s@%s" % (AUTHOR, HOST)
            patchname = BOOTSTRAP_PATCHNAME % source_module
            log = BOOTSTRAP_CHANGELOG % locals()
        self._commit(changeset.date, author, patchname, log,
                     entries=['%s/...' % self.basedir])

    def _initializeWorkingDir(self):
        """
        Execute ``bzr init``.
        """

        from os import getenv
        from os.path import join
        from dualwd import IGNORED_METADIRS

        cmd = [self.repository.BZR_CMD, "init"]
        init = ExternalCommand(cwd=self.basedir, command=cmd)
        init.execute()

        if init.exit_status:
            raise TargetInitializationFailure(
                "%s returned status %s" % (str(init), init.exit_status))

        # Create the .bzrignore file, that contains a glob per line,
        # with all known VCs metadirs to be skipped.
        ignore = open(join(self.basedir, '.hgignore'), 'w')
        ignore.write('\n'.join(['(^|/)%s($|/)' % md
                                for md in IGNORED_METADIRS]))
        ignore.write('\ntailor.log\ntailor.info\n')
        ignore.close()

        SyncronizableTargetWorkingDir._initializeWorkingDir(self)
