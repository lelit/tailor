#! /usr/bin/python
# -*- mode: python; coding: utf-8 -*-
# :Progetto: vcpx -- Darcs details
# :Creato:   ven 18 giu 2004 14:45:28 CEST
# :Autore:   Lele Gaifax <lele@nautilus.homeip.net>
# 

__docformat__ = 'reStructuredText'

from cvsync.shwrap import SystemCommand
from source import UpdatableSourceWorkingDir
from target import SyncronizableTargetWorkingDir


class DarcsInitialize(SystemCommand):
    COMMAND = "darcs initialize"


class DarcsRecord(SystemCommand):
    COMMAND = "darcs record -v --all --look-for-adds --author=%(author)s --logfile=%(logfile)s"

    def __call__(self, output=None, dry_run=False, patchname=None, **kwargs):
        logfile = kwargs.get('logfile')
        if not logfile:
            from tempfile import NamedTemporaryFile

            log = NamedTemporaryFile(bufsize=0)
            print >>log, patchname

            logmessage = kwargs.get('logmessage')
            if logmessage:
                print >>log, logmessage
            
            kwargs['logfile'] = log.name
            
        return SystemCommand.__call__(self, output=output,
                                      dry_run=dry_run, 
                                      **kwargs)


class DarcsMv(SystemCommand):
    COMMAND = "darcs mv %(old)s %(new)s"


class DarcsRemove(SystemCommand):
    COMMAND = "darcs remove %(entry)s"


class DarcsAdd(SystemCommand):
    COMMAND = "darcs add --non-recursive %(entry)s"


class DarcsPull(SystemCommand):
    COMMAND = "darcs pull --patches='%(patch)s'"


class DarcsWorkingDir(UpdatableSourceWorkingDir,SyncronizableTargetWorkingDir):

    ## UpdatableSourceWorkingDir
    
    def _getUpstreamChangesets(self, root):
        """
        Do the actual work of fetching the upstream changeset.
        
        This method must be overridden by subclasses.
        """

        # XXX
        
    def _applyChangeset(self, root, changeset):
        """
        Do the actual work of applying the changeset to the working copy.
        """

        dpull = DarcsPull(working_dir=root)
        dpull(patch=changeset.revision)

    ## SyncronizableTargetWorkingDir

    def _addEntry(self, root, entry):
        """
        Add a new entry, maybe registering the directory as well.
        """

        c = DarcsAdd(working_dir=root)
        c(entry=entry)

    def _commit(self, root, author, remark, changelog=None, entries=None):
        """
        Commit the changeset.
        """

        c = DarcsRecord(working_dir=root)
        c(patchname=remark, logmessage=changelog, author=author)
        
    def _removeEntry(self, root, entry):
        """
        Remove an entry.
        """

        c = DarcsRemove(working_dir=root)
        c(entry=entry)

    def _renameEntry(self, root, oldentry, newentry):
        """
        Rename an entry.
        """

        c = DarcsMv(working_dir=root)
        c(old=oldentry, new=newentry)

