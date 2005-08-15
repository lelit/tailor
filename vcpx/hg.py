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

from shwrap import ExternalCommand, ReopenableNamedTemporaryFile
from target import SyncronizableTargetWorkingDir, TargetInitializationFailure
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
            cmd = [self.repository.HG_CMD, "add"]
            ExternalCommand(cwd=self.basedir, command=cmd).execute(notdirs)

    def _commit(self, date, author, patchname, changelog=None, entries=None):
        """
        Commit the changeset.
        """

        from time import mktime
        from sys import getdefaultencoding

        encoding = ExternalCommand.FORCE_ENCODING or getdefaultencoding()

        logmessage = []
        if patchname:
            logmessage.append(patchname.encode(encoding))
        if changelog:
            logmessage.append('')
            logmessage.append(changelog.encode(encoding))
        logmessage.append('')

        cmd = [self.repository.HG_CMD, "commit", "-u", author,
               "-l", "%(logfile)s",
               "-d", "%(time)s UTC"]
        c = ExternalCommand(cwd=self.basedir, command=cmd)

        rontf = ReopenableNamedTemporaryFile('hg', 'tailor')
        log = open(rontf.name, "w")
        log.write('\n'.join(logmessage))
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
            cmd = [self.repository.HG_CMD, "remove"]
            ExternalCommand(cwd=self.basedir, command=cmd).execute(notdirs)

    def _renamePathname(self, oldname, newname):
        """
        Rename a filesystem object.
        """

        from os.path import join, isdir
        from os import walk
        from dualwd import IGNORED_METADIRS

        cmd = [self.repository.HG_CMD, "copy"]
        copy = ExternalCommand(cwd=self.basedir, command=cmd)
        if isdir(join(self.basedir, newname)):
            # Given lack of support for directories in current HG,
            # loop over all files under the new directory and
            # do a copy on them.
            skip = len(self.basedir)+len(newname)+2
            for dir, subdirs, files in walk(join(self.basedir, newname)):
                prefix = dir[skip:]

                for excd in IGNORED_METADIRS:
                    if excd in subdirs:
                        subdirs.remove(excd)

                for f in files:
                    copy.execute(join(oldname, prefix, f),
                                 join(newname, prefix, f))
        else:
            copy.execute(oldname, newname)

    def _prepareTargetRepository(self, source_repo):
        """
        Execute ``hg init``.
        """

        from os import makedirs
        from os.path import join, exists

        if not exists(self.basedir):
            makedirs(self.basedir)
        elif exists(join(self.basedir, self.repository.METADIR)):
            return

        init = ExternalCommand(cwd=self.basedir,
                               command=[self.repository.HG_CMD, "init"])
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
            ignore.write('^')
            ignore.write(self.state_file.filename[len(self.basedir)+1:])
            ignore.write('$\n')
        ignore.close()

    def _initializeWorkingDir(self):
        """
        Use ``hg addremove`` to import initial version of the tree.
        """

        ExternalCommand(cwd=self.basedir,
                        command=[self.repository.HG_CMD, "addremove"]).execute()
