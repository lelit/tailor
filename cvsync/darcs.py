#! /usr/bin/python
# -*- mode: python; coding: utf-8 -*-
# :Progetto: Bice -- Sync SVN->Darcs
# :Sorgente: $HeadURL$
# :Creato:   mer 02 giu 2004 01:11:48 CEST
# :Autore:   Lele Gaifax <lele@nautilus.homeip.net>
# :Modifica: $LastChangedDate$
# :Fatta da: $LastChangedBy$
# 

"""A little layer above the Darcs world.
"""

__docformat__ = 'reStructuredText'

from shwrap import SystemCommand
from target import SyncronizableTargetWorkingDir

AUTHOR = "tailor@localhost"


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
                                      dry_run=dry_run, author=AUTHOR,
                                      **kwargs)


class DarcsMv(SystemCommand):
    COMMAND = "darcs mv %(old)s %(new)s"


class DarcsRemove(SystemCommand):
    COMMAND = "darcs remove %(entry)s"


class DarcsAdd(SystemCommand):
    COMMAND = "darcs add %(entry)s"


class DarcsWorkingDir(SyncronizableTargetWorkingDir):
    """Represent a Darcs working directory."""

    def initialize(self):
        """Execute `darcs initialize`."""

        di = DarcsInitialize(working_dir=self.root)
        di(output=True)
        
    def commit(self, remark, changelog):
        """Record current changes in a darcs patch."""

        drec = DarcsRecord(working_dir=self.root)
        drec(output=True, patchname=remark, logmessage=changelog)

    def rename(self, old, new):
        """Rename something named old to new."""
        
        dvm = DarcsMv(working_dir=self.root)
        dvm(old=old, new=new)

    def remove(self, entry):
        """Remove an entry from the darcs repos."""
        
        drm = DarcsRemove(working_dir=self.root)
        drm(entry=entry)

    def add(self, entry):
        """Add a new entry to the darcs repos."""
        
        dadd = DarcsAdd(working_dir=self.root)
        dadd(entry=entry)
        
    def update(self, revision):
        """No op for darcs."""

        pass
    
