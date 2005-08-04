# -*- mode: python; coding: utf-8 -*-
# :Progetto: vcpx -- Mercurial stuff
# :Creato:   ven 24 giu 2005 20:42:46 CEST
# :Autore:   Lele Gaifax <lele@nautilus.homeip.net>
# :Licenza:  GNU General Public License
# 
# Modified 2005 by Walter Landry for ArX

"""
This module implements the backends for ArX.
"""

__docformat__ = 'reStructuredText'

from shwrap import ExternalCommand, PIPE, ReopenableNamedTemporaryFile
from target import SyncronizableTargetWorkingDir, TargetInitializationFailure

ARX_CMD = "arx"

class ArxWorkingDir(SyncronizableTargetWorkingDir):

    ## SyncronizableTargetWorkingDir

    def _addPathnames(self, root, names):
        """
        Add some new filesystem objects.
        """

        from os.path import join, isdir

        cmd = [ARX_CMD, "add"]
        ExternalCommand(cwd=root, command=cmd).execute(names)

    def _commit(self,root, date, author, remark, changelog=None, entries=None):
        """
        Commit the changeset.
        """

        from time import mktime
        from sys import getdefaultencoding
        
        encoding = ExternalCommand.FORCE_ENCODING or getdefaultencoding()

        logmessage = ""
        if remark:
            logmessage=remark.encode(encoding)
        if changelog:
            if logmessage!="":
                logmessage+="\n\n"+changelog.encode(encoding)
            else:
                logmessage=changelog.encode(encoding)

        if logmessage=="":
            logmessage=" "

        cmd = [ARX_CMD, "commit", "-s", logmessage, "--author", author,
               "--date", date.isoformat()]
        c = ExternalCommand(cwd=root, command=cmd)
        c.execute()
        
    def _removePathnames(self, root, names):
        """
        Remove some filesystem object.
        """
        cmd = [ARX_CMD, "rm"]
        ExternalCommand(cwd=root, command=cmd).execute(names)

    def _renamePathname(self, root, oldname, newname):
        """
        Rename a filesystem object.
        """

        cmd = [ARX_CMD, "copy"]
        rename = ExternalCommand(cwd=root, command=cmd)
        rename.execute(oldname,newname)
            
    def _initializeWorkingDir(self, root, repository, module, subdir):
        """
        Setup the ArX working copy
        
        The user must setup a ArX working directory himself. Then
        we simply use 'arx commit', without having to specify an archive
        or branch. ArX looks up the archive and branch in it's _arx
        directory.
        """

        from os.path import exists, join
        from dircache import listdir
        from dualwd import IGNORED_METADIRS
        from os import walk

        if not exists(join(root, '_arx')):
            raise TargetInitializationFailure("Please setup '%s' as an ArX working directory" % root)

        self._addPathnames(root, [subdir])

        cmd = [ARX_CMD, "add"]
        add_path = ExternalCommand(cwd=root, command=cmd)

        for root, dirs, files in walk(root):
            for f in files:
                if f!="tailor.log" and f!="tailor.info":
                    add_path.execute(join(root,f))
            for metadir in IGNORED_METADIRS:
                if metadir in dirs:
                    dirs.remove(metadir)
            for d in dirs:
                add_path.execute(join(root,d))

