#! /usr/bin/python
# -*- mode: python; coding: utf-8 -*-
# :Progetto: vcpx -- Pure CVS solution
# :Creato:   dom 11 lug 2004 01:59:36 CEST
# :Autore:   Lele Gaifax <lele@nautilus.homeip.net>
# 

"""
Given `cvsps` shortcomings, this backend uses CVS only.
"""

__docformat__ = 'reStructuredText'

from shwrap import SystemCommand
from cvsps import CvspsWorkingDir


def compare_cvs_revs(rev1, rev2):
    """Compare two CVS revision numerically, not alphabetically."""

    if not rev1: rev1 = '0'
    if not rev2: rev2 = '0'

    r1 = [int(n) for n in rev1.split('.')]
    r2 = [int(n) for n in rev2.split('.')]
    
    return cmp(r1, r2)


class CvsLog(SystemCommand):
    COMMAND = "cvs log -N -S %(since)s"
       
    def __call__(self, output=None, dry_run=False, **kwargs):
        since = kwargs.get('since')
        if since:
            kwargs['since'] = "-d '%s<'" % str(since)
        else:
            kwargs['since'] = ''
            
        return SystemCommand.__call__(self, output=output,
                                      dry_run=dry_run, **kwargs)

def changesets_from_cvslog(log, sincerev=None):
    """
    Parse CVS log.
    """

    ## RCS file: /cvsroot/docutils/docutils/THANKS.txt,v
    ## Working file: THANKS.txt
    ## head: 1.2
    ## branch:
    ## locks: strict
    ## access list:
    ## symbolic names:
    ## keyword substitution: kv
    ## total revisions: 2;      selected revisions: 2
    ## description:
    ## ----------------------------
    ## revision 1.2
    ## date: 2004/06/10 02:17:20;  author: goodger;  state: Exp;  lines: +3 -2
    ## updated
    ## ----------------------------
    ## revision 1.1
    ## date: 2004/06/03 13:50:58;  author: goodger;  state: Exp;
    ## Added to project (exctracted from HISTORY.txt)
    ## =====================================================================...

    coll = ChangeSetCollector(log)
    for cs in coll:
        yield cs
        
class ChangeSetCollector(object):
    """Collector of the applied change sets."""
    
    def __init__(self, log):
        """
        Initialize a ChangeSetCollector instance.

        Loop over the modified entries and collect their logs.
        """

        self.changesets = {}
        """The dictionary mapping (date, author, log) to each entry."""
       
        self.__parseCvsLog(log)
        
    def __iter__(self):
        keys = self.changesets.keys()
        keys.sort()
        return iter([self.changesets[k] for k in keys])
    
    def __collect(self, timestamp, author, changelog, entry, revision):
        """Register a change set about an entry."""

        from changes import Changeset
        
        key = (timestamp, author, changelog)
        if self.changesets.has_key(key):
            return self.changesets[key].addEntry(entry, revision)
        else:
            cs = Changeset(revision, timestamp, author, changelog)
            self.changesets[key] = cs
            return cs.addEntry(entry, revision)

    def __parseRevision(self, entry, log):
        """Parse a single revision log, extracting the needed information
           and register it.

           Return None when there are no more logs to be parsed,
           otherwise the revision number."""

        from datetime import datetime
        
        revision = log.readline()
        if not revision or not revision.startswith('revision '):
            return None
        rev = revision[9:-1]

        info = log.readline().split(';')
        
        day,time = info[0][6:].split(' ')
        y,m,d = map(int, day.split('/'))
        hh,mm,ss = map(int, time.split(':'))
        date = datetime(y,m,d,hh,mm,ss)
        author = info[1].strip()[8:]
        mesg = []
        l = log.readline()
        while (l <> '----------------------------\n' and
               l <> '=============================================================================\n'):
            mesg.append(l[:-1])
            l = log.readline()

        return (date, author, '\n'.join(mesg), entry, rev)
    
    def __parseCvsLog(self, log):
        """Parse a complete CVS log."""

        while 1:
            l = log.readline()
            while l and not l.startswith('Working file: '):
                l = log.readline()
            
            if not l.startswith('Working file: '):
                break

            entry = l[14:-1]
            
            l = log.readline()
            while l and not l.startswith('total revisions: '):
                l = log.readline()

            assert l.startswith('total revisions: ')

            total, selected = l.split(';')
            total = total.strip()
            selected = selected.strip()

            # If the log shows all changes to the entry, than it's
            # a new one
            
            newentry = total.split(':')[1] == selected.split(':')[1]
            
            l = log.readline()
            while l and l <> '----------------------------\n':
                l = log.readline()
                
            cs = self.__parseRevision(entry, log)
            while cs:
                date,author,changelog,e,rev = cs

                last = self.__collect(date, author, changelog, e, rev)
                last.action_kind = last.UPDATED
                
                cs = self.__parseRevision(entry, log)

            if newentry:
                last.action_kind = last.ADDED

class CvsWorkingDir(CvspsWorkingDir):
    """
    Reimplement the mechanism used to get a *changeset* view of the
    CVS commits.
    """
    
    def _getUpstreamChangesets(self, root, sincerev=None):
        cvslog = CvsLog(working_dir=root)
        
        from os.path import join, exists
         
        if sincerev:
            sincerev = int(sincerev)

            # XXX: derive the date from the revision
            since = dosomethingsmart(sincerev)
        else:
            since = None
            
        changesets = []
        log = cvslog(output=True, since=since)
        for cs in changesets_from_cvslog(log, sincerev):
            changesets.append(cs)

        return changesets
    

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


