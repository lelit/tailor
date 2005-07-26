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

BAZAAR_CMD = 'bzr'
    
class BzrWorkingDir(SyncronizableTargetWorkingDir):

    ## SyncronizableTargetWorkingDir

    def _addEntries(self, root, entries):
        """
        Add a sequence of entries.
        """

        cmd = [BAZAAR_CMD, "add"]
        ExternalCommand(cwd=root, command=cmd).execute(entries)

    def _commit(self,root, date, author, remark, changelog=None, entries=None):
        """
        Commit the changeset.
        """

        logmessage = remark
        if changelog:
            logmessage += '\n%s' % changelog
        logmessage += '\n\nOriginal author: %s\nDate: %s\n' % (author, date)

        cmd = [BAZAAR_CMD, "commit", "-m", logmessage]
        if not entries:
            entries = ['.']

        ExternalCommand(cwd=root, command=cmd).execute(entries)
        
    def _removeEntries(self, root, entries):
        """
        Remove a sequence of entries.
        """

        cmd = [BAZAAR_CMD, "remove"]
        ExternalCommand(cwd=root, command=cmd).execute(entries)

    def _renameEntry(self, root, oldentry, newentry):
        """
        Rename an entry.
        """

        cmd = [BAZAAR_CMD, "rename"]
        ExternalCommand(cwd=root, command=cmd).execute(old, new)

    def initializeNewWorkingDir(self, root, repository, module, subdir,
                                changeset, initial):
        """
        Initialize a new working directory, just extracted from
        some other VC system, importing everything's there.
        """

        from target import AUTHOR, HOST, BOOTSTRAP_PATCHNAME, \
             BOOTSTRAP_CHANGELOG

        self._initializeWorkingDir(root, repository, module, subdir)
        revision = changeset.revision
        if initial:
            author = changeset.author
            remark = changeset.log
            log = None
        else:
            author = "%s@%s" % (AUTHOR, HOST)
            remark = BOOTSTRAP_PATCHNAME % module
            log = BOOTSTRAP_CHANGELOG % locals()
        self._commit(root, changeset.date, author, remark, log,
                     entries=[subdir, '%s/...' % subdir])

    def _initializeWorkingDir(self, root, repository, module, subdir):
        """
        Execute ``bzr init``.
        """

        from os import getenv
        from os.path import join
        from dualwd import IGNORED_METADIRS

        cmd = [BAZAAR_CMD, "init"]
        init = ExternalCommand(cwd=root, command=cmd)
        init.execute()

        if init.exit_status:
            raise TargetInitializationFailure(
                "%s returned status %s" % (str(init), init.exit_status))

        # Create the .bzrignore file, that contains a glob per line,
        # with all known VCs metadirs to be skipped.
        ignore = open(join(root, '.hgignore'), 'w')
        ignore.write('\n'.join(['(^|/)%s($|/)' % md
                                for md in IGNORED_METADIRS]))
        ignore.write('\ntailor.log\ntailor.info\n')
        ignore.close()

        SyncronizableTargetWorkingDir._initializeWorkingDir(self, root,
                                                            repository, module,
                                                            subdir)
