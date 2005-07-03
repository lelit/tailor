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

from shwrap import ExternalCommand, PIPE, ReopenableNamedTemporaryFile
from target import SyncronizableTargetWorkingDir, TargetInitializationFailure

HG_CMD = "hg"

class HgWorkingDir(SyncronizableTargetWorkingDir):

    ## SyncronizableTargetWorkingDir

    def _addPathnames(self, root, names):
        """
        Add some new filesystem objects.
        """

        cmd = [HG_CMD, "add"]
        ExternalCommand(cwd=root, command=cmd).execute(names)

    def _commit(self,root, date, author, remark, changelog=None, entries=None):
        """
        Commit the changeset.
        """

        from time import mktime

        cmd = [HG_CMD, "commit", "-u", author, "-l", "%(logfile)s",
               "-d", "%(time)s UTC"]
        c = ExternalCommand(cwd=root, command=cmd)
        
        rontf = ReopenableNamedTemporaryFile('hg', 'tailor')
        log = open(rontf.name, "w")
        log.write(remark)
        if changelog:
            log.write('\n\n')
            log.write(changelog)
        log.close()            

        c.execute(logfile=rontf.name, time=mktime(date.timetuple()))
        
    def _removePathnames(self, root, names):
        """
        Remove some filesystem object.
        """

        cmd = [HG_CMD, "remove"]
        ExternalCommand(cwd=root, command=cmd).execute(names)

    def _renamePathname(self, root, oldname, newname):
        """
        Rename a filesystem object.
        """

        cmd = [HG_CMD, "copy"]
        ExternalCommand(cwd=root, command=cmd).execute(oldname, newname)

        cmd = [HG_CMD, "remove"]
        ExternalCommand(cwd=root, command=cmd).execute(oldname)

    def _initializeWorkingDir(self, root, repository, module, subdir):
        """
        Execute ``hg init``.
        """

        from os import getenv
        from os.path import join
        from re import escape
        from dualwd import IGNORED_METADIRS
        
        init = ExternalCommand(cwd=root, command=[HG_CMD, "init"])
        init.execute()

        if init.exit_status:
            raise TargetInitializationFailure(
                "%s returned status %s" % (str(init), init.exit_status))

        # Create the .hgignore file, that contains a regexp per line
        # with all known VCs metadirs to be skipped.
        ignore = open(join(root, '.hgignore'), 'w')
        ignore.write('\n'.join(['(^|/)%s($|/)' % escape(md)
                                for md in IGNORED_METADIRS]))
        ignore.write('\n^tailor.log$\n^tailor.info$\n')
        ignore.close()

        ExternalCommand(cwd=root, command=[HG_CMD, "addremove"]).execute()
