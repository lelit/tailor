# -*- mode: python; coding: utf-8 -*-
# :Progetto: vcpx -- Pure CVS solution
# :Creato:   dom 11 lug 2004 01:59:36 CEST
# :Autore:   Lele Gaifax <lele@nautilus.homeip.net>
# :Licenza:  GNU General Public License
#

"""
Given `cvsps` shortcomings, this backend uses CVS only.
"""

__docformat__ = 'reStructuredText'

from vcpx.repository.cvsps import CvspsRepository, CvspsWorkingDir
from vcpx.shwrap import ExternalCommand, STDOUT, PIPE
from vcpx.source import GetUpstreamChangesetsFailure
from vcpx.config import ConfigurationError
from vcpx.tzinfo import UTC


class CvsRepository(CvspsRepository):
    def _load(self, project):
        CvspsRepository._load(self, project)

        tmc = project.config.get(self.name, 'trim-module-components', '0')
        self.trim_module_components = int(tmc)


def normalize_cvs_rev(rev):
    """Convert a revision string to a tuple of numbers, eliminating the
    penultimate zero in a 'magic branch number' if there is one.
    1.1.1.1 is converted to (1,1). """
    if not rev: rev = '0'

    # handle locked files by taking only the first part of the
    # revision string to handle gracefully lines like "1.1 locked"
    rev = rev.split()[0]

    r = [int(n) for n in rev.split('.')]
    # convert "magic branch numbers" like 1.2.0.2 to regular
    # branch numbers like 1.2.2.
    if len(r) > 2 and r[-2] == 0:
        r = r[0:-2] + r[-1:]

    if r == [1,1,1,1]:
        r = [1,1]

    return tuple(r)

def compare_cvs_revs(revstr1, revstr2):
    """Compare two CVS revision strings numerically, not alphabetically."""

    r1 = normalize_cvs_rev(revstr1)
    r2 = normalize_cvs_rev(revstr2)

    return cmp(r1, r2)

def cvs_revs_same_branch(rev1, rev2):
    """True iff the two normalized revision numbers are on the same branch."""

    # Odd-length revisions are branch numbers, even-length ones
    # are revision numbers.

    # Two branch numbers can't be on the same branch unless they're identical.
    if len(rev1) % 2 and len(rev2) % 2:
        return rev1 == rev2

    # Two revision numbers are on the same branch if they
    # agree up to the last number.
    if len(rev1) % 2 == 0 and len(rev2) % 2 == 0:
        return rev1[0:-1] == rev2[0:-1]

    # One branch number, one revision number.  If by removing the last number
    # of one you get the other, then they're on the same branch, regardless of
    # which is longer.  E.g. revision 1.2 is the root of the branch 1.2.2;
    # revision 1.2.2.2 is directly on the branch 1.2.2.
    if rev1[0:-1] == rev2:
        return True

    if rev2[0:-1] == rev1:
        return True

    return False

def is_branch(rev):
    """True iff the given (normalized) revision number is a branch number"""
    if len(rev) % 2:
        return True

def rev2branch(rev):
    """Return the branch on which this (normalized) revision lies"""
    assert not is_branch(rev)
    return rev[0:-1]


def changesets_from_cvslog(log, module, branch=None,
                           entries=None, since=None, threshold=None,
                           trim_module_components=0):
    """
    Parse CVS log.
    """

    collected = ChangeSetCollector(log, module, branch, entries, since,
                                   trim_module_components)

    last = None

    if threshold is None:
        from datetime import timedelta
        threshold = timedelta(seconds=180)

    # Loop over collected changesets, and collapse those with same author,
    # same changelog and that were committed within a threshold one from the
    # other. If they have entries in common, keep them separated. Special
    # treatment to deleted entries, given that sometime there are two
    # deletions on the same file: in that case, keep only the last one,
    # with higher revision.
    for cs in collected:
        if (last and last.author == cs.author and last.log == cs.log and
            abs(lastts - cs.date) < threshold and
            not last.tags and
            not [e for e in cs.entries
                 if e.name in [n.name for n in last.entries
                               if n.action_kind <> e.action_kind]]):
            for e in cs.entries:
                if e.action_kind == e.DELETED:
                    doubledelete = False
                    for n in last.entries:
                        if n.name == e.name and n.action_kind == n.DELETED:
                            doubledelete = True
                            n.new_revision = e.new_revision
                            break
                    if not doubledelete:
                        last.entries.append(e)
                else:
                    last.entries.append(e)
            last.tags = cs.tags
            if lastts < cs.date:
                lastts = cs.date
        else:
            if last:
                last.date = lastts
                yield last
            last = cs
            lastts = cs.date

    if last:
        yield last


def _getGlobalCVSRevision(timestamp, author):
    """
    CVS does not have the notion of a repository-wide revision number,
    since it tracks just single files.

    Here we could "count" the grouped changesets ala `cvsps`,
    but that's tricky because of branches.  Since right now there
    is nothing that depends on this being a number, not to mention
    a *serial* number, simply emit a (hopefully) unique signature...
    """

    # don't print timezone info, to remain compatible (does not buy us
    # anything, it being always UTC)
    return "%s by %s" % (timestamp.replace(tzinfo=None), author)

def _splitGlobalCVSRevision(revision):
    """
    Split what _getGlobalCVSRevision() returns into the two components.
    """

    assert ' by ' in revision, \
           "Simple revision found, expected 'timestamp by author'"
    return revision.split(' by ')


class ChangeSetCollector(object):
    """Collector of the applied change sets."""

    # Some string constants we look for in CVS output.
    intra_sep = '-' * 28 + '\n'
    inter_sep = '=' * 77 + '\n'

    def __init__(self, log, module, branch, entries, since,
                 trim_module_components=0):
        """
        Initialize a ChangeSetCollector instance.

        Loop over the modified entries and collect their logs.
        """

        from logging import getLogger

        self.changesets = {}
        """The dictionary mapping (date, author, log) to each entry."""

        self.cvslog = log
        """The log to be parsed."""

        self.module = module
        """The CVS module name."""

        self.__lookahead = []
        """The look ahead line stack."""

        self.log = getLogger('tailor.vcpx.cvs.collector')

        self.trim_module_components = trim_module_components

        self.__parseCvsLog(branch, entries, since)

    def __iter__(self):
        # Since there can be duplicate keys, try to produce the right
        # ordering taking into account the first action (thus ADDs
        # will preceed UPDs...)
        keys = []
        for k,c in self.changesets.items():
            action1 = len(c.entries)>0 and c.entries[0].action_kind or ' '
            keys.append( (k[0], k[1], action1, k[2]) )
        keys.sort()

        return iter([self.changesets[(k[0], k[1], k[3])] for k in keys])

    def __collect(self, timestamp, author, changelog, entry, revision):
        """Register a change set about an entry."""

        from vcpx.changes import Changeset

        key = (timestamp, author, changelog)
        if self.changesets.has_key(key):
            cs = self.changesets[key]
            for e in cs.entries:
                if e.name == entry:
                    return e
            return cs.addEntry(entry, revision)
        else:
            cs = Changeset(_getGlobalCVSRevision(timestamp, author),
                           timestamp, author, changelog)
            self.changesets[key] = cs
            return cs.addEntry(entry, revision)

    def __readline(self, lookahead=False):
        """
        Read a line from the log, intercepting the directory being listed.

        This is used to determine the pathname of each entry, relative to
        the root of the working copy.
        """

        if lookahead:
            l = self.cvslog.readline()
            self.__lookahead.append(l)
            return l
        else:
            if self.__lookahead:
                l = self.__lookahead.pop(0)
            else:
                l = self.cvslog.readline()
        # Some version of CVS emits the following with a different char-case
        while l.lower().startswith('cvs rlog: logging '):
            currentdir = l[18:-1]
            if currentdir.startswith(self.module):
                # If the directory starts with the module name, keep
                # just the remaining part
                self.__currentdir = currentdir[len(self.module)+1:]
            elif self.trim_module_components:
                # This is a quick&dirty workaround to the CVS modules
                # issue: if, by some heuristic, the user tells how
                # many components to cut off...
                parts = currentdir.split('/')
                if len(parts)>self.trim_module_components:
                    parts = parts[self.trim_module_components:]
                else:
                    parts = []
                self.__currentdir = '/'.join(parts)
            else:
                # strip away first component, the name of the product
                slash = currentdir.find('/')
                if slash >= 0:
                    self.__currentdir = currentdir[slash+1:]
                else:
                    self.__currentdir = ''
            l = self.cvslog.readline()

        return l

    def __parseRevision(self, entry):
        """
        Parse a single revision log, extracting the needed information.

        Return None when there are no more logs to be parsed,
        otherwise a tuple with the relevant data.
        """

        from datetime import datetime

        revision = self.__readline()
        if not revision or not revision.startswith('revision '):
            return None
        # Don't just knock off the leading 'revision ' here.
        # There may be locks, in which case we get output like:
        # 'revision 1.4    locked by: mem;', with a tab char.
        rev = revision[:-1].split()[1]

        infoline = self.__readline()

        info = infoline.split(';')

        assert info[0][:6] == 'date: ', infoline

        # 2004-04-19 14:45:42 +0000, the timezone may be missing
        dateparts = info[0][6:].split(' ')
        assert len(dateparts) >= 2, `dateparts`

        day = dateparts[0]
        time = dateparts[1]
        y,m,d = map(int, day.split(day[4]))
        hh,mm,ss = map(int, time.split(':'))
        date = datetime(y,m,d,hh,mm,ss,0,UTC)

        assert info[1].strip()[:8] == 'author: ', infoline

        author = info[1].strip()[8:]

        assert info[2].strip()[:7] == 'state: ', infoline

        state = info[2].strip()[7:]

        # Fourth element, if present and like "lines +x -y", indicates
        # this is a change to an existing file. Otherwise its a new
        # one.

        newentry = not info[3].strip().startswith('lines: ')

        # The next line may be either the first of the changelog or a
        # continuation (?) of the preceeding info line with the
        # "branches"

        l = self.__readline()
        if l.startswith('branches: ') and l.endswith(';\n'):
            infoline = infoline[:-1] + ';' + l
            # read the effective first line of log
            l = self.__readline()

        mesg = []
        while True:
            if l == self.intra_sep:
                if self.__readline(True).startswith('revision '):
                    break
            if l in (None, '', self.inter_sep):
                break
            if l<>self.intra_sep:
                mesg.append(l[:-1])
            l = self.__readline()

        if len(mesg)==1 and mesg[0] == '*** empty log message ***':
            changelog = ''
        else:
            changelog = '\n'.join(mesg)

        return (date, author, changelog, entry, rev, state, newentry)

    def __parseCvsLog(self, branch, entries, since):
        """Parse a complete CVS log."""

        from os.path import split, join
        from re import compile
        from time import strptime
        from datetime import datetime
        from vcpx.changes import Changeset

        revcount_regex = compile('\\bselected revisions:\\s*(\\d+)\\b')

        self.__currentdir = None

        file2rev2tags = {}
        tagcounts = {}
        branchnum = None
        while 1:
            l = self.__readline()
            while l and not l.startswith('RCS file: '):
                l = self.__readline()

            if not l.startswith('RCS file: '):
                break

            assert self.__currentdir is not None, \
                   "Missed 'cvs rlog: Logging XX' line"

            entry = join(self.__currentdir, split(l[10:-1])[1][:-2])
            if entries is not None:
                while l and not l.startswith('head: '):
                    l = self.__readline()
                assert l, "Missed 'head:' line"
                if branch is None:
                    branchnum = normalize_cvs_rev(l[6:-1])
                    branchnum = rev2branch(branchnum)

                while l and not l == 'symbolic names:\n':
                    l = self.__readline()

                assert l, "Missed 'symbolic names:' line"

                l = self.__readline()
                rev2tags = {}
                while l.startswith('\t'):
                    tag,revision = l[1:-1].split(': ')
                    tagcounts[tag] = tagcounts.get(tag,0) + 1
                    revision = normalize_cvs_rev(revision)
                    rev2tags.setdefault(revision,[]).append(tag)
                    if tag == branch:
                        branchnum = revision

                    l = self.__readline()

                # branchnum may still be None, if this file doesn't exist
                # on the requested branch.

                # filter out branch tags, and tags for revisions that are
                # on other branches.
                for revision in rev2tags.keys():
                    if is_branch(revision) or \
                       not branchnum or \
                       not cvs_revs_same_branch(revision,branchnum):
                        del rev2tags[revision]

                file2rev2tags[entry] = rev2tags

            expected_revisions = None
            while l not in (self.inter_sep, self.intra_sep):
                m = revcount_regex.search(l)
                if m is not None:
                    expected_revisions = int(m.group(1))
                l = self.__readline()
            last = previous = None
            found_revisions = 0
            while (l <> self.inter_sep or
                   not self.__readline(True).startswith('revision ')):
                cs = self.__parseRevision(entry)
                if cs is None:
                    break

                date,author,changelog,e,rev,state,newentry = cs

                # CVS seems to sometimes mess up what it thinks the branch is...
                if branchnum and not cvs_revs_same_branch(normalize_cvs_rev(rev),
                                                          branchnum):
                    self.log.warning("Skipped revision %s on entry %s "
                                     "as revision didn't match branch revision %s "
                                     "for branch %s"
                                     % (str(normalize_cvs_rev(rev)), entry,
                                        str(branchnum), str(branch)))
                    expected_revisions -= 1
                    continue

                if not (previous and state == 'dead' and previous.action_kind == previous.DELETED):
                    # Skip spurious entries added in a branch
                    if not (rev == '1.1' and state == 'dead' and
                            changelog.startswith('file ') and
                            ' was initially added on branch ' in changelog):
                        last = self.__collect(date, author, changelog, e, rev)
                        if state == 'dead':
                            last.action_kind = last.DELETED
                        elif newentry:
                            last.action_kind = last.ADDED
                        else:
                            last.action_kind = last.UPDATED
                    found_revisions = found_revisions + 1

                    if previous and last.action_kind == last.DELETED:
                        # For unknown reasons, sometimes there are two dead
                        # revision is a row.
                        if previous.action_kind <> last.DELETED:
                            previous.action_kind = previous.ADDED

                    previous = last

            if expected_revisions <> found_revisions:
                self.log.warning('Expecting %s revisions, found %s',
                                 expected_revisions, found_revisions)

        # If entries is not given, don't try to desume tags information
        if entries is None:
            return

        # Determine the current revision of each live
        # (i.e. non-deleted) entry.
        state = dict(entries.getFileVersions())

        # before stepping through changes, see if the initial state is
        # taggable.  If so, add an initial changeset that does nothing
        # but tag, using the date of the last revision tailor imported
        # on its previous run.  There's no way to tell when the tag
        # was really applied, so we don't know if it was seen on the
        # last run or not.  Before applying the tag on the other end,
        # we'll have to check whether it's already been applied.
        tags = self.__getApplicableTags(state, file2rev2tags, tagcounts)
        if tags:
            if since == None:
                # I think this could only happen if the CVS repo was
                # tagged before any files were added to it.  We could
                # probably get a better date by looking at when the
                # files were added, but who cares.
                timestamp = datetime(1900,1,1).replace(tzinfo=UTC)
            else:
                # "since" is a revision name read from the state file,
                # which means it was originally generated by
                # getGlobalCVSRevision.  The format string "%Y-%m-%d
                # %H:%M:%S" matches the format generated by the implicit
                # call to timestamp.__str__() in getGlobalCVSRevision.
                y,m,d,hh,mm,ss,d1,d2,d3 = strptime(since, "%Y-%m-%d %H:%M:%S")
                timestamp = datetime(y,m,d,hh,mm,ss,0,UTC)
            author = "unknown tagger"
            changelog = "tag %s %s" % (timestamp, tags)
            key = (timestamp, author, changelog)
            self.changesets[key] = Changeset(_getGlobalCVSRevision(timestamp,
                                                                   author),
                                             timestamp,author,changelog,
                                             tags=tags)

        # Walk through the changesets, identifying ones that result in
        # a state with a tag.  Add that info to the changeset.
        for cs in self.__iter__():
            self.__updateState(state, cs)
            cs.tags = self.__getApplicableTags(state, file2rev2tags, tagcounts)

    def __getApplicableTags(self,state,taginfo,expectedcounts):
        # state:   a dictionary mapping filename->revision
        #
        # taginfo: a two-level dictionary mapping
        #          tagname->revision->list of tags.
        #
        # expectedcounts: a dictionary mapping tagname->number of
        #                 files tagged with that name.
        observedcounts = {}
        possibletags = []
        for filename, revno in state.iteritems():
            filetags = taginfo[filename].get(revno,[])
            if len(possibletags) == 0:
                # first iteration of loop
                possibletags = filetags

            # Intersection of possibletags and filetags.  I'm
            # avoiding using python sets to preserve python 2.3
            # compatibility.
            possibletags = [t for t in possibletags if t in filetags]
            for t in filetags:
                 observedcounts[t] = observedcounts.get(t,0) + 1

            if len(possibletags) == 0:
                break

        # All currently existing files carry the tags in possibletags.
        # But that doesn't mean that the tags correspond to this
        # state--we might need to create additional files before
        # tagging.
        possibletags = [t for t in possibletags if
                        observedcounts[t] == expectedcounts[t]]

        return possibletags

    def __updateState(self,state, changeset):
        for e in changeset.entries:
            if e.action_kind in (e.ADDED, e.UPDATED):
                state[e.name] = normalize_cvs_rev(e.new_revision)
            elif e.action_kind == e.DELETED:
                if state.has_key(e.name):
                    del state[e.name]
            elif e.action_kind == e.RENAMED:
                if state.has_key(e.name):
                    del state[e.old_name]
                state[e.name] = normalize_cvs_rev(e.new_revision)


class CvsWorkingDir(CvspsWorkingDir):
    """
    Reimplement the mechanism used to get a *changeset* view of the
    CVS commits.
    """

    def _getUpstreamChangesets(self, sincerev):
        from os.path import join, exists
        from time import sleep

        from codecs import getreader

        try:
            reader = getreader(self.repository.encoding)
        except (ValueError, LookupError), err:
            raise ConfigurationError('Encoding "%s" does not seem to be '
                                     'allowed on this system (%s): you '
                                     'may override the default with '
                                     'something like "encoding = ascii" in '
                                     'the %s config section' %
                                     (self.repository.encoding, err,
                                      self.repository.name))

        branch = None
        fname = join(self.repository.basedir, 'CVS', 'Tag')
        if exists(fname):
            tag = open(fname).read()
            if tag[0] == 'T':
                branch=tag[1:-1]

        cmd = self.repository.command("-f", "-d", "%(repository)s", "rlog")

        if not sincerev or sincerev in ("INITIAL", "HEAD"):
            # We are bootstrapping, trying to collimate the actual
            # revision on disk with the changesets, or figuring out
            # the first revision
            since = None
            if sincerev == "HEAD":
                if branch and branch<>'HEAD':
                    cmd.append("-r%(branch)s.")
                else:
                    cmd.append("-rHEAD:HEAD")
            else:
                cmd.append("-r:HEAD")
                if not branch:
                    cmd.append("-b")
        elif ' by ' in sincerev:
            since, author = _splitGlobalCVSRevision(sincerev)
            cmd.extend(["-d", "%(since)s UTC<"])
            if branch:
                cmd.append("-r%(branch)s")
            else:
                cmd.append("-b")
        elif sincerev[0] in '0123456789':
            since = sincerev
            cmd.extend(["-d", "%(since)s UTC<"])
        elif ' ' in sincerev:
            branch, since = sincerev.split(' ', 1)
            if since.strip() == 'INITIAL':
                cmd.extend(["-r%(branch)s"])
            else:
                cmd.extend(["-d", "%(since)s UTC<", "-r%(branch)s"])
        else:
            # Then we assume it's a tag
            branch = sincerev
            since = None
            cmd.extend(["-r:%(branch)s"])

        cvslog = ExternalCommand(command=cmd)

        retry = 0
        while True:
            log = cvslog.execute(self.repository.module, stdout=PIPE,
                                 stderr=STDOUT, since=since,
                                 repository=self.repository.repository,
                                 branch=branch or 'HEAD', TZ='UTC0')[0]
            if cvslog.exit_status:
                retry += 1
                if retry>3:
                    break
                delay = 2**retry
                self.log.info("%s returned status %s, "
                              "retrying in %d seconds...",
                              str(cvslog), cvslog.exit_status,
                              delay)
                sleep(retry)
            else:
                break

        if cvslog.exit_status:
            raise GetUpstreamChangesetsFailure(
                "%s returned status %d" % (str(cvslog), cvslog.exit_status))

        log = reader(log, self.repository.encoding_errors_policy)
        return changesets_from_cvslog(log, self.repository.module,
                                      branch,
                                      CvsEntries(self.repository.rootdir),
                                      since,
                                      self.repository.changeset_threshold,
                                      self.repository.trim_module_components)

    def _checkoutUpstreamRevision(self, revision):
        """
        Adjust the 'revision' slot of the changeset, to make it a
        repository wide unique id.
        """

        last = CvspsWorkingDir._checkoutUpstreamRevision(self, revision)
        last.revision = _getGlobalCVSRevision(last.date, last.author)
        return last


class CvsEntry(object):
    """Collect the info about a file in a CVS working dir."""

    __slots__ = ('filename', 'cvs_version', 'timestamp', 'cvs_tag')

    def __init__(self, entry):
        """Initialize a CvsEntry."""

        from datetime import datetime
        from time import strptime

        dummy, fn, rev, ts, dummy, tag = entry.split('/')

        self.filename = fn
        self.cvs_version = rev

        if ts == 'Result of merge':
            self.timestamp = datetime.now(tz=UTC)
        else:
            if ts.startswith('Result of merge+'):
                ts = ts[16:]
            y,m,d,hh,mm,ss,d1,d2,d3 = strptime(ts, "%a %b %d %H:%M:%S %Y")
            self.timestamp = datetime(y,m,d,hh,mm,ss,0,UTC)

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

    def getYoungestEntry(self):
        """Find and return the most recently changed entry."""

        latest = None

        for e in self.files.values():
            if not latest or e.timestamp > latest.timestamp:
                latest = e

        for d in self.directories.values():
            e = d.getYoungestEntry()

            # skip if there are no entries in the directory
            if not e:
                continue

            if not latest or e.timestamp > latest.timestamp:
                latest = e

        return latest

    def getFileVersions(self, prefix=''):
        """Return a set of (entry name, version number) pairs."""

        pairs = [(prefix+e.filename, normalize_cvs_rev(e.cvs_version))
                 for e in self.files.values()]

        for dirname, entries in self.directories.iteritems():
            pairs += [(prefix+filename, version)
                      for filename, version in
                      entries.getFileVersions("%s/" % dirname)]

        return pairs

    def isEmpty(self):
        """Return True is this directory does not contain any subentry."""

        return not self.files and not self.directories
