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
    COMMAND = "cvs log -N -S %(branch)s %(since)s 2>/dev/null"
       
    def __call__(self, output=None, dry_run=False, **kwargs):
        since = kwargs.get('since')
        if since:
            kwargs['since'] = "-d'%s<'" % since
        else:
            kwargs['since'] = ''

        branch = kwargs.get('branch')
        if branch:
            kwargs['branch'] = "-r%s" % branch
        else:
            kwargs['branch'] = ''
            
        return SystemCommand.__call__(self, output=output,
                                      dry_run=dry_run, **kwargs)


def changesets_from_cvslog(log, sincedate=None):
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

    from datetime import timedelta

    collected = ChangeSetCollector(log)
    collapsed = []

    threshold = timedelta(seconds=180)
    last = None
    
    for cs in collected:
        if sincedate and cs.date <= sincedate:
            continue
        
        if not last:
            last = cs
            collapsed.append(cs)
        else:
            if last.author == cs.author and \
               last.log == cs.log and \
               abs(last.date - cs.date) < threshold:
                last.entries.extend(cs.entries)
            else:
                last = cs
                collapsed.append(cs)

    return collapsed

        
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
    
    def __getGlobalRevision(self, timestamp, author, changelog):
        """
        CVS does not have the notion of a repository-wide revision number,
        since it tracks just single files.

        Here we could "count" the grouped changesets ala `cvsps`,
        but that's tricky because of branches.  Since right now there
        is nothing that depends on this being a number, not to mention
        a *serial* number, simply emit a (hopefully) unique signature...
        """

        # NB: the _getUpstreamChangesets() below depends on this format

        return str(timestamp)

    def __collect(self, timestamp, author, changelog, entry, revision):
        """Register a change set about an entry."""

        from changes import Changeset
        
        key = (timestamp, author, changelog)
        if self.changesets.has_key(key):
            return self.changesets[key].addEntry(entry, revision)
        else:
            cs = Changeset(self.__getGlobalRevision(timestamp,
                                                    author,
                                                    changelog),
                           timestamp, author, changelog)
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

        infoline = log.readline()

        info = infoline.split(';')

        assert info[0][:6] == 'date: '
        # 2004-04-19 14:45:42 +0000, the timezone may be missing
        dateparts = info[0][6:].split(' ') 
        day = dateparts[0]
        time = dateparts[1]
        y,m,d = map(int, day.split(day[4]))
        hh,mm,ss = map(int, time.split(':'))
        date = datetime(y,m,d,hh,mm,ss)

        assert info[1].strip()[:8] == 'author: '

        author = info[1].strip()[8:]

        assert info[2].strip()[:7] == 'state: '

        state = info[2].strip()[7:]

        # Fourth element, if present and like "lines +x -y", indicates
        # this is a change to an existing file. Otherwise its a new
        # one.

        newentry = not info[3].strip().startswith('lines: ')
        
        # The next line may be either the first of the changelog or a
        # continuation (?) of the preceeding info line with the
        # "branches"

        l = log.readline()
        if l.startswith('branches: ') and l.endswith(';\n'):
            infoline = infoline[:-1] + ';' + l
            # read the effective first line of log
            l = log.readline()
            
        mesg = []
        while (l <> '----------------------------\n' and
               l <> '=============================================================================\n'):
            mesg.append(l[:-1])
            l = log.readline()

        if len(mesg)==1 and mesg[0] == '*** empty log message ***':
            changelog = ''
        else:
            changelog = '\n'.join(mesg)
            
        return (date, author, changelog, entry, rev, state, newentry)
    
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

            l = log.readline()
            while l and l <> '----------------------------\n':
                l = log.readline()
                
            cs = self.__parseRevision(entry, log)
            while cs:
                date,author,changelog,e,rev,state,newentry = cs

                last = self.__collect(date, author, changelog, e, rev)
                if state == 'dead':
                    last.action_kind = last.DELETED
                elif newentry:
                    last.action_kind = last.ADDED
                else:
                    last.action_kind = last.UPDATED
                
                cs = self.__parseRevision(entry, log)
        

class CvsWorkingDir(CvspsWorkingDir):
    """
    Reimplement the mechanism used to get a *changeset* view of the
    CVS commits.
    """
    
    def _getUpstreamChangesets(self, root, sincerev=None):
        from os.path import join, exists
        from time import strptime

        cvslog = CvsLog(working_dir=root)
        
        if not sincerev:
            # We are bootstrapping, trying to collimate the
            # actual revision on disk with the changesets.
            # Start from the ancient entry timestamp.
            entries = CvsEntries(root)
            ancient = entries.getAncientEntry()
            since = ancient.timestamp.isoformat(sep=' ')
            sincedate = None
        else:
            # Assume this is from __getGlobalRevision()
            since = sincerev
            y,m,d,hh,mm,ss,d1,d2,d3=strptime(sincerev, "%a %b %d %H:%M:%S %Y")
            sincedate = datetime(y,m,d,hh,mm,ss)
            
        branch = ''
        fname = join(root, 'CVS', 'Tag')
        if exists(fname):
            tag = open(fname).read()
            if tag.startswith('T'):
                branch=tag[1:-1]

        changesets = []
        log = cvslog(output=True, since=since, branch=branch)
        for cs in changesets_from_cvslog(log, sincedate):
            changesets.append(cs)

        return changesets
    

class CvsEntry(object):
    """Collect the info about a file in a CVS working dir."""
    
    __slots__ = ('filename', 'cvs_version', 'timestamp', 'cvs_tag')

    def __init__(self, entry):
        """Initialize a CvsEntry."""

        from datetime import datetime
        from time import strptime
        
        dummy, fn, rev, ts, dummy, tag = entry.split('/')

        if ts.startswith('Result of merge+'):
            ts = ts[16:]
            
        self.filename = fn
        self.cvs_version = rev
        y,m,d,hh,mm,ss,d1,d2,d3 = strptime(ts, "%a %b %d %H:%M:%S %Y")
        self.timestamp = datetime(y,m,d,hh,mm,ss)
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
        
        entries = join(root, 'CVS', 'Entries')
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
                if (isdir(dir) and exists(join(dir, 'CVS', 'Entries'))
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

    def getAncientEntry(self):
        latest = None
        for e in self.files.values():
            if not latest:
                latest = e

            if e.timestamp < latest.timestamp:
                latest = e

        for d in self.directories.values():
            e = d.getAncientEntry()

            # skip if there are no entries in the directory
            if not e:
                continue
            
            if not latest:
                latest = e

            if e.timestamp < latest.timestamp:
                latest = e

        return latest
    
