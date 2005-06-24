#! /usr/bin/python
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

from shwrap import SystemCommand, shrepr, ReopenableNamedTemporaryFile
from target import SyncronizableTargetWorkingDir, TargetInitializationFailure

class HgCommit(SystemCommand):
    COMMAND = "hg commit -u %(user)s -l %(logfile)s -d '%(time)s UTC'"

    def __call__(self, output=None, dry_run=False, **kwargs):
        from time import mktime
        
        logmessage = kwargs.get('logmessage')
        rontf = ReopenableNamedTemporaryFile('hg', 'tailor')
        log = open(rontf.name, "w")
        log.write(logmessage)
        log.close()            
        kwargs['logfile'] = rontf.name
        author = kwargs.get('author')
        kwargs['user'] = shrepr(author)
        kwargs['time'] = mktime(kwargs.get('date').timetuple())
        
        return SystemCommand.__call__(self, output=output,
                                      dry_run=dry_run, **kwargs)
    

class HgWorkingDir(SyncronizableTargetWorkingDir):

    ## SyncronizableTargetWorkingDir

    def _addPathnames(self, root, names):
        """
        Add some new filesystem objects.
        """

        c = SystemCommand(working_dir=root, command="hg add %(names)s")
        c(names=' '.join([shrepr(n) for n in names]))

    def _commit(self,root, date, author, remark, changelog=None, entries=None):
        """
        Commit the changeset.
        """

        c = HgCommit(working_dir=root)
        
        if changelog:
            logmessage = remark + '\n\n' + changelog
        else:
            logmessage = remark
            
        if entries:
            entries = ' '.join([shrepr(e) for e in entries])
        else:
            entries = '.'
            
        c(author=author, logmessage=logmessage, date=date, entries=entries)
        
    def _removePathnames(self, root, names):
        """
        Remove some filesystem object.
        """

        c = SystemCommand(working_dir=root, command="hg remove %(names)s")
        c(names=' '.join([shrepr(n) for n in names]))

    def _renamePathname(self, root, oldname, newname):
        """
        Rename a filesystem object.
        """

        c = SystemCommand(working_dir=root,
                          command="hg copy %(old)s %(new)s")
        c(old=shrepr(oldname), new=repr(newname))
        
        c = SystemCommand(working_dir=root,
                          command="hg remove %(old)s")
        c(old=shrepr(oldname))

    def _initializeWorkingDir(self, root, repository, module, subdir):
        """
        Execute ``hg init``.
        """

        from os import getenv
        from os.path import join
        
        c = SystemCommand(working_dir=root, command="hg init")
        c(output=True)

        if c.exit_status:
            raise TargetInitializationFailure(
                "'hg init' returned status %s" % c.exit_status)

        c = SystemCommand(working_dir=root, command="hg addremove")
        c()
