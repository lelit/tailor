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

from shwrap import ExternalCommand, PIPE, ReopenableNamedTemporaryFile, STDOUT
from source import UpdatableSourceWorkingDir, \
     ChangesetApplicationFailure, GetUpstreamChangesetsFailure
from target import SyncronizableTargetWorkingDir, TargetInitializationFailure
from sys import stderr
from os.path import exists, join, isdir
from os import renames, access, F_OK

class MonotoneWorkingDir(SyncronizableTargetWorkingDir):

    ## SyncronizableTargetWorkingDir

    def _addPathnames(self, names):
        """
        Add some new filesystem objects, skipping directories (directory addition is implicit in monotone)
        """
        fnames=[]
        for fn in names:
            if isdir(join(self.basedir, fn)):
                self.log_info("ignoring addition of directory '%s' (%s)" % (fn, join(self.basedir, fn)) );
            else:
                fnames.append(fn)

        cmd = [self.repository.MONOTONE_CMD, "add"]
        add = ExternalCommand(cwd=self.basedir, command=cmd)
        add.execute(fnames)
        if add.exit_status:
            raise ChangesetApplicationFailure("%s returned status %s" % (str(add),add.exit_status))

    def _addSubtree(self, subdir):
        """
        Add a whole subtree
        """
        cmd = [self.repository.MONOTONE_CMD, "add"]
        add = ExternalCommand(cwd=self.basedir, command=cmd)
        add.execute(subdir)
        if add.exit_status:
            raise ChangesetApplicationFailure("%s returned status %s" % (str(add),add.exit_status))

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
            logmessage.append('')
            logmessage.append(changelog.encode(encoding))
        logmessage.append('')

        rontf = ReopenableNamedTemporaryFile('mtn', 'tailor')
        log = open(rontf.name, "w")
        log.write('\n'.join(logmessage))
        log.close()

        cmd = [self.repository.MONOTONE_CMD, "commit", "--author", author,
               "--date", date.isoformat(),
               "--message-file", rontf.name]
        commit = ExternalCommand(cwd=self.basedir, command=cmd)

        if not entries:
            entries = ['.']

        output, error = commit.execute(entries, stdout=PIPE, stderr=PIPE)

        # monotone complaints if there are no changes from the last commit.
        # we ignore those errors ...
        if commit.exit_status:
            text = error.read()
            if text.find("monotone: misuse: no changes to commit") == -1:
                self.log_error(text)
                raise ChangesetApplicationFailure(
                    "%s returned status %s" % (str(commit),commit.exit_status))
            else:
                stderr.write("No changes to commit - changeset ignored\n")

    def _removePathnames(self, names):
        """
        Remove some filesystem object. 
        """

        # Monotone currently doesn't allow removing a directory,
        # so we must remove every item separately and intercept monotone directory errore messages.
        # We can't just filter the directories, because the wc doesn't contain them anymore ...
        cmd = [self.repository.MONOTONE_CMD, "drop"]
        drop = ExternalCommand(cwd=self.basedir, command=cmd)
        for fn in names:
            dum, error = drop.execute(fn, stderr=PIPE)
            if drop.exit_status:
                if not error.read().find("drop <directory>"):
                    log_error(error.read())
                    raise ChangesetApplicationFailure("%s returned status %s" % (str(drop),drop.exit_status))

    def _renamePathname(self, oldname, newname):
        """
        Rename a filesystem object.
        """
        # this function is called *after* the file/dir has changed name,
        # and monotone doesn't like it.
        # we put names back to make it happy ...
        if access(join(self.basedir, newname), F_OK):
            if access(join(self.basedir, oldname), F_OK):
                raise ChangesetApplicationFailure("Can't rename %s to %s. Both names already exist" % (oldname, newname) )
            renames(join(self.basedir, newname), join(self.basedir, oldname))
            self.log_info("preparing to rename %s->%s" % (oldname, newname))
        
        cmd = [self.repository.MONOTONE_CMD, "rename"]
        rename = ExternalCommand(cwd=self.basedir, command=cmd)
        o1, o2 =rename.execute(oldname, newname, stderr=PIPE)
        stderr.write(o2.read())
        
        # redo the rename ...
        renames(join(self.basedir, oldname), join(self.basedir, newname))
        if rename.exit_status:
            raise ChangesetApplicationFailure("%s returned status %s" % (str(rename),rename.exit_status))

    def _initializeWorkingDir(self):
        """
        Setup the monotone working copy

        The user must setup a monotone working directory himself. Then
        we simply use 'monotone commit', without having to specify a database
        file or branch. Monotone looks up the database and branch in it's MT
        directory.
        """

        if not exists(join(self.basedir, 'MT')):
            raise TargetInitializationFailure("Please setup '%s' as a monotone working directory" % self.basedir)

        self._addSubtree([self.repository.subdir])
