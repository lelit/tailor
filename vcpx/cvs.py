#! /usr/bin/python
# -*- mode: python; coding: utf-8 -*-
# :Progetto: vcpx -- CVS details
# :Creato:   mer 16 giu 2004 00:46:12 CEST
# :Autore:   Lele Gaifax <lele@nautilus.homeip.net>
# 

"""
This module contains supporting classes for CVS. To get a
cross-repository revision number ala Subversion, the implementation
uses `cvsps` to fetch the changes from the upstream repository.
"""

__docformat__ = 'reStructuredText'

from shwrap import SystemCommand
from source import UpdatableSourceWorkingDir
from target import SyncronizableTargetWorkingDir


class CvsPsLog(SystemCommand):
    COMMAND = "cvsps %(update)s-b %(branch)s 2>/dev/null"

    def __call__(self, output=None, dry_run=False, **kwargs):
        update = kwargs.get('update', '')
        if update:
            update = '-u '
        kwargs['update'] = update
        
        return SystemCommand.__call__(self, output=output,
                                      dry_run=dry_run, **kwargs)

    
class CvsUpdate(SystemCommand):
    COMMAND = 'cvs -q %(dry)supdate -d -r%(revision)s %(entry)s2>&1'
    
    def __call__(self, output=None, dry_run=False, **kwargs):
        if dry_run:
            kwargs['dry'] = '-n '
        else:
            kwargs['dry'] = ''

        return SystemCommand.__call__(self, output=output,
                                      dry_run=False, **kwargs)


class CvsAdd(SystemCommand):
    COMMAND = "cvs -q add %(entry)s"


class CvsCommit(SystemCommand):
    COMMAND = "cvs -q ci -F %(logfile)s %(entries)s"
    

class CvsRemove(SystemCommand):
    COMMAND = "cvs -q remove %(entry)s"


class CvsCheckout(SystemCommand):
    COMMAND = "cvs -q -d%(repository)s checkout -r %(revision)s %(module)s"


class CvsWorkingDir(UpdatableSourceWorkingDir,
                    SyncronizableTargetWorkingDir):

    """
    An instance of this class represent a read/write CVS working directory,
    so that it can be used both as source of patches, or as a target
    repository.

    They use `cvsps` to actual fetch the changesets metadata from the
    server, so that we can reasonably group related changes that would
    otherwise be sparsed, as CVS is file-centric.

    To accomodate this, the last revision (from cvsps point of view)
    imported in the repository is stored in a file in the `CVS`
    directory at the root of the working copy. This shouldn't
    interfere with the normal operations, but since the file isn't
    versioned you may easily loose it....
    """
    
    ## UpdatableSourceWorkingDir
    
    def __getLastUpstreamRevision(self, root):
        from os.path import join, exists
        
        fname = join(root, 'CVS', 'last-synced-revision')
        if exists(fname):
            f = open(fname)
            lastrev = f.read()
            f.close()
            return lastrev

    def __setLastUpstreamRevision(self, root, revision):
        from os.path import join, exists
        
        fname = join(root, 'CVS', 'last-synced-revision')
        f = open(fname, 'w')
        f.write(revision)
        f.close()

    def _getUpstreamChangesets(self, root):
        cvsps = CvsPsLog(working_dir=root)

        startfrom_rev = self.__getLastUpstreamRevision(root)
        if startfrom_rev:
            startfrom_rev = int(startfrom_rev)+1
            
        from os.path import join, exists
        
        fname = join(root, 'CVS', 'Tag')
        if exists(fname):
            branch=open(fname).read()[1:-1]
        else:
            branch="HEAD"

        changesets = []
        log = cvsps(output=True, update=True, branch=branch)
        for cs in self.__enumerateChangesets(log):
            if not startfrom_rev or (startfrom_rev<=int(cs.revision)):
                changesets.append(cs)

        return changesets
    
    def __enumerateChangesets(self, log):
        """
        Parse CVSps log.
        """

        from changes import Changeset, ChangesetEntry

        # cvsps output sample:
        ## ---------------------
        ## PatchSet 1500
        ## Date: 2004/05/09 17:54:22
        ## Author: grubert
        ## Branch: HEAD
        ## Tag: (none)
        ## Log:
        ## Tell the reason for using mbox (not wrapping long lines).
        ##
        ## Members:
        ##         docutils/writers/latex2e.py:1.78->1.79
        
        log.seek(0)

        l = None
        while 1:
            l = log.readline()
            if l <> '---------------------\n':
                break

            l = log.readline()
            assert l.startswith('PatchSet '), "Parse error: %s"%l

            pset = {}
            pset['revision'] = l[9:-1]
            l = log.readline()
            while not l.startswith('Log:'):
                field,value = l.split(':',1)
                pset[field.lower()] = value.strip()
                l = log.readline()

            msg = []
            l = log.readline()
            msg.append(l)
            l = log.readline()
            while l <> 'Members: \n':
                msg.append(l)
                l = log.readline()

            pset['log'] = ''.join(msg)

            assert l.startswith('Members:'), "Parse error: %s" % l

            pset['entries'] = entries = []
            l = log.readline()

            while l.startswith('\t'):
                file,revs = l[1:-1].split(':')
                fromrev,torev = revs.split('->')

                e = ChangesetEntry(file)
                e.old_revision = fromrev
                e.new_revision = torev

                if fromrev=='INITIAL':
                    e.action_kind = e.ADDED
                elif "(DEAD)" in torev:
                    e.action_kind = e.DELETED
                else:
                    e.action_kind = e.UPDATED

                entries.append(e)
                l = log.readline()

            yield Changeset(**pset)

    def _applyChangeset(self, root, changeset):
        cvsup = CvsUpdate(working_dir=root)
        for e in changeset.entries:
            cvsup(entry=e.name, revision=e.new_revision)
        self.__setLastUpstreamRevision(root, changeset.revision)
        
    ## SyncronizableTargetWorkingDir

    def _addEntry(self, root, entry):
        """
        Add a new entry, maybe registering the directory as well.
        """

        from os.path import split, join, exists

        basedir = split(entry)[0]
        if basedir and not exists(join(root, basedir, 'CVS')):
            self._addEntry(root, basedir)
        
        c = CvsAdd(working_dir=root)
        c(entry=entry)

    def _checkoutUpstreamRevision(self, basedir, repository, module, revision):
        """
        Concretely do the checkout of the upstream sources. Use `revision` as
        the name of the tag to get.
        """

        from os.path import join
        
        c = CvsCheckout(working_dir=basedir)
        c(output=True, repository=repository, module=module, revision=revision)

        # update cvsps cache and get its last CVS "revision"
        wdir = join(basedir, module)
        csets = self._getUpstreamChangesets(wdir)
        last = csets[-1]
        self.__setLastUpstreamRevision(wdir, last.revision)

    def _commit(self, root, author, remark, changelog=None, entries=None):
        """
        Commit the changeset.
        """
        
        from tempfile import NamedTemporaryFile
        
        log = NamedTemporaryFile(bufsize=0)
        log.write(remark)
        log.write('\n')
        if changelog:
            log.write(changelog)
            log.write('\n')
        
        c = CvsCommit(working_dir=root)
        c(entries=entries, logfile=log.name)
        log.close()
        
    def _removeEntry(self, root, entry):
        """
        Remove an entry.
        """

        c = CvsRemove(working_dir=root)
        c(entry=entry)

    def _renameEntry(self, root, oldentry, newentry):
        """
        Rename an entry.
        """

        self._removeEntry(root, oldentry)
        self._addEntry(root, newentry)

    def _initializeWorkingDir(self, root, addentry=None):
        """
        Add the given directory to an already existing CVS working tree.
        """

        SyncronizableTargetWorkingDir._initializeWorkingDir(self, root, CvsAdd)
