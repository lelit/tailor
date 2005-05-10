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
    COMMAND = "monotone commit --author=\"%(key)s\" --date=\"%(date)s\""

    def __call__(self, output=None, dry_run=False, **kwargs):

        from os.path import exists, join

        if not exists(join(self.working_dir, 'MT')):
            # If MonotoneCommit is called outside the working copy
            # (i.e. there is no MT directory) we test if we are given
            # only the subdir as entry to commit. In that case, switch
            # to root/subdir as working directory and issue a commit
            # without any entries.
            
            entries = kwargs['entries']
            entries = entries.replace(' ', '')
            entries = entries.strip('\"')
            if (exists(join(self.working_dir, entries))):
                self.working_dir = join(self.working_dir, entries)
                kwargs['entries'] = ""
            else:
                raise TargetInitializationFailure("not a valid monotone working copy (MT directory is missing in %s)" % self.working_dir)

        log = open(self.working_dir + "/MT/log", "w");

        logmessage = kwargs.get('logmessage')
        if logmessage:
            log.write(logmessage + "\n")

        log.close();

        return SystemCommand.__call__(self, output=output,
                                      dry_run=dry_run, **kwargs)

class MonotoneRemove(SystemCommand):
    COMMAND = "monotone drop %(entry)s"


class MonotoneMv(SystemCommand):
    COMMAND = "monotone rename %(old)s %(new)s"


class MonotoneWorkingDir(SyncronizableTargetWorkingDir):

    ## SyncronizableTargetWorkingDir

    def _addPathnames(self, root, names):
        """
        Add some new filesystem objects.
        """

        c = SystemCommand(working_dir=root, command="monotone add %(names)s")
        c(names=' '.join([shrepr(n) for n in names]))

    def _commit(self,root, date, author, remark, changelog=None, entries=None):
        """
        Commit the changeset.
        """

        c = MonotoneCommit(working_dir=root)
        
        if entries:
            entries = ' '.join([shrepr(e) for e in entries])
        else:
            entries = '.'

        # monotone doesn't like empty changelogs ...
        if changelog == None or len(changelog)<1:
            if len(remark)>0:
                changelog = remark
            else:
                changelog = "**** empty log message ****"
        changelog = changelog.replace('"', '\\"')
        
        # monotone date must be expressed as ISO8601 
        outstr = c(output=True, key=author, logmessage=changelog,
                   date=date.isoformat(), entries=entries)

        # monotone complaints if there are no changes from the last commit.
        # we ignore those errors ...
        if c.exit_status:
           if outstr.getvalue().find("monotone: misuse: no changes to commit") == -1:
               outstr.close()
               raise TargetInitializationFailure(
                  "'monotone commit returned %s" % c.exit_status)
        outstr.close()      
        
    def _removePathnames(self, root, names):
        """
        Remove some filesystem object.
        """

        c = MonotoneRemove(working_dir=root)
        c(entry=' '.join([shrepr(n) for n in names]))

    def _renamePathname(self, root, oldname, newname):
        """
        Rename a filesystem object.
        """

        c = MonotoneMv(working_dir=root)
        c(old=shrepr(oldname), new=repr(newname))

    def _initializeWorkingDir(self, root, repository, module, subdir):
        """
        Setup the monotone working copy
        
        The user must setup a monotone working directory himself. Then
        we simply use 'monotone commit', without having to specify a database
        file or branch. Monotone looks up the database and branch in it's MT
        directory.
        """

        from os.path import exists, join
        
        if not exists(join(root, subdir, 'MT')):
            raise TargetInitializationFailure("Please setup %s as a monotone working directory." % root)

        c = SystemCommand(working_dir=join(root, subdir),
                          command="monotone add %(names)s")
        c(names='.')
