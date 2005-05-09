#! /usr/bin/python
# -*- mode: python; coding: utf-8 -*-
# :Progetto: vcpx -- Monotone details
# :Creato:   Tue Apr 12 01:28:10 CEST 2005
# :Autore:   Markus Schiltknecht <markus@bluegap.ch>
#

"""
This module contains supporting classes for Monotone.
"""

__docformat__ = 'reStructuredText'

from shwrap import SystemCommand, shrepr
from source import UpdatableSourceWorkingDir, \
     ChangesetApplicationFailure, GetUpstreamChangesetsFailure
from target import SyncronizableTargetWorkingDir, TargetInitializationFailure

class MonotoneCommit(SystemCommand):
    COMMAND = "MONOTONE_AUTHOR=\"%(key)s\" monotone commit --date=\"%(date)s\" %(entries)s"

    def __call__(self, output=None, dry_run=False, **kwargs):
        log = open(self.working_dir + "/MT/log", "w");

        logmessage = kwargs.get('logmessage')
        if logmessage:
            log.write(logmessage + "\n")

        log.close();

        return SystemCommand.__call__(self, output=output,
                                      dry_run=dry_run, **kwargs)

class MonotoneAdd(SystemCommand):
    COMMAND = "monotone add %(entry)s"

class MonotoneRemove(SystemCommand):
    COMMAND = "monotone drop %(entry)s"


class MonotoneMv(SystemCommand):
    COMMAND = "monotone rename %(old)s %(new)s"


class MonotoneWorkingDir(UpdatableSourceWorkingDir, SyncronizableTargetWorkingDir):

    ## SyncronizableTargetWorkingDir

    def _addEntries(self, root, entries):
        """
        Add a sequence of entries.
        """

        c = MonotoneAdd(working_dir=root)
        c(entry=' '.join([shrepr(e.name) for e in entries]))

    def _commit(self,root, date, author, remark, changelog=None, entries=None):
        """
        Commit the changeset.
        """

        c = MonotoneCommit(working_dir=root)
        
        if entries:
            entries = ' '.join([shrepr(e) for e in entries])
        else:
            entries = '.'
            
        c(key=author, logmessage=changelog, date=date, entries=entries)

        if c.exit_status:
            raise TargetInitializationFailure(
                "'monotone commit returned %s" % c.exit_status)
        
    def _removeEntries(self, root, entries):
        """
        Remove a sequence of entries.
        """

        c = MonotoneRemove(working_dir=root)
        c(entry=' '.join([shrepr(e.name) for e in entries]))

    def _renameEntry(self, root, oldentry, newentry):
        """
        Rename an entry.
        """

        c = MonotoneMv(working_dir=root)
        c(old=shrepr(oldentry), new=repr(newentry))

    def _initializeWorkingDir(self, root, repository, module, subdir):
        """
        Execute `monotone setup`.
        """

        from os.path import join
        
        c = SystemCommand(working_dir=root, command="monotone setup .")
        c(output=True)

        if c.exit_status:
            raise TargetInitializationFailure(
                "'monotone setup' returned status %s" % c.exit_status)

        c = SystemCommand(working_dir=root,
                          command="monotone add %(entry)s")
        c(entry=shrepr(subdir))
