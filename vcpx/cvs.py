#! /usr/bin/python
# -*- mode: python; coding: utf-8 -*-
# :Progetto: vcpx -- CVS details
# :Creato:   mer 16 giu 2004 00:46:12 CEST
# :Autore:   Lele Gaifax <lele@nautilus.homeip.net>
# 

__docformat__ = 'reStructuredText'

from cvsync.shwrap import SystemCommand
from source import UpdatableSourceWorkingDir
from target import SyncronizableTargetWorkingDir


class CvsPsLog(SystemCommand):
    COMMAND = "cvsps %(update)s-b%(branch)s"

    def __call__(self, output=None, dry_run=False, **kwargs):
        update = kwargs.get('update', '')
        if update:
            update = '-u '
        kwargs['update'] = update
        
        return SystemCommand.__call__(self, output=output,
                                      dry_run=dry_run, **kwargs)

    
class CvsUpdate(SystemCommand):
    COMMAND = 'cvs %(dry)supdate -d -r%(revision)s %(entry)s2>&1'
    
    def __call__(self, output=None, dry_run=False, **kwargs):
        if dry_run:
            kwargs['dry'] = '-n '
        else:
            kwargs['dry'] = ''

        return SystemCommand.__call__(self, output=output,
                                      dry_run=False, **kwargs)


class CvsAdd(SystemCommand):
    COMMAND = "cvs add %(entry)s"


class CvsCommit(SystemCommand):
    COMMAND = "cvs ci -F %(logfile)s %(entries)s"
    

class CvsRemove(SystemCommand):
    COMMAND = "cvs remove %(entry)s"


from textwrap import TextWrapper
from re import compile, MULTILINE
    
itemize_re = compile('^[ ]*[-*] ', MULTILINE)

def refill(msg):
    wrapper = TextWrapper()
    s = []
    items = itemize_re.split(msg)
    if len(items)>1:
        wrapper.initial_indent = ' - '
        wrapper.subsequent_indent = ' '*3
                
    for m in items:
        if m:
            s.append(wrapper.fill(m))
            s.append('')

    return '\n'.join(s)


class CvsWorkingDir(UpdatableSourceWorkingDir,
                    SyncronizableTargetWorkingDir):

    ## UpdatableSourceWorkingDir
    
    def __getLastUpstreamRevision(self, root):
        from os.path import join, exists
        
        fname = join(root, 'CVS', 'last-synced-revision')
        if exists(fname):
            return open(fname).read()

    def __setLastUpstreamRevision(self, root, revision):
        from os.path import join, exists
        
        fname = join(root, 'CVS', 'last-synced-revision')
        open(fname, 'w').write(revision)
        
    def _getUpstreamChangesets(self, root):
        cvsps = CvsPsLog(update=True, working_dir=root)

        startfrom_rev = self.__getLastUpstreamRevision(root)
        if startfrom_rev:
            startfrom_rev = int(startfrom_rev)
            
        from os.path import join, exists
        
        fname = join(self.root, 'CVS', 'Tag')
        if exists(fname):
            branch=open(fname).read()[1:-1]
        else:
            branch="HEAD"

        log = cvsps(output=True, branch=branch)
        for cs in self.__enumerateChangesets(log):
            if not startfrom_rev or (startfrom_rev<=cs.revision):
                self.changesets.append(cs)
                
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

            pset['log'] = refill(''.join(msg))

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
        for e in cs.entries:
            cvsup(entry=e.name, revision=e.new_revision)
        self.__setLastUpstreamRevision(root, revision)
        
    ## SyncronizableTargetWorkingDir

    def _addEntry(self, root, entry):
        """
        Add a new entry, maybe registering the directory as well.
        """

        from os.path import split, join, exists

        basedir = split(entry)[0]
        if basedir and not exists(join(basedir, 'CVS')):
            self._addEntry(root, basedir)
        
        c = CvsAdd(working_dir=root)
        c(entry=entry)

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
