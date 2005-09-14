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
from mercurial import ui, hg, commands

class HglibWorkingDir(SyncronizableTargetWorkingDir):
    def _addPathnames(self, names):
        from os.path import join, isdir

        notdirs = [n for n in names if not isdir(join(self.basedir, n))]
        if notdirs:
            self._hg.add(notdirs)

    def _commit(self, date, author, patchname, changelog=None, names=None):
        from time import mktime

        encoding = self.repository.encoding

        logmessage = []
        if patchname:
            logmessage.append(patchname.encode(encoding))
        if changelog:
            logmessage.append(changelog.encode(encoding))
        self._hg.commit(names and [n.encode(encoding) for n in names] or [],
                        '\n'.join(logmessage),
                        author.encode(encoding),
                        "%d 0" % mktime(date.timetuple()))

    def _removePathnames(self, names):
        """Remove a sequence of entries"""

        from os.path import join, isdir

        notdirs = [n for n in names if not isdir(join(self.basedir, n))]
        if notdirs:
            self._hg.remove(notdirs)

    def _renamePathname(self, oldname, newname):
        """Rename an entry"""

        from os.path import join, isdir
        from os import walk
        from dualwd import IGNORED_METADIRS

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
                    self._hg.copy(join(oldname, prefix, f),
                                  join(newname, prefix, f))
        else:
            self._hg.copy(oldname, newname)

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
