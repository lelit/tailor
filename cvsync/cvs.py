#  -*- Python -*- -*- coding: iso-8859-1 -*-
# :Progetto: Bice -- Sync CVS->SVN: dettagli CVS
# :Sorgente: $HeadURL: http://svn.bice.dyndns.org/progetti/wip/tools/cvsync/cvs.py $
# :Creato:   sab 10 apr 2004 16:41:16 CEST
# :Autore:   Lele Gaifax <lele@nautilus.homeip.net>
# :Modifica: $LastChangedDate: 2004-05-21 14:33:02 +0200 (ven, 21 mag 2004) $
# :Fatta da: $LastChangedBy: lele $
# 

"""Needed CVS functionalities wrapped in a few classes."""

__docformat__ = 'reStructuredText'

from shwrap import SystemCommand

class CvsUpdateError(Exception):
    """Exception raised by the ``cvs update`` command."""
    pass


class CvsUpdate(SystemCommand):
    COMMAND = 'cvs %(dry)supdate -I .svn -d %(tag)s2>&1'
    
    def __call__(self, output=None, dry_run=False, **kwargs):
        if dry_run:
            kwargs['dry'] = '-n '
        else:
            kwargs['dry'] = ''

        tag = kwargs.get('tag')
        if tag:
            kwargs['tag'] = '-r%s ' % tag
        else:
            kwargs['tag'] = ''
            
        return SystemCommand.__call__(self, output=output,
                                      dry_run=False, **kwargs)


class CvsLogError(Exception):
    """Exception raised by the ``cvs log`` command."""
    pass


class CvsLog(SystemCommand):
    COMMAND = 'cvs log -N %(rev)s %(entry)s'
       
    def __call__(self, output=None, dry_run=False, **kwargs):
        rev = kwargs['rev']
        if rev:
            kwargs['rev'] = '-r%s' % rev
        
        return SystemCommand.__call__(self, output=output,
                                      dry_run=dry_run, **kwargs)


def compare_revs(rev1, rev2):
    """Compare two CVS revision numerically, not alphabetically."""

    if not rev1: rev1 = '0'
    if not rev2: rev2 = '0'
    
    r1 = [int(n) for n in rev1.split('.')]
    r2 = [int(n) for n in rev2.split('.')]

    return cmp(r1, r2)

class ChangeSetCollector(object):
    """Collector of the applied change sets."""
    
    def __init__(self, wc, relax):
        """Initialize a ChangeSetCollector instance.

           Loop over the modified entries and collect their logs.

           If `relax` is True, do not consider ``cvs log`` errors as
           fatal: do not raise a CvsLogError exception, simply emit a
           message.
           
           Return a ChangeSetCollector instance that holds all the
           messages."""

        from sync import CHANGESET_CACHE
        from os.path import exists
        import shelve
        
        self.changesets = {}
        """The dictionary mapping (date, author, log) to each entry."""
       
        cache = shelve.open(CHANGESET_CACHE, 'c', writeback=True)
        touched = wc.added + wc.modified + wc.removed + wc.conflicts
        cvslog = CvsLog()
        
        print "Fetching the CVS log of %d entries..." % len(touched)

        # Too bad that the CVS log option -rX::Y (that's just what we need
        # here) is unreliable, as sometimes it omits the Y log too.  So
        # we use the -rX:Y one, that has the drawback the it prints the
        # log for the initial X version...
        
        try:
            # First pass: record each actual revision range in the cache
            for entry in touched:
                if cache.has_key(entry):
                    # If the entry is already in the cache, use the
                    # revision stored there, since the working copy
                    # may be already at a newer one.
                    if type(cache[entry]) == type(''):
                        oldrev = cache[entry]
                    else:
                        oldrev = cache[entry][0]
                        
                    if oldrev:
                        fromrev = oldrev.split(':')[0]
                    else:
                        fromrev = ''
                else:                        
                    oldrev = wc.before.getFileInfo(entry)
                    if oldrev:
                        fromrev = oldrev.cvs_version
                    else:
                        fromrev = ''

                if wc.after:
                    newrev = wc.after.getFileInfo(entry)
                    if newrev:
                        torev = newrev.cvs_version
                    else:
                        torev = ''
                else:
                    torev = ''

                if fromrev or torev:
                    revrange = '%s:%s' % (fromrev, torev)
                else:
                    revrange = ''
                
                if (not cache.has_key(entry) or
                    type(cache[entry]) == type('')):
                    cache[entry] = revrange
                else:
                    if type(cache[entry]) <> type(''):
                        print "Using cached log for %s[%s]" % (entry,
                                                               cache[entry][0])
        except:
            from os import unlink

            cache.close()
            unlink(CHANGESET_CACHE)

            raise
        
        try:                
            # Second pass: do the actual query for the log
            for entry in cache.keys():
                if type(cache[entry]) == type(''):
                    rev = cache[entry]
                    log = cvslog(output=True, entry=repr(entry), rev=rev)
                    if cvslog.exit_status and relax:
                        print "Mmm, retrying once..."
                        log = cvslog(output=True, entry=repr(entry), rev=rev)
                    if cvslog.exit_status and relax:
                        print "Arg, third and last try..."
                        log = cvslog(output=True, entry=repr(entry), rev=rev)

                    if cvslog.exit_status:
                        if not relax:
                            raise CvsLogError("CVS log exited with status %d" %
                                              cvslog.exit_status)

                    cache[entry] = (rev, log)

            # Third pass: do the actual parse
            for entry in cache.keys():
                rev, log = cache[entry]
                if rev and not rev.startswith(':'):
                    firstrev = rev.split(':')[0]
                else:
                    firstrev = None
                lastrev = self.parseCvsLog(entry, log, firstrev)
                if rev.endswith(':') and lastrev:
                    rev = rev + lastrev
                cache[entry] = (rev, log)
        finally:
            cache.close()            

    def __str__(self):
        """Concatenate the collected change logs in a string suitable for the
           commit log.

           Format each message as nicely as possible, recognising itemized
           paragraphs and wrapping each one."""

        from textwrap import dedent, TextWrapper
        from re import compile, MULTILINE

        itemize_re = compile('^[ ]*[-*] ', MULTILINE)
        s = []
        keys = self.changesets.keys()
        keys.sort()
        wrapper = TextWrapper()
        for k in keys:
            d = 'Date: %s  Author: %s' % (k[0], k[1])
            s.append(d)
            s.append('-' * len(d))
            s.append('')

            entries = self.changesets[k]
            entries.sort()
            for e in entries:
                s.append(' * %s (%s)' % e)
            s.append('')

            msg = dedent(k[2])
            items = itemize_re.split(msg)
            if len(items)>1:
                wrapper.initial_indent = '   - '
                wrapper.subsequent_indent = ' '*5
            else:
                wrapper.initial_indent = wrapper.subsequent_indent = ' '*3
                
            for m in items:
                if m:
                    s.append(wrapper.fill(m))
                    s.append('')
                    
        return '\n'.join(s)
    
    def collect(self, timestamp, author, changelog, entry, revision):
        """Register a change set about an entry."""

        date = timestamp.split(' ')[0]
        key = (date, author, changelog)
        if self.changesets.has_key(key):
            if (entry,revision) not in self.changesets[key]:
                self.changesets[key].append((entry,revision))
        else:
            self.changesets[key] = [(entry,revision)]

    def parseRevision(self, entry, log):
        """Parse a single revision log, extracting the needed information
           and register it.

           Return None when there are no more logs to be parsed,
           otherwise the revision number."""
        
        revision = log.readline()
        if not revision or not revision.startswith('revision '):
            return None
        rev = revision[9:-1]
        info = log.readline().split(';')
        date = info[0][6:]
        author = info[1].strip()[8:]
        mesg = []
        l = log.readline()
        while (l <> '----------------------------\n' and
               l <> '=============================================================================\n'):
            mesg.append(l[:-1])
            l = log.readline()

        return (date, author, '\n'.join(mesg), entry, rev)
    
    def parseCvsLog(self, entry, log, firstrev):
        """Parse a complete CVS log of an entry.

           Since ``cvs log -rX::Y`` is *unreliable* (it omits even the
           log for Y, sometime), `log` should be generated by
           ``cvs log -rX:Y``, that is the inclusive form: the `firstrev`
           is then used to ignore revision X log."""

        log.seek(0)
        l = log.readline()
        while l and l <> '----------------------------\n':
            l = log.readline()

        cs = self.parseRevision(entry, log)
        while cs:
            date,author,changelog,e,rev = cs

            if not firstrev or compare_revs(rev, firstrev)>0:
                self.collect(date, author, changelog, e, rev)
                
            cs = self.parseRevision(entry, log)


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


class CvsWorkingDir(object):
    """Represent a CVS working directory."""

    __slots__ = ('root', 'before', 'after',
                 'added', 'removed', 'modified',
                 'merged', 'conflicts', 'obstructing')

    def __init__(self, root):
        """Initialize a CvsWorkingDir instance."""
        
        self.root = root
        """The directory in question."""

        self.before = CvsEntries(root)
        """Cache of files and directories entries, before anything happens."""

        self.after = None
        """Cache of files and directories entries, after the update."""
        
        self.added = []
        """List of added entries, after update."""
        
        self.modified = []
        """List of modified entries, after update."""

        self.merged = []
        """List of merged entries, after update."""
        
        self.removed = []
        """List of removed entries, after update."""
        
        self.conflicts = []
        """List of conflicting entries, after update."""

        self.obstructing = []
        """List of obstructing files, that CVS did not expect to find."""

    def __str__(self):
        return "CvsWorkingDir('%s', %s)" % (self.root, self.before)

    def parseUpdateLog(self, output, relax=True):
        """Do the actual parse of the output of ``cvs update``.

           Try to understand the madness, and populate the various
           lists: modified, added, removed and conflicts.

           Return True if there is any changed/added/removed entry.
           False *may* indicate conflicts."""

        for line in output:
            if len(line)<2:
                if not relax:
                    print "Unrecognised CVS update line:\n%r" % line
            elif line[0] in 'UPM' and line[1] == ' ':
                fname = line[2:-1]
                if self.before.getFileInfo(fname):
                    self.modified.append(fname)
                else:
                    self.added.append(fname)

                if line[0] == 'M':
                    # In CVS parlance this means either a merge OR a
                    # local modification. Will check for them later.
                    self.merged.append(fname)
            elif line[0] == 'A':
                self.added.append(line[2:-1])
            elif line[0] == 'C':
                fname = line[2:-1]
                if fname not in self.conflicts:
                    self.conflicts.append(fname)
            elif line[0] == '?':
                # not under CVS
                pass
            elif (line.startswith('cvs update: Updating ') or
                  line.startswith('cvs server: Updating ') or
                  (line.startswith('cvs update:') and
                   line.endswith('-- ignored\n'))):
                pass
            elif 'is modified but no longer in the repository' in line:
                fname = line[23:].split("'")[0]
                self.removed.append(fname)
            elif ((line.startswith('cvs server: ')
                   or line.startswith('cvs update: '))
                  and line.endswith('is no longer in the repository\n')):
                fname = line[line.index(':')+2:-32]
                self.removed.append(fname)
            elif 'is not (any longer) pertinent' in line:
                if "warning: '" in line:
                    fname = line[line.index('warning:')+10:
                                 line.index("' is not (any longer) pertinent")]
                elif "warning:" in line:
                    fname = line[line.index('warning:')+9:
                                 line.index(" is not (any longer) pertinent")]
                else:
                    fname = line[22:].split("'")[0]
                self.removed.append(fname)
            elif 'it is in the way' in line:
                fname = line[line.index('move away `')+11:
                             line.index("'; it is in the way")]
                self.obstructing.append(fname)
            elif line.startswith('cvs update: warning:') \
                 and line.endswith('was lost\n'):
                # cvs update: warning: examples.py was lost"
                fname = line[line.index('warning:')+9:-9]
                self.added.append(fname)                
            elif line.startswith('RCS file: ') \
                     or line.startswith('retrieving revision ') \
                     or line.startswith('Merging differences between ') \
                     or line.startswith('rcsmerge: warning: conflicts ') \
                     or line.startswith('cvs update: conflicts found in '):
                pass
            else:
                if not relax:
                    print "Unrecognised CVS update line:\n%r" % line

        if self.after:
            # Check about those 'M's
            for entry in self.merged:
                before = self.before.getFileInfo(entry)
                after = self.after.getFileInfo(entry)

                # If the two revision are the same, it means that CVS
                # didn't touch the entry, just told that it's been
                # diverged locally.
                if before.cvs_version == after.cvs_version:
                    self.modified.remove(entry)
                    
        return (self.added or
                self.removed or
                self.modified)

    def update(self, options, prevlog=None):
        """Execute a ``cvs update`` on the directory, or reload the
           log of a previous session given in `prevlog`.

           If `options.changelog` is True, parse the command output and
           eventually collect applied changes in a ChangeSetCollector
           and return it, or the list of conflicts if nothing changed.

           If `options.changelog` is False return True if any change **or**
           conflict actually occurred.

           If either `options.debug` or `options.dry_run` is True, do
           not consider ``cvs log`` errors as fatal: do not raise a
           CvsLogError exception, simply emit a message."""

        from sync import ERR_MESSAGE_FILE_NAME
        from shutil import copyfileobj

        dry_run = options.dry_run
        changelog = options.changelog
        debug = options.debug
        relax = debug or dry_run
        tag = options.cvstag or ''
        
        if not prevlog:
            cvsup = CvsUpdate()
            output = cvsup(output=True, dry_run=dry_run, tag=tag)

            errout = open(ERR_MESSAGE_FILE_NAME, 'w')
            copyfileobj(output, errout)
            errout.close()
            output.seek(0)
            
            if cvsup.exit_status:
                raise CvsUpdateError("CVS update exited with status %d" %
                                     cvsup.exit_status)
        else:
            output = prevlog

        if not dry_run:
            self.after = CvsEntries(self.root)
            
        logsneeded = self.parseUpdateLog(output, relax)

        # If needed, build up a changelog looping over each changed
        # entry asking the ``cvs log`` of the appropriate range of
        # revisions.
        if changelog:
            if logsneeded:
                return ChangeSetCollector(self, relax)
            else:
                return self.conflicts
        else:
            return (self.added or
                    self.removed or
                    self.conflicts or
                    self.modified)

    def compareDirectories(self):
        """Compare the directories before and after the update and return
           a tuple (added, removed)."""

        return self.before.compareDirectories(self.after)

