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
    COMMAND = "darcs record --standard-verbosity --all --look-for-adds --logfile=%(logfile)"

    def __call__(self, output=None, dry_run=False, patchname=None, **kwargs):
        logfile = kwargs.get('logfile')
        if not logfile:
            from tempfile import NamedTemporaryFile

            log = NamedTemporaryFile()
            print >>log, patchname

            logmessage = kwargs.get('logmessage')
            if logmessage:
                print >>log, logmessage

            kwargs['logfile'] = log.name
            
        return SystemCommand.__call__(self, output=output,
                                      dry_run=dry_run, **kwargs)

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
        drec(patchname=patchname, log=log)
