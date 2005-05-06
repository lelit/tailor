#! /usr/bin/python
# -*- mode: python; coding: utf-8 -*-
# :Progetto: vcpx -- Codeville details
# :Creato:   gio 05 mag 2005 23:47:45 CEST
# :Autore:   Lele Gaifax <lele@nautilus.homeip.net>
# 

"""
This module implements the backends for Codeville.
"""

__docformat__ = 'reStructuredText'

from shwrap import SystemCommand, shrepr
from target import SyncronizableTargetWorkingDir, TargetInitializationFailure

class CdvAdd(SystemCommand):
    COMMAND = "cdv add %(entry)s"

class CdvCommit(SystemCommand):
    COMMAND = "cdv -u %(user)s commit -m %(comment)s %(entries)s"

    def __call__(self, output=None, dry_run=False, **kwargs):
        logmessage = kwargs.get('logmessage')
        kwargs['comment'] = shrepr(logmessage)
        author = kwargs.get('author')
        kwargs['user'] = shrepr(author)
        
        return SystemCommand.__call__(self, output=output,
                                      dry_run=dry_run, **kwargs)
    

class CdvWorkingDir(SyncronizableTargetWorkingDir):

    ## SyncronizableTargetWorkingDir

    def _addEntries(self, root, entries):
        """
        Add a sequence of entries.
        """

        c = SystemCommand(working_dir=root, command="cdv add %(entries)s")
        c(entries=' '.join([shrepr(e.name) for e in entries]))

    def _commit(self,root, date, author, remark, changelog=None, entries=None):
        """
        Commit the changeset.
        """

        c = CdvCommit(working_dir=root)
        
        logmessage = "%s\nOriginal date: %s" % (remark, date)
        if changelog:
            logmessage = logmessage + '\n\n' + changelog
            
        if entries:
            entries = ' '.join([shrepr(e) for e in entries])
        else:
            entries = '.'
            
        c(author=author, logmessage=logmessage, entries=entries)
        
    def _removeEntries(self, root, entries):
        """
        Remove a sequence of entries.
        """

        c = SystemCommand(working_dir=root, command="cdv remove %(entries)s")
        c(entries=' '.join([shrepr(e.name) for e in entries]))

    def _renameEntry(self, root, oldentry, newentry):
        """
        Rename an entry.
        """

        c = SystemCommand(working_dir=root,
                          command="cdv rename %(old)s %(new)s")
        c(old=shrepr(oldentry), new=repr(newentry))

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

    def _initializeWorkingDir(self, root, repository, module, subdir, addentry=None):
        """
        Execute `cdv init`.
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
                                                            subdir, CdvAdd)
