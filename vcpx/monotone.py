# -*- mode: python; coding: utf-8 -*-
# :Progetto: vcpx -- Monotone details
# :Creato:   Tue Apr 12 01:28:10 CEST 2005
# :Autore:   Markus Schiltknecht <markus@bluegap.ch>
# :Licenza:  GNU General Public License
#

"""
This module contains supporting classes for Monotone.
"""

__docformat__ = 'reStructuredText'

from shwrap import ExternalCommand, PIPE, ReopenableNamedTemporaryFile
from source import UpdatableSourceWorkingDir, \
     ChangesetApplicationFailure, GetUpstreamChangesetsFailure
from target import SyncronizableTargetWorkingDir, TargetInitializationFailure
from sys import stderr

MONOTONE_CMD = "monotone"

class MonotoneWorkingDir(SyncronizableTargetWorkingDir):

    ## SyncronizableTargetWorkingDir

    def _addPathnames(self, root, names):
        """
        Add some new filesystem objects.
        """

        cmd = [MONOTONE_CMD, "add"]
        add = ExternalCommand(cwd=root, command=cmd)
        add.execute(names)

    def _commit(self,root, date, author, remark, changelog=None, entries=None):
        """
        Commit the changeset.
        """

        rontf = ReopenableNamedTemporaryFile('mtn', 'tailor')
        log = open(rontf.name, "w")
        log.write(remark)
        log.write('\n')
        if changelog:
            log.write(changelog)
            log.write('\n')
        log.close()

        cmd = [MONOTONE_CMD, "commit", "--author", author,
               "--date", date.isoformat(),
               "--message-file", rontf.name]
        commit = ExternalCommit(cwd=root, command=cmd)
        
        if not entries:
            entries = ['.']

        output = commit.execute(entries, stdout=PIPE)

        # monotone complaints if there are no changes from the last commit.
        # we ignore those errors ...
        if commit.exit_status:
            text = output.read()
            if text.find("monotone: misuse: no changes to commit") == -1:
                stderr.write(text)
                raise TargetInitializationFailure(
                    "%s returned status %s" % (str(commit),commit.exit_status))
            else:
                stderr.write("No changes to commit - changeset ignored\n")
        
    def _removePathnames(self, root, names):
        """
        Remove some filesystem object.
        """

        cmd = [MONOTONE_CMD, "drop"]
        drop = ExternalCommand(cwd=root, command=cmd)
        drop.execute(names)

    def _renamePathname(self, root, oldname, newname):
        """
        Rename a filesystem object.
        """

        cmd = [MONOTONE_CMD, "rename"]
        rename = ExternalCommand(cwd=root, command=cmd)
        rename.execute(oldname, newname)

    def _initializeWorkingDir(self, root, repository, module, subdir):
        """
        Setup the monotone working copy
        
        The user must setup a monotone working directory himself. Then
        we simply use 'monotone commit', without having to specify a database
        file or branch. Monotone looks up the database and branch in it's MT
        directory.
        """

        from os.path import exists, join

        if not exists(join(root, 'MT')):
            raise TargetInitializationFailure("Please setup '%s' as a monotone working directory" % root)

        self._addPathnames(root, [subdir])
