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
from source import UpdatableSourceWorkingDir, ChangesetApplicationFailure
from target import SyncronizableTargetWorkingDir, TargetInitializationFailure


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
    COMMAND = 'cvs -q %(dry)supdate -d -r%(revision)s %(entry)s 2>&1'
    
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


def compare_cvs_revs(rev1, rev2):
    """Compare two CVS revision numerically, not alphabetically."""

    if not rev1: rev1 = '0'
    if not rev2: rev2 = '0'

    r1 = [int(n) for n in rev1.split('.')]
    r2 = [int(n) for n in rev2.split('.')]
    
    return cmp(r1, r2)


class CvsWorkingDir(UpdatableSourceWorkingDir,
                    SyncronizableTargetWorkingDir):

    """
    An instance of this class represent a read/write CVS working directory,
    so that it can be used both as source of patches, or as a target
    repository.

    It uses `cvsps` to do the actual fetch of the changesets metadata
    from the server, so that we can reasonably group together related
    changes that would otherwise be sparsed, as CVS is file-centric.
    """
    
    ## UpdatableSourceWorkingDir
    
    def _getUpstreamChangesets(self, root, sincerev=None):
        cvsps = CvsPsLog(working_dir=root)
        
        from os.path import join, exists
         
        branch="HEAD"
        fname = join(root, 'CVS', 'Tag')
        if exists(fname):
            tag = open(fname).read()
            if tag.startswith('T'):
                branch=tag[1:-1]

        if sincerev:
            sincerev = int(sincerev)
            
        changesets = []
        log = cvsps(output=True, update=True, branch=branch)
        for cs in self.__enumerateChangesets(log, sincerev):
            changesets.append(cs)

        return changesets
    
    def __enumerateChangesets(self, log, sincerev=None):
        """
        Parse CVSps log.
        """

        from changes import Changeset, ChangesetEntry
        from datetime import datetime
        
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
            pset['revision'] = l[9:-1].strip()
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
                if not sincerev or (sincerev<int(pset['revision'])):
                    file,revs = l[1:-1].split(':')
                    fromrev,torev = revs.split('->')

                    e = ChangesetEntry(file)
                    e.old_revision = fromrev
                    e.new_revision = torev

                    if fromrev=='INITIAL':
                        e.action_kind = e.ADDED
                    elif "(DEAD)" in torev:
                        e.action_kind = e.DELETED
                        e.new_revision = torev[:torev.index('(DEAD)')]
                    else:
                        e.action_kind = e.UPDATED

                    entries.append(e)
                    
                l = log.readline()

            if not sincerev or (sincerev<int(pset['revision'])):
                cvsdate = pset['date']
                y,m,d = map(int, cvsdate[:10].split('/'))
                hh,mm,ss = map(int, cvsdate[11:19].split(':'))
                timestamp = datetime(y, m, d, hh, mm, ss)
                pset['date'] = timestamp
            
                yield Changeset(**pset)

    def _applyChangeset(self, root, changeset, logger=None):
        from os.path import join, exists, dirname
        from os import makedirs
        
        entries = CvsEntries(root)
        
        cvsup = CvsUpdate(working_dir=root)
        for e in changeset.entries:
            if e.action_kind == e.UPDATED:
                info = entries.getFileInfo(e.name)
                if info and info.cvs_version == e.new_revision:
                    if logger: logger.debug("skipping '%s' since it's already "
                                            "at revision %s", e.name,
                                            e.new_revision)
                    continue
                
            cvsup(output=True, entry=e.name, revision=e.new_revision)

            if cvsup.exit_status:
                raise ChangesetApplicationFailure(
                    "'cvs update' returned status %s" % cvsup.exit_status)
            
            if e.action_kind == e.DELETED:
                # XXX: should drop edir if empty
                pass
                
    def _checkoutUpstreamRevision(self, basedir, repository, module, revision,
                                  logger=None):
        """
        Concretely do the checkout of the upstream sources. Use `revision` as
        the name of the tag to get.

        Return the effective cvsps revision.
        """

        from os.path import join, exists
        
        wdir = join(basedir, module)
        if not exists(wdir):
            c = CvsCheckout(working_dir=basedir)
            c(output=True,
              repository=repository,
              module=module,
              revision=revision)
            if c.exit_status:
                raise TargetInitializationFailure(
                    "'cvs checkout' returned status %s" % c.exit_status)
        else:
            if logger: logger.info("Using existing %s", wdir)
            
        self.__forceTagOnEachEntry(wdir)
        
        entries = CvsEntries(wdir)
        
        # update cvsps cache, then loop over the changesets and find the
        # last applied, to find out the actual cvsps revision

        csets = self._getUpstreamChangesets(wdir)
        csets.reverse()
        found = False
        for cset in csets:
            for m in cset.entries:
                info = entries.getFileInfo(m.name)
                if info:
                    actualversion = info.cvs_version
                    found = compare_cvs_revs(actualversion,m.new_revision)>=0
                    if not found:
                        break
                
            if found:
                last = cset
                break

        if not found:
            raise TargetInitializationFailure(
                "Something went wrong, did not find the right cvsps "
                "revision in '%s'" % wdir)
        else:
            if logger: logger.info("working copy up to cvsps revision %s",
                                   last.revision)
            
        return last.revision
    
    def _willApplyChangeset(self, changeset):
        """
        This gets called just before applying each changeset.
        
        Since CVS has no "createdir" event, we have to take care
        of new directories, creating empty-but-reasonable CVS dirs.
        """

        for m in changeset.entries:
            if m.action_kind == m.ADDED:
                self.__createParentCVSDirectories(m.name)
            
        return True

    def __createParentCVSDirectories(self, path):
        """
        Verify that the hierarchy down to the entry is under CVS.

        If the directory containing the entry does not exists,
        create it and make it appear as under CVS so that succeding
        'cvs update' will work.
        """
        
        from os.path import split, join, exists
        from os import mkdir
        
        basedir = split(path)[0]

        assert basedir, "Uhm, going too far"
        
        cvsarea = join(basedir, 'CVS') 
        if basedir and not exists(cvsarea):
            parentcvs = self.__createParentCVSDirectories(basedir)

            if not exists(basedir):
                mkdir(basedir)

            # Create fake CVS area
            mkdir(cvsarea)

            # Create an empty "Entries" file
            entries = open(join(cvsarea, 'Entries'), 'w')
            entries.close()

            reposf = open(join(parentcvs, 'Repository'))
            rep = reposf.readline()[:-1]
            reposf.close()

            reposf = open(join(cvsarea, 'Repository'), 'w')
            reposf.write("%s/%s\n" % (rep, split(basedir)[1]))
            reposf.close()

            rootf = open(join(parentcvs, 'Root'))
            root = rootf.readline()
            rootf.close()

            rootf = open(join(cvsarea, 'Root'), 'w')
            rootf.write(root)
            rootf.close()

        return cvsarea
    
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

    def __forceTagOnEachEntry(self, root):
        """
        Massage each CVS/Entries file, locking (ie, tagging) each
        entry to its current CVS version.

        This is to prevent silly errors such those that could arise
        after a manual `cvs update` in the working directory.
        """
        
        from os import walk, rename
        from os.path import join

        for dir, subdirs, files in walk(root):
            if dir[-3:] == 'CVS':
                efn = join(dir, 'Entries')
                f = open(efn)
                entries = f.readlines()
                f.close()
                rename(efn, efn+'.old')
                
                newentries = []
                for e in entries:
                    if e.startswith('/'):
                        fields = e.split('/')
                        fields[-1] = "T%s\n" % fields[2]
                        newe = '/'.join(fields)
                        newentries.append(newe)
                    else:
                        newentries.append(e)

                f = open(efn, 'w')
                f.writelines(newentries)
                f.close()
    
    def _commit(self,root, date, author, remark, changelog=None, entries=None):
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

        if entries:
            entries = ' '.join(entries)
        else:
            entries = '.'
            
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


class CvsEntry(object):
    """Collect the info about a file in a CVS working dir."""
    
    __slots__ = ('filename', 'cvs_version', 'cvs_tag')

    def __init__(self, entry):
        """Initialize a CvsEntry."""
        
        dummy, fn, rev, date, dummy, tag = entry.split('/')
        self.filename = fn
        self.cvs_version = rev
        self.cvs_tag = tag

    def __str__(self):
        return "CvsEntry('%s', '%s', '%s')" % (self.filename,
                                               self.cvs_version,
                                               self.cvs_tag)


class CvsEntries(object):
    """Collection of CvsEntry."""

    __slots__ = ('files', 'directories', 'deleted')
    
    def __init__(self, root):
        """Parse CVS/Entries file.

           Walk down the working directory, collecting info from each
           CVS/Entries found."""

        from os.path import join, exists, isdir
        from os import listdir
        
        self.files = {}
        """Dict of `CvsEntry`, keyed on each file under revision control."""
        
        self.directories = {}
        """Dict of `CvsEntries`, keyed on subdirectories under revision
           control."""

        self.deleted = False
        """Flag to denote that this directory was removed."""
        
        entries = join(root, 'CVS/Entries')
        if exists(entries):
            for entry in open(entries).readlines():
                entry = entry[:-1]

                if entry.startswith('/'):
                    e = CvsEntry(entry)
                    if file and e.filename==file:
                        return e
                    else:
                        self.files[e.filename] = e
                elif entry.startswith('D/'):
                    d = entry.split('/')[1]
                    subdir = CvsEntries(join(root, d))
                    self.directories[d] = subdir
                elif entry == 'D':
                    self.deleted = True 

            # Sometimes the Entries file does not contain the directories:
            # crawl the current directory looking for missing ones.

            for entry in listdir(root):
                if entry == '.svn':
                    continue                
                dir = join(root, entry)
                if (isdir(dir) and exists(join(dir, 'CVS/Entries'))
                    and not self.directories.has_key(entry)):
                    self.directories[entry] = CvsEntries(dir)
                    
            if self.deleted:
                self.deleted = not self.files and not self.directories
            
    def __str__(self):
        return "CvsEntries(%d files, %d subdirectories)" % (
            len(self.files), len(self.directories))

    def getFileInfo(self, fpath):
        """Fetch the info about a path, if known.  Otherwise return None."""

        try:
            if '/' in fpath:
                dir,rest = fpath.split('/', 1)
                return self.directories[dir].getFileInfo(rest)
            else:
                return self.files[fpath]
        except KeyError:
            return None

    def removedDirectories(self, other, prefix=''):
        from os.path import join
        
        result = []
        for d in self.directories.keys():
            a = self.directories.get(d)
            b = other.directories.get(d)
            dirpath = join(prefix, d)
            if not b or b.deleted:
                result.append(dirpath)
            else:
                result.extend(a.removedDirectories(b, prefix=dirpath))
        return result

    def addedDirectories(self, other, prefix=''):
        from os.path import join
        
        result = []
        for d in other.directories.keys():
            a = self.directories.get(d)
            b = other.directories.get(d)
            dirpath = join(prefix, d)
            if not a:
                result.append(dirpath)
            else:
                result.extend(a.addedDirectories(b, prefix=dirpath))
        return result
    
    def compareDirectories(self, other):
        """Compare the directories with those of another instance and return
           a tuple (added, removed)."""

        added = self.addedDirectories(other)
        removed = self.removedDirectories(other)

        return (added, removed)


