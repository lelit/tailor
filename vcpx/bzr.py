# -*- mode: python; coding: utf-8 -*-
# :Progetto: vcpx -- baazar-ng support
# :Creato:   ven 20 mag 2005 08:15:02 CEST
# :Autore:   Johan Rydberg <jrydberg@gnu.org>
# :Licenza:  GNU General Public License
# 

"""
This module implements the backends for Baazar-NG.
"""

__docformat__ = 'reStructuredText'

from shwrap import SystemCommand, shrepr
from target import SyncronizableTargetWorkingDir, TargetInitializationFailure

class BzrCommit(SystemCommand):
    COMMAND = "bzr commit -m %(comment)s %(entries)s"

    def __call__(self, output=None, dry_run=False, **kwargs):
        logmessage = kwargs.get('logmessage')
        kwargs['comment'] = shrepr(logmessage)
        
        return SystemCommand.__call__(self, output=output,
                                      dry_run=dry_run, **kwargs)
    

class BzrWorkingDir(SyncronizableTargetWorkingDir):

    ## SyncronizableTargetWorkingDir

    def _addEntries(self, root, entries):
        """
        Add a sequence of entries.
        """

        c = SystemCommand(working_dir=root, command="bzr add %(entries)s")
        c(entries=' '.join([shrepr(e.name) for e in entries]))

    def _commit(self,root, date, author, remark, changelog=None, entries=None):
        """
        Commit the changeset.
        """

        c = BzrCommit(working_dir=root)
        
        logmessage = "%s\nOriginal author: %s\nDate: %s" % (remark, author,
                                                            date)
        if changelog:
            logmessage = logmessage + '\n\n' + changelog
            
        if entries:
            entries = ' '.join([shrepr(e) for e in entries])
        else:
            entries = '.'
            
        c(logmessage=logmessage, entries=entries)
        
    def _removeEntries(self, root, entries):
        """
        Remove a sequence of entries.
        """

        c = SystemCommand(working_dir=root, command="bzr remove %(entries)s")
        c(entries=' '.join([shrepr(e.name) for e in entries]))

    def _renameEntry(self, root, oldentry, newentry):
        """
        Rename an entry.
        """

        c = SystemCommand(working_dir=root,
                          command="bzr rename %(old)s %(new)s")
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
        self._commit(root, now, AUTHOR,
                     BOOTSTRAP_PATCHNAME % module,
                     BOOTSTRAP_CHANGELOG % locals(),
                     entries=[subdir, '%s/...' % subdir])

    def _initializeWorkingDir(self, root, repository, module, subdir):
        """
        Execute ``bzr init``.
        """

        from os import getenv
        from os.path import join
        from dualwd import IGNORED_METADIRS
        
        c = SystemCommand(working_dir=root, command="bzr init")
        c(output=True)

        if c.exit_status:
            raise TargetInitializationFailure(
                "'bzr init' returned status %s" % c.exit_status)

        #c = SystemCommand(working_dir=root,
        #                  command="bzr add %(entry)s")
        #c(entry=shrepr(subdir))

        # Create the .bzrignore file, that contains a glob per line,
        # with all known VCs metadirs to be skipped.
        ignore = open(join(root, '.hgignore'), 'w')
        ignore.write('\n'.join(['(^|/)%s($|/)' % md
                                for md in IGNORED_METADIRS]))
        ignore.write('\ntailor.log\ntailor.info\n')
        ignore.close()

        SyncronizableTargetWorkingDir._initializeWorkingDir(self, root,
                                                            repository, module,
                                                            subdir)
