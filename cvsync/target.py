#! /usr/bin/python
# -*- mode: python; coding: utf-8 -*-
# :Progetto: Bice -- Syncable targets
# :Sorgente: $HeadURL$
# :Creato:   ven 04 giu 2004 00:27:07 CEST
# :Autore:   Lele Gaifax <lele@nautilus.homeip.net>
# :Modifica: $LastChangedDate$
# :Fatta da: $LastChangedBy$
# 

"""
Syncronizable targets are the simplest abstract wrappers around a
working directory under both CVS and some other kind of version
control system.
"""

__docformat__ = 'reStructuredText'

class SyncronizableTargetWorkingDir(object):
    """This is an abstract working dir. Subclasses MUST override ALL
       these methods."""

    __slots__ = ('root',)

    def __init__(self, root):
        """Initialize the instance pointing to the specified root
           directory."""

        self.root = root
        """The directory in question."""
        
    def add(self, entry):
        """Add an entry."""

        raise "%s should override this method" % self.__class__

    def remove(self, entry):
        """Remove an entry."""

        raise "%s should override this method" % self.__class__

    def update(self, revision="HEAD"):
        """
        Bring this directory up to its HEAD revision in the
        repository.  Return a dictionary of changed items, grouped by
        kind of change.
        """

        raise "%s should override this method" % self.__class__

    def commit(self, remark, changelog):
        """Commit the changes."""

        raise "%s should override this method" % self.__class__

