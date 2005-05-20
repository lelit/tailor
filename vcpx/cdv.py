#! /usr/bin/python
# -*- mode: python; coding: utf-8 -*-
# :Progetto: vcpx -- Codeville details
# :Creato:   gio 05 mag 2005 23:47:45 CEST
# :Autore:   Lele Gaifax <lele@nautilus.homeip.net>
# :Licenza:  GNU General Public License
# 

"""
This module implements the backends for Codeville.
"""

__docformat__ = 'reStructuredText'

from shwrap import SystemCommand, shrepr
from target import SyncronizableTargetWorkingDir, TargetInitializationFailure

class CdvCommit(SystemCommand):
    COMMAND = "cdv -u %(user)s commit -m %(comment)s -D '%(time)s' %(entries)s"

    def __call__(self, output=None, dry_run=False, **kwargs):
        logmessage = kwargs.get('logmessage')
        kwargs['comment'] = shrepr(logmessage)
        author = kwargs.get('author')
        kwargs['user'] = shrepr(author)
        kwargs['time'] = kwargs.get('date').strftime('%Y/%m/%d %H:%M:%S UTC')
        
        return SystemCommand.__call__(self, output=output,
                                      dry_run=dry_run, **kwargs)
    

class CdvWorkingDir(SyncronizableTargetWorkingDir):

    ## SyncronizableTargetWorkingDir

    def _addPathnames(self, root, names):
        """
        Add some new filesystem objects.
        """

        c = SystemCommand(working_dir=root, command="cdv add %(names)s")
        c(names=' '.join([shrepr(n) for n in names]))

    def _commit(self,root, date, author, remark, changelog=None, entries=None):
        """
        Commit the changeset.
        """

        c = CdvCommit(working_dir=root)
        
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

        c = SystemCommand(working_dir=root, command="cdv remove %(names)s")
        c(names=' '.join([shrepr(n) for n in names]))

    def _renamePathname(self, root, oldname, newname):
        """
        Rename a filesystem object.
        """

        c = SystemCommand(working_dir=root,
                          command="cdv rename %(old)s %(new)s")
        c(old=shrepr(oldname), new=repr(newname))

    def initializeNewWorkingDir(self, root, repository, module, subdir, revision):
        """
        Initialize a new working directory, just extracted from
        some other VC system, importing everything's there.
        """

        from datetime import datetime
        from target import AUTHOR, HOST, BOOTSTRAP_PATCHNAME, \
             BOOTSTRAP_CHANGELOG
        
        now = datetime.now()
        self._initializeWorkingDir(root, repository, module, subdir)
        self._commit(root, now, '%s@%s' % (AUTHOR, HOST),
                     BOOTSTRAP_PATCHNAME % module,
                     BOOTSTRAP_CHANGELOG % locals(),
                     entries=[subdir, '%s/...' % subdir])

    def _initializeWorkingDir(self, root, repository, module, subdir):
        """
        Execute ``cdv init``.
        """

        from os import getenv
        from os.path import join
        
        c = SystemCommand(working_dir=root, command="cdv init")
        c(output=True)

        if c.exit_status:
            raise TargetInitializationFailure(
                "'cdv init' returned status %s" % c.exit_status)

        c = SystemCommand(working_dir=root, command="cdv set user %(user)s")
        c(user=getenv('CDV_USER') or getenv('LOGNAME'))
        
        SyncronizableTargetWorkingDir._initializeWorkingDir(self, root,
                                                            repository, module,
                                                            subdir)
