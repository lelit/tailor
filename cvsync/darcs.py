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

class DarcsInitialize(SystemCommand):
    COMMAND = "darcs initialize"

class DarcsRecord(SystemCommand):
    COMMAND = "darcs record --standard-verbosity --all --look-for-adds --logfile=%(logfile)s"

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
                                      dry_run=dry_run, **kwargs)

class DarcsMv(SystemCommand):
    COMMAND = "darcs mv %(old)s %(new)s"

class DarcsRemove(SystemCommand):
    COMMAND = "darcs remove %(entry)s"

class DarcsAdd(SystemCommand):
    COMMAND = "darcs add %(entry)s"
    
class DarcsWorkingDir(object):
    """Represent a Darcs working directory."""

    __slots__ = ('root',)

    def __init__(self, root):
        """Initialize a DarcsWorkingDir instance."""
        
        self.root = root
        """The directory in question."""

    def initialize(self):
        """Execute `darcs initialize`."""

        di = DarcsInitialize(working_dir=self.root)
        di()
        
    def record(self, patchname, logmessage=None):
        """Record current changes in a darcs patch."""

        drec = DarcsRecord(working_dir=self.root)
        drec(patchname=patchname, logmessage=logmessage)

    def rename(self, old, new):
        """Rename something named old to new."""
        
        # strip initial '/'
        old = old[1:]
        new = new[1:]
        
        dvm = DarcsMv(working_dir=self.root)
        dvm(old=old, new=new)

    def remove(self, entry):
        """Remove an entry from the darcs repos."""
        
        # strip initial '/'
        entry = entry[1:]

        drm = DarcsRemove(working_dir=self.root)
        drm(entry=entry)

    def add(self, entry):
        """Add a new entry to the darcs repos."""
        
        # strip initial '/'
        entry = entry[1:]

        dadd = DarcsAdd(working_dir=self.root)
        dadd(entry=entry)
        
