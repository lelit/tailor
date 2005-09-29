# -*- mode: python; coding: utf-8 -*-
# :Progetto: vcpx -- Mercurial stuff
# :Creato:   ven 24 giu 2005 20:42:46 CEST
# :Autore:   Lele Gaifax <lele@nautilus.homeip.net>
# :Licenza:  GNU General Public License
#

"""
This module implements the backends for Mercurial.
"""

__docformat__ = 'reStructuredText'

from shwrap import ExternalCommand, ReopenableNamedTemporaryFile, PIPE
from target import SyncronizableTargetWorkingDir, TargetInitializationFailure, \
     ChangesetReplayFailure
from source import ChangesetApplicationFailure

class HgWorkingDir(SyncronizableTargetWorkingDir):

    ## SyncronizableTargetWorkingDir

    def _addPathnames(self, names):
        """
        Add some new filesystem objects.
        """

        from os.path import join, isdir

        # Currently hg does not handle directories at all, so filter
        # them out.

        notdirs = [n for n in names if not isdir(join(self.basedir, n))]
        if notdirs:
            cmd = self.repository.command("add")
            ExternalCommand(cwd=self.basedir, command=cmd).execute(notdirs)

    def _commit(self, date, author, patchname, changelog=None, entries=None):
        """
        Commit the changeset.
        """

        from time import mktime
        from locale import getpreferredencoding

        encoding = ExternalCommand.FORCE_ENCODING or getpreferredencoding()

        logmessage = []
        if patchname:
            logmessage.append(patchname.encode(encoding))
        if changelog:
            logmessage.append(changelog.encode(encoding))

        cmd = self.repository.command("commit", "-u", author.encode(encoding),
                                      "-l", "%(logfile)s",
                                      "-d", "%(time)d 0")
        c = ExternalCommand(cwd=self.basedir, command=cmd)

        rontf = ReopenableNamedTemporaryFile('hg', 'tailor')
        log = open(rontf.name, "w")
        log.write('\n'.join(logmessage) or "Empty changelog")
        log.close()

        c.execute(logfile=rontf.name, time=mktime(date.timetuple()))

        if c.exit_status:
            raise ChangesetApplicationFailure("%s returned status %d" %
                                              (str(c), c.exit_status))

    def _removePathnames(self, names):
        """
        Remove some filesystem object.
        """

        from os.path import join, isdir

        # Currently hg does not handle directories at all, so filter
        # them out.

        notdirs = [n for n in names if not isdir(join(self.basedir, n))]
        if notdirs:
            cmd = self.repository.command("remove")
            ExternalCommand(cwd=self.basedir, command=cmd).execute(notdirs)

    def _renamePathname(self, oldname, newname):
        """
        Rename a filesystem object.
        """

        from os.path import join, isdir

        cmd = self.repository.command("rename", "--after")
        copy = ExternalCommand(cwd=self.basedir, command=cmd)
        if isdir(join(self.basedir, newname)):
            # Given lack of support for directories in current HG,
            # loop over all files presented by "hg manifest" under the
            # old directory and do a copy on them.
            cmd = self.repository.command("manifest")
            manifest = ExternalCommand(cwd=self.basedir, command=cmd)
            output = manifest.execute(stdout=PIPE)[0]
            for row in output:
                sha, mode, oldpath = row[:-1].split(' ')
                if oldpath.startswith(oldname):
                    tail = oldpath[len(oldname)+2:]
                    copy.execute(oldpath, join(newname, tail))
                    if copy.exit_status:
                        raise ChangesetReplayFailure("Could not rename %r "
                                                     "into %r: maybe using a "
                                                     "pre 0.7 mercurial?")
        else:
            copy.execute(oldname, newname)
            if copy.exit_status:
                raise ChangesetReplayFailure("Could not rename %r "
                                             "into %r: maybe using a "
                                             "pre 0.7 mercurial?")

    def _prepareTargetRepository(self):
        """
        Execute ``hg init``.
        """

        from os.path import join, exists

        if not exists(join(self.basedir, self.repository.METADIR)):
            init = ExternalCommand(cwd=self.basedir,
                                   command=self.repository.command("init"))
            init.execute()

            if init.exit_status:
                raise TargetInitializationFailure(
                    "%s returned status %s" % (str(init), init.exit_status))

    def _prepareWorkingDirectory(self, source_repo):
        """
        Create the .hgignore.
        """

        from os.path import join
        from re import escape
        from dualwd import IGNORED_METADIRS

        # Create the .hgignore file, that contains a regexp per line
        # with all known VCs metadirs to be skipped.
        ignore = open(join(self.basedir, '.hgignore'), 'w')
        ignore.write('\n'.join(['(^|/)%s($|/)' % escape(md)
                                for md in IGNORED_METADIRS]))
        ignore.write('\n')
        if self.logfile.startswith(self.basedir):
            ignore.write('^')
            ignore.write(self.logfile[len(self.basedir)+1:])
            ignore.write('$\n')
        if self.state_file.filename.startswith(self.basedir):
            sfrelname = self.state_file.filename[len(self.basedir)+1:]
            ignore.write('^')
            ignore.write(sfrelname)
            ignore.write('$\n')
            ignore.write('^')
            ignore.write(sfrelname+'.journal')
            ignore.write('$\n')
        ignore.close()

    def _initializeWorkingDir(self):
        """
        Use ``hg addremove`` to import initial version of the tree.
        """

        ExternalCommand(cwd=self.basedir,
                        command=self.repository.command("addremove")).execute()
