#! /usr/bin/python
# -*- mode: python; coding: utf-8 -*-
# :Progetto: vcpx -- Darcs details
# :Creato:   ven 18 giu 2004 14:45:28 CEST
# :Autore:   Lele Gaifax <lele@nautilus.homeip.net>
# 

"""
This module contains supporting classes for the `darcs` versioning system.
"""

__docformat__ = 'reStructuredText'

from cvsync.shwrap import SystemCommand
from source import UpdatableSourceWorkingDir
from target import SyncronizableTargetWorkingDir


class DarcsInitialize(SystemCommand):
    COMMAND = "darcs initialize"


class DarcsRecord(SystemCommand):
    COMMAND = "darcs record --all --look-for-adds --author=%(author)s --logfile=%(logfile)s"

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
    COMMAND = "darcs mv --standard-verbosity %(old)s %(new)s"


class DarcsRemove(SystemCommand):
    COMMAND = "darcs remove --standard-verbosity %(entry)s"


class DarcsAdd(SystemCommand):
    COMMAND = "darcs add --not-recursive --standard-verbosity %(entry)s"


class DarcsTag(SystemCommand):
    COMMAND = "darcs tag --standard-verbosity --patch-name='%(tagname)s'"


class DarcsWorkingDir(UpdatableSourceWorkingDir,SyncronizableTargetWorkingDir):
    """
    A working directory under ``darcs``.
    """
    
    ## UpdatableSourceWorkingDir
    
    def _getUpstreamChangesets(self, root):
        """
        Do the actual work of fetching the upstream changeset.
        
        This is different from the other mechanism: here we want register
        with the target the changes we submitted to this repository to be
        sent back to upstream.

        So, here we actually list the changes after the last tag.
        """

        tagname = self._getLastTag(root)
        # darcs changes --from-tag=tagname --xml-output
        
    def _applyChangeset(self, root, changeset):
        """
        Do the actual work of applying the changeset to the working copy.

        The changeset is already applied, so this is a do nothing method.
        """

        return
    
    ## SyncronizableTargetWorkingDir

    def _replayChangeset(self, root, changeset):
        """
        Do nothing except for renames, as darcs will do the right
        thing on disappeared and added files.
        """

        for e in changeset.entries:
            if e.action_kind == e.RENAMED:
                self._renameEntry(root, e.old_name, e.name)
    
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
        c(output=True, patchname=remark, logmessage=changelog, author=author)
        
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

    def initializeNewWorkingDir(self, root, repository, revision):
        """
        Initialize the new repository and create a tag.
        """
        
        SyncronizableTargetWorkingDir.initializeNewWorkingDir(self,
                                                              root,
                                                              repository,
                                                              revision)
        self._createTag(root, 'Upstream revision %s' % revision)

    def _createTag(self, root, tagname):
        """
        Tag the current situation and remember this as the *last tag*.
        """

        from os.path import join, exists
        
        c = DarcsTag(working_dir=root)
        c(tagname=tagname)
        
        fname = join(root, '_darcs', 'last-sync-tag')
        f = open(fname, 'w')
        f.write(tagname)
        f.close()
        
    def _getLastTag(self, root):
        """
        Return the name of the last emitted tag, if any, otherwise None.
        """
        
        from os.path import join, exists
        
        fname = join(root, '_darcs', 'last-sync-tag')
        if exists(fname):
            f = open(fname)
            tagname = f.read()
            f.close()
            
            return tagname

    def _initializeWorkingDir(self, root):
        """
        Execute `darcs initialize`.
        """
        
        c = DarcsInitialize(working_dir=root)
        c(output=True)

