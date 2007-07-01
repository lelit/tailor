# -*- mode: python; coding: utf-8 -*-
# :Progetto: Tailor -- Darcs peculiarities when used as a source
# :Creato:   lun 10 lug 2006 00:04:59 CEST
# :Autore:   Lele Gaifax <lele@nautilus.homeip.net>
# :Licenza:  GNU General Public License
#

"""
This module contains the source specific bits of the darcs backend.
"""

__docformat__ = 'reStructuredText'

import re

from vcpx.changes import ChangesetEntry, Changeset
from vcpx.shwrap import ExternalCommand, PIPE, STDOUT
from vcpx.source import UpdatableSourceWorkingDir, ChangesetApplicationFailure, \
                        GetUpstreamChangesetsFailure
from vcpx.target import TargetInitializationFailure
from vcpx.tzinfo import UTC


class DarcsChangeset(Changeset):
    """
    Fixup darcs idiosyncrasies:

    - collapse "add A; rename A B" into "add B"
    - collapse "rename A B; remove B" into "remove A"
    """

    def __init__(self, revision, date, author, log, entries=None, **other):
        """
        Initialize a new DarcsChangeset.
        """

        super(DarcsChangeset, self).__init__(revision, date, author, log, entries=None, **other)
        if entries is not None:
            for e in entries:
                self.addEntry(e, revision)

    def addEntry(self, entry, revision):
        """
        Fixup darcs idiosyncrasies:

        - collapse "add A; rename A B" into "add B"
        - annihilate "add A; remove A"
        - collapse "rename A B; remove B" into "remove A"
        """

        # This should not happen, since the parser feeds us an already built
        # list of ChangesetEntries, anyway...
        if not isinstance(entry, ChangesetEntry):
            return super(DarcsChangeset, self).addEntry(entry, revision)

        # Ok, before adding this entry, check it against already
        # known: if this is an add, and there's a rename (such as "add
        # A; rename A B; ") then...

        if entry.action_kind == entry.ADDED:
            # ... we have to check existings, because of a bug in
            # darcs: `changes --xml` (as of 1.0.7) emits the changes
            # in the wrong order, that is, it prefers to start with
            # renames, *always*, even when they obviously follows the
            # add of the same entry (even, it should apply this "fix"
            # by its own).
            #
            # So, if there's a rename of this entry there, change that
            # to an addition instead, and don't insert any other entry

            dirname = entry.name+'/' # darcs hopefully use forward slashes also under win

            for i,e in enumerate(self.entries):
                if e.action_kind == e.RENAMED and e.old_name == entry.name:
                    # Luckily enough (since removes are the first entries
                    # in the list, that is) by anticipating the add we
                    # cure also the case below, when addition follows
                    # edit.
                    e.action_kind = e.ADDED
                    e.old_name = None
                    return e

                # Assert also that add_dir events must preceeds any
                # add_file and ren_file that have that dir as target,
                # and that add_file preceeds any edit.

                if ((e.name == entry.name or e.name.startswith(dirname))
                    or (e.action_kind == e.RENAMED and e.old_name.startswith(dirname))):
                    self.entries.insert(i, entry)
                    return entry

        # Likewise, if this is a deletion, and there is a rename of
        # this entry (such as "rename A B; remove B") then turn the
        # existing rename into a deletion instead.

        # If instead the removed entry was added by the same patch,
        # annihilate the two: a bug in darcs (possibly fixed in recent
        # versions) created patches with ADD+EDIT+REMOVE of a single
        # file (see tailor ticket #71, or darcs issue185). Too bad
        # another bug (still present in 1.0.8) hides that and makes
        # very hard (read: impossible) any workaround on the tailor
        # side. Luckily I learnt another tiny bit of Haskell and
        # proposed a fix for that: hopefully the patch will be
        # accepted by darcs developers. In the meantime, I attached it
        # to ticket #71: without that, tailor does not have enough
        # information to do the right thing.

        elif entry.action_kind == entry.DELETED:
            for i,e in enumerate(self.entries):
                if e.action_kind == e.RENAMED and e.name == entry.name:
                    e.action_kind = e.DELETED
                    e.name = e.old_name
                    e.old_name = None
                    return e
                elif e.action_kind == e.ADDED and e.name == entry.name:
                    del self.entries[i]
                    return None

        # Ok, it must be either an edit or a rename: the former goes
        # obviously to the end, and since the latter, as said, come
        # in very early, appending is just good.
        self.entries.append(entry)
        return entry


def changesets_from_darcschanges(changes, unidiff=False, repodir=None,
                                 chunksize=2**15, replace_badchars=None):
    """
    Parse XML output of ``darcs changes``.

    Return a list of ``Changeset`` instances.

    Filters out the (currently incorrect) tag info from
    changesets_from_darcschanges_unsafe.
    """

    csets = changesets_from_darcschanges_unsafe(changes, unidiff,
                                                repodir, chunksize,
                                                replace_badchars)
    for cs in csets:
        yield cs

def changesets_from_darcschanges_unsafe(changes, unidiff=False, repodir=None,
                                        chunksize=2**15, replace_badchars=None):
    """
    Do the real work of parsing the change log, including tags.
    Warning: the tag information in the changsets returned by this
    function are only correct if each darcs tag in the repo depends on
    all of the patches that precede it.  This is not a valid
    assumption in general--a tag that does not depend on patch P can
    be pulled in from another darcs repo after P.  We collect the tag
    info anyway because DarcsWorkingDir._currentTags() can use it
    safely despite this problem.  Hopefully the problem will
    eventually be fixed and this function can be renamed
    changesets_from_darcschanges.
    """
    from xml.sax import make_parser
    from xml.sax.handler import ContentHandler, ErrorHandler
    from datetime import datetime

    class DarcsXMLChangesHandler(ContentHandler):
        def __init__(self):
            self.changesets = []
            self.current = None
            self.current_field = []
            if unidiff and repodir:
                cmd = ["darcs", "diff", "--unified", "--repodir", repodir,
                       "--patch", "%(patchname)s"]
                self.darcsdiff = ExternalCommand(command=cmd)
            else:
                self.darcsdiff = None

        def startElement(self, name, attributes):
            if name == 'patch':
                self.current = {}
                self.current['author'] = attributes['author']
                date = attributes['date']
                from time import strptime
                try:
                    # 20040619130027
                    timestamp = datetime(*strptime(date, '%Y%m%d%H%M%S')[:6])
                except ValueError:
                    # Old darcs patches use the form Sun Oct 20 20:01:05 EDT 2002
                    timestamp = datetime(*strptime(date[:19] + date[-5:], '%a %b %d %H:%M:%S %Y')[:6])

                timestamp = timestamp.replace(tzinfo=UTC) # not true for the ValueError case, but oh well

                self.current['date'] = timestamp
                self.current['comment'] = ''
                self.current['hash'] = attributes['hash']
                self.current['entries'] = []
            elif name in ['name', 'comment', 'add_file', 'add_directory',
                          'modify_file', 'remove_file', 'remove_directory']:
                self.current_field = []
            elif name == 'move':
                self.old_name = attributes['from']
                self.new_name = attributes['to']

        def endElement(self, name):
            if name == 'patch':
                cset = DarcsChangeset(self.current['name'],
                                      self.current['date'],
                                      self.current['author'],
                                      self.current['comment'],
                                      self.current['entries'],
                                      tags=self.current.get('tags',[]))
                cset.darcs_hash = self.current['hash']
                if self.darcsdiff:
                    cset.unidiff = self.darcsdiff.execute(TZ='UTC',
                        stdout=PIPE, patchname=cset.revision)[0].read()

                self.changesets.append(cset)
                self.current = None
            elif name in ['name', 'comment']:
                val = ''.join(self.current_field)
                if val[:4] == 'TAG ':
                    self.current.setdefault('tags',[]).append(val[4:])
                self.current[name] = val
            elif name == 'move':
                entry = ChangesetEntry(self.new_name)
                entry.action_kind = entry.RENAMED
                entry.old_name = self.old_name
                self.current['entries'].append(entry)
            elif name in ['add_file', 'add_directory', 'modify_file',
                          'remove_file', 'remove_directory']:
                entry = ChangesetEntry(''.join(self.current_field).strip())
                entry.action_kind = { 'add_file': entry.ADDED,
                                      'add_directory': entry.ADDED,
                                      'modify_file': entry.UPDATED,
                                      'remove_file': entry.DELETED,
                                      'remove_directory': entry.DELETED
                                    }[name]

                self.current['entries'].append(entry)

        def characters(self, data):
            self.current_field.append(data)

    parser = make_parser()
    handler = DarcsXMLChangesHandler()
    parser.setContentHandler(handler)
    parser.setErrorHandler(ErrorHandler())

    def fixup_badchars(s, map):
        if not map:
            return s

        ret = [map.get(c, c) for c in s]
        return "".join(ret)

    chunk = fixup_badchars(changes.read(chunksize), replace_badchars)
    while chunk:
        parser.feed(chunk)
        for cs in handler.changesets:
            yield cs
        handler.changesets = []
        chunk = fixup_badchars(changes.read(chunksize), replace_badchars)
    parser.close()
    for cs in handler.changesets:
        yield cs


class DarcsSourceWorkingDir(UpdatableSourceWorkingDir):
    """
    A source working directory under ``darcs``.
    """

    is_hash_rx = re.compile('[0-9a-f]{14}-[0-9a-f]{5}-[0-9a-f]{40}\.gz')

    def _getUpstreamChangesets(self, sincerev):
        """
        Do the actual work of fetching the upstream changeset.
        """

        cmd = self.repository.command("pull", "--dry-run")
        pull = ExternalCommand(cwd=self.repository.basedir, command=cmd)
        output = pull.execute(self.repository.repository,
                              stdout=PIPE, stderr=STDOUT, TZ='UTC0')[0]

        if pull.exit_status:
            raise GetUpstreamChangesetsFailure(
                "%s returned status %d saying\n%s" %
                (str(pull), pull.exit_status, output.read()))

        return self._parseDarcsPull(output)


    def _parseDarcsPull(self, output):
        """Process 'darcs pull' output to Changesets.
        """
        from datetime import datetime
        from time import strptime
        from sha import new
        from vcpx.changes import Changeset

        l = output.readline()
        while l and not (l.startswith('Would pull the following changes:') or
                         l == 'No remote changes to pull in!\n'):
            l = output.readline()

        if l <> 'No remote changes to pull in!\n':
            ## Sat Jul 17 01:22:08 CEST 2004  lele@nautilus
            ##   * Refix _getUpstreamChangesets for darcs

            fsep = re.compile('[ :]+')
            l = output.readline()
            while not l.startswith('Making no changes:  this is a dry run.'):
                # Assume it's a line like
                #    Sun Jan  2 00:24:04 UTC 2005  lele@nautilus.homeip.net
                # Use a regular expression matching multiple spaces or colons
                # to split it, and use the first 7 fields to build up a datetime.
                pieces = fsep.split(l.rstrip(), 8)
                assert len(pieces)>=7, "Cannot parse %r as a patch timestamp" % l
                date = ' '.join(pieces[:8])
                author = pieces[8]
                y,m,d,hh,mm,ss,d1,d2,d3 = strptime(date, "%a %b %d %H %M %S %Z %Y")
                date = datetime(y,m,d,hh,mm,ss,0,UTC)
                l = output.readline().rstrip()
                assert (l.startswith('  *') or
                        l.startswith('  UNDO:') or
                        l.startswith('  tagged')), \
                        "Got %r but expected the start of the log" % l

                if l.startswith('  *'):
                    name = l[4:]
                else:
                    name = l[2:]

                changelog = []
                l = output.readline()
                while l.startswith('  '):
                    changelog.append(l[2:-1])
                    l = output.readline()

                cset = Changeset(name, date, author, '\n'.join(changelog))
                compactdate = date.strftime("%Y%m%d%H%M%S")
                if name.startswith('UNDO: '):
                    name = name[6:]
                    inverted = 't'
                else:
                    inverted = 'f'

                if name.startswith('tagged '):
                    name = name[7:]
                    if cset.tags is None:
                        cset.tags = [name]
                    else:
                        cset.tags.append(name)
                    name = "TAG " + name

                phash = new()
                phash.update(name)
                phash.update(author)
                phash.update(compactdate)
                phash.update(''.join(changelog))
                phash.update(inverted)
                cset.darcs_hash = '%s-%s-%s.gz' % (compactdate,
                                                   new(author).hexdigest()[:5],
                                                   phash.hexdigest())


                yield cset

                while not l.strip():
                    l = output.readline()

    def _applyChangeset(self, changeset):
        """
        Do the actual work of applying the changeset to the working copy.
        """

        needspatchesopt = False
        if hasattr(changeset, 'darcs_hash'):
            selector = '--match'
            revtag = 'hash ' + changeset.darcs_hash
        elif changeset.revision.startswith('tagged '):
            selector = '--tag'
            revtag = changeset.revision[7:]
        else:
            selector = '--match'
            revtag = 'date "%s" && author "%s"' % (
                changeset.date.strftime("%Y%m%d%H%M%S"),
                changeset.author)
            # The 'exact' matcher doesn't groke double quotes:
            # """currently there is no provision for escaping a double
            # quote, so you have to choose between matching double
            # quotes and matching spaces"""
            if not '"' in changeset.revision:
                revtag += ' && exact "%s"' % changeset.revision.replace('%', '%%')
            else:
                needspatchesopt = True

        cmd = self.repository.command("pull", "--all", "--quiet",
                                      selector, revtag)

        if needspatchesopt:
            cmd.extend(['--patches', re.escape(changeset.revision)])

        pull = ExternalCommand(cwd=self.repository.basedir, command=cmd)
        output = pull.execute(stdout=PIPE, stderr=STDOUT, input='y')[0]

        if pull.exit_status:
            raise ChangesetApplicationFailure(
                "%s returned status %d saying\n%s" %
                (str(pull), pull.exit_status, output.read()))

        conflicts = []
        line = output.readline()
        while line:
            if line.startswith('We have conflicts in the following files:'):
                files = output.readline()[:-1].split(' ')
                self.log.warning("Conflict after 'darcs pull': %s",
                                 ' '.join(files))
                conflicts.extend(files)
            line = output.readline()

        cmd = self.repository.command("changes", selector, revtag,
                                      "--xml-output", "--summ")
        changes = ExternalCommand(cwd=self.repository.basedir, command=cmd)
        last = changesets_from_darcschanges(changes.execute(stdout=PIPE)[0],
                                            replace_badchars=self.repository.replace_badchars)
        try:
            changeset.entries.extend(last.next().entries)
        except StopIteration:
            pass

        return conflicts

    def _handleConflict(self, changeset, conflicts, conflict):
        """
        Handle the conflict raised by the application of the upstream changeset.

        Override parent behaviour: with darcs, we need to execute a revert
        on the conflicted files, **trashing** local changes, but there should
        be none of them in tailor context.
        """

        self.log.info("Reverting changes to %s, to solve the conflict",
                      ' '.join(conflict))
        cmd = self.repository.command("revert", "--all")
        revert = ExternalCommand(cwd=self.repository.basedir, command=cmd)
        revert.execute(conflict)

    def _checkoutUpstreamRevision(self, revision):
        """
        Concretely do the checkout of the upstream revision and return
        the last applied changeset.
        """

        from os.path import join, exists
        from os import mkdir
        from vcpx.source import InvocationError

        if not self.repository.repository:
            raise InvocationError("Must specify a the darcs source repository")

        if revision == 'INITIAL' or self.is_hash_rx.match(revision):
            initial = True

            if revision == 'INITIAL':
                cmd = self.repository.command("changes", "--xml-output",
                                              "--repo", self.repository.repository,
                                               "--reverse")
                changes = ExternalCommand(command=cmd)
                output = changes.execute(stdout=PIPE, stderr=STDOUT)[0]

                if changes.exit_status:
                    raise ChangesetApplicationFailure(
                        "%s returned status %d saying\n%s" %
                        (str(changes), changes.exit_status,
                         output and output.read() or ''))

                csets = changesets_from_darcschanges(output, replace_badchars=self.repository.replace_badchars)
                changeset = csets.next()

                revision = 'hash %s' % changeset.darcs_hash
            else:
                revision = 'hash %s' % revision
        else:
            initial = False

        if self.repository.subdir == '.' or exists(self.repository.basedir):
            # This is currently *very* slow, compared to the darcs get
            # below!
            if not exists(join(self.repository.basedir, '_darcs')):
                if not exists(self.repository.basedir):
                    mkdir(self.repository.basedir)

                cmd = self.repository.command("initialize")
                init = ExternalCommand(cwd=self.repository.basedir, command=cmd)
                init.execute()

                if init.exit_status:
                    raise TargetInitializationFailure(
                        "%s returned status %s" % (str(init),
                                                   init.exit_status))

                cmd = self.repository.command("pull", "--all", "--quiet")
                if revision and revision<>'HEAD':
                    cmd.extend([initial and "--match" or "--tag", revision])
                dpull = ExternalCommand(cwd=self.repository.basedir, command=cmd)
                output = dpull.execute(self.repository.repository,
                                       stdout=PIPE, stderr=STDOUT)[0]

                if dpull.exit_status:
                    raise TargetInitializationFailure(
                        "%s returned status %d saying\n%s" %
                        (str(dpull), dpull.exit_status, output.read()))
        else:
            # Use much faster 'darcs get'
            cmd = self.repository.command("get", "--quiet")
            if revision and revision<>'HEAD':
                cmd.extend([initial and "--to-match" or "--tag", revision])
            else:
                cmd.append("--partial")
            dget = ExternalCommand(command=cmd)
            output = dget.execute(self.repository.repository, self.repository.basedir,
                                  stdout=PIPE, stderr=STDOUT)[0]

            if dget.exit_status:
                raise TargetInitializationFailure(
                    "%s returned status %d saying\n%s" %
                    (str(dget), dget.exit_status, output.read()))

        cmd = self.repository.command("changes", "--last", "1",
                                      "--xml-output")
        changes = ExternalCommand(cwd=self.repository.basedir, command=cmd)
        output = changes.execute(stdout=PIPE, stderr=STDOUT)[0]

        if changes.exit_status:
            raise ChangesetApplicationFailure(
                "%s returned status %d saying\n%s" %
                (str(changes), changes.exit_status, output.read()))

        last = changesets_from_darcschanges(output, replace_badchars=self.repository.replace_badchars)

        return last.next()
