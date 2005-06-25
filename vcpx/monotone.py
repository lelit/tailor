# -*- mode: python; coding: utf-8 -*-
# :Progetto: vcpx -- Monotone details
# :Creato:   Tue Apr 12 01:28:10 CEST 2005
# :Autore:   Markus Schiltknecht <markus@bluegap.ch>
# :Licenza:  GNU General Public License
#

"""
This module contains supporting classes for Monotone.
"""

__docformat__ = 'reStructuredText'

from shwrap import SystemCommand, shrepr, ReopenableNamedTemporaryFile
from source import UpdatableSourceWorkingDir, \
     ChangesetApplicationFailure, GetUpstreamChangesetsFailure
from target import SyncronizableTargetWorkingDir, TargetInitializationFailure
from sys import stderr

class MonotoneCommit(SystemCommand):
    COMMAND = "monotone commit --author=\"%(key)s\" --date=\"%(date)s\" --message-file=\"%(logfile)s\" 2>&1"

    def __call__(self, output=None, dry_run=False, **kwargs):

        # the log message is written on a temporary file
        rontf = ReopenableNamedTemporaryFile('mtn', 'tailor')
        logmessage = kwargs.get('logmessage')
        if logmessage:
            log = open(rontf.name, "w")
            log.write(logmessage)
            log.close()            
        kwargs['logfile'] = rontf.name

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
        
        # monotone dates must be expressed as ISO8601 
        outstr = c(output=True, key=author, logmessage=changelog,
                   date=date.isoformat(), entries=entries)

        # monotone complaints if there are no changes from the last commit.
        # we ignore those errors ...
        if c.exit_status:
           if outstr.getvalue().find("monotone: misuse: no changes to commit") == -1:
               stderr.write(outstr.getvalue())
               outstr.close()
               raise TargetInitializationFailure(
                  "'monotone commit returned %s" % c.exit_status)
           else:
               stderr.write("No changes to commit - changeset ignored\n")
             
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

        if not exists(join(root, 'MT')):
            raise TargetInitializationFailure("Please setup '%s' as a monotone working directory" % root)

        c = SystemCommand(working_dir=root,
                          command="monotone add %(names)s")
        c(names=subdir)
