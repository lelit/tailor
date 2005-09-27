# -*- mode: python; coding: utf-8 -*-
# :Progetto: vcpx -- Mercurial native backend
# :Creato:   dom 11 set 2005 22:58:38 CEST
# :Autore:   Lele Gaifax <lele@nautilus.homeip.net>
# :Licenza:  GNU General Public License
#

"""
This module implements the backends for Mercurial, using its native API
instead of thru the command line.
"""

__docformat__ = 'reStructuredText'

from target import SyncronizableTargetWorkingDir, TargetInitializationFailure
from mercurial import ui, hg, commands, util

class HglibWorkingDir(SyncronizableTargetWorkingDir):

    def _normalizeEntryPaths(self, entry):
        """
        Normalize the name and old_name of an entry.

        This implementation uses ``mercurial.util.normpath()``, since
        at this level hg is expecting UNIX style pathnames, with
        forward slash"/" as separator, also under insane operating systems.
        """

        entry.name = util.normpath(entry.name)
        if entry.old_name:
            entry.old_name = util.normpath(entry.old_name)

    def _addPathnames(self, names):
        from os.path import join, isdir, normpath

        notdirs = [n for n in names
                   if not isdir(join(self.basedir, normpath(n)))]
        if notdirs:
            self._hg.add(notdirs)

    def _commit(self, date, author, patchname, changelog=None, names=None):
        from time import mktime

        encoding = self.repository.encoding

        logmessage = []
        if patchname:
            logmessage.append(patchname)
        if changelog:
            logmessage.append(changelog)
        if logmessage:
            logmessage = '\n'.join(logmessage).encode(encoding)
        else:
            logmessage = "Empty changelog"
        self._hg.commit(names and [n.encode(encoding) for n in names] or [],
                        logmessage, author.encode(encoding),
                        "%d 0" % mktime(date.timetuple()))

    def _removePathnames(self, names):
        """Remove a sequence of entries"""

        from os.path import join, isdir, normpath

        notdirs = [n for n in names
                   if not isdir(join(self.basedir, normpath(n)))]
        if notdirs:
            self._hg.remove(notdirs)

    def _renamePathname(self, oldname, newname):
        """Rename an entry"""

        from os.path import join, isdir, normpath

        if isdir(join(self.basedir, normpath(newname))):
            # Given lack of support for directories in current HG,
            # loop over all files under the old directory and
            # do a copy on them.
            for src, oldpath in self._hg.dirstate.walk(oldname):
                tail = oldpath[len(oldname)+2:]
                self._hg.copy(oldpath, join(newname, tail))
                self._hg.remove([oldpath])
        else:
            self._hg.copy(oldname, newname)
            self._hg.remove(oldname)

    def _prepareTargetRepository(self):
        """
        Create the base directory if it doesn't exist, and the
        repository as well in the new working directory.
        """

        from os.path import join, exists

        project = self.repository.project
        self._ui = ui.ui(project.verbose,
                         project.config.get(self.repository.name,
                                            'debug', False),
                         project.verbose, False)

        if exists(join(self.basedir, self.repository.METADIR)):
            create = 0
        else:
            create = 1
        self._hg = hg.repository(ui=self._ui, path=self.basedir, create=create)

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
        commands.add(self._ui, self._hg, self.basedir)
