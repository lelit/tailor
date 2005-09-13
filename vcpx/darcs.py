# -*- mode: python; coding: utf-8 -*-
# :Progetto: vcpx -- Darcs details
# :Creato:   ven 18 giu 2004 14:45:28 CEST
# :Autore:   Lele Gaifax <lele@nautilus.homeip.net>
# :Licenza:  GNU General Public License
#

"""
This module contains supporting classes for the ``darcs`` versioning system.
"""

__docformat__ = 'reStructuredText'

from shwrap import ExternalCommand, PIPE, STDOUT
from source import UpdatableSourceWorkingDir, ChangesetApplicationFailure, \
     GetUpstreamChangesetsFailure
from target import SyncronizableTargetWorkingDir, TargetInitializationFailure
from xml.sax import SAXException

MOTD = """\
Tailorized equivalent of
%s
"""

def changesets_from_darcschanges(changes, unidiff=False, repodir=None):
    """
    Parse XML output of ``darcs changes``.

    Return a list of ``Changeset`` instances.
    """

    from xml.sax import parse
    from xml.sax.handler import ContentHandler
    from changes import ChangesetEntry, Changeset
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
                # 20040619130027
                y = int(date[:4])
                m = int(date[4:6])
                d = int(date[6:8])
                hh = int(date[8:10])
                mm = int(date[10:12])
                ss = int(date[12:14])
                timestamp = datetime(y, m, d, hh, mm, ss)
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
                # Sort the paths to make tests easier
                self.current['entries'].sort(lambda x,y: cmp(x.name, y.name))
                name = self.current['name']
                log = self.current['comment']
                if log:
                    changelog = name + '\n' + log
                else:
                    changelog = name
                cset = Changeset(name,
                                 self.current['date'],
                                 self.current['author'],
                                 changelog,
                                 self.current['entries'])
                cset.darcs_hash = self.current['hash']
                if self.darcsdiff:
                    cset.unidiff = self.darcsdiff.execute(
                        stdout=PIPE, patchname=cset.revision)[0].read()

                self.changesets.append(cset)
                self.current = None
            elif name in ['name', 'comment']:
                self.current[name] = ''.join(self.current_field)
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


    handler = DarcsXMLChangesHandler()
    parse(changes, handler)
    changesets = handler.changesets

    # sort changeset by date
    changesets.sort(lambda x, y: cmp(x.date, y.date))

    return changesets


class DarcsWorkingDir(UpdatableSourceWorkingDir,SyncronizableTargetWorkingDir):
    """
    A working directory under ``darcs``.
    """

    ## UpdatableSourceWorkingDir

    def _getUpstreamChangesets(self, sincerev):
        """
        Do the actual work of fetching the upstream changeset.
        """

        from datetime import datetime
        from time import strptime
        from changes import Changeset
        from sha import new

        cmd = self.repository.command("pull", "--dry-run")
        pull = ExternalCommand(cwd=self.basedir, command=cmd)
        output = pull.execute(self.repository.repository,
                              stdout=PIPE, stderr=STDOUT, TZ='UTC')[0]

        if pull.exit_status:
            raise GetUpstreamChangesetsFailure(
                "%s returned status %d saying \"%s\"" %
                (str(pull), pull.exit_status, output.read()))

        l = output.readline()
        while l and not (l.startswith('Would pull the following changes:') or
                         l == 'No remote changes to pull in!\n'):
            l = output.readline()

        changesets = []

        if l <> 'No remote changes to pull in!\n':
            ## Sat Jul 17 01:22:08 CEST 2004  lele@nautilus
            ##   * Refix _getUpstreamChangesets for darcs

            l = output.readline()
            while not l.startswith('Making no changes:  this is a dry run.'):
                # Assume it's a line like
                #    Sun Jan  2 00:24:04 UTC 2005  lele@nautilus.homeip.net
                # we used to split on the double space before the email,
                # but in this case this is wrong. Waiting for xml output,
                # is it really sane asserting date's length to 28 chars?
                date = l[:28]
                author = l[30:-1]
                y,m,d,hh,mm,ss,d1,d2,d3 = strptime(date, "%a %b %d %H:%M:%S %Z %Y")
                date = datetime(y,m,d,hh,mm,ss)
                l = output.readline()
                assert (l.startswith('  * ') or
                        l.startswith('  UNDO:') or
                        l.startswith('  tagged'))

                if l.startswith('  *'):
                    name = l[4:-1]
                else:
                    name = l[2:-1]

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
                phash = new()
                phash.update(name)
                phash.update(author)
                phash.update(compactdate)
                phash.update(''.join(changelog))
                phash.update(inverted)
                cset.darcs_hash = '%s-%s-%s.gz' % (compactdate,
                                                   new(author).hexdigest()[:5],
                                                   phash.hexdigest())
                changesets.append(cset)

                while not l.strip():
                    l = output.readline()

        return changesets

    def _applyChangeset(self, changeset):
        """
        Do the actual work of applying the changeset to the working copy.
        """

        from re import escape

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
            cmd.extend(['--patches', escape(changeset.revision)])

        pull = ExternalCommand(cwd=self.basedir, command=cmd)
        output = pull.execute(stdout=PIPE, stderr=STDOUT)[0]

        if pull.exit_status:
            raise ChangesetApplicationFailure(
                "%s returned status %d saying \"%s\"" %
                (str(pull), pull.exit_status, output.read()))

        conflicts = []
        line = output.readline()
        while line:
            if line.startswith('We have conflicts in the following files:'):
                files = output.readline()[:-1].split('./')[1:]
                self.log_info("Conflict after 'darcs pull': '%s'" %
                              ' '.join(files))
                conflicts.extend(['./' + f for f in files])
            line = output.readline()

        cmd = self.repository.command("changes", selector, revtag,
                                      "--xml-output", "--summ")
        changes = ExternalCommand(cwd=self.basedir, command=cmd)
        last = changesets_from_darcschanges(changes.execute(stdout=PIPE)[0])
        if last:
            changeset.entries.extend(last[0].entries)

        return conflicts

    def _handleConflict(self, changeset, conflicts, conflict):
        """
        Handle the conflict raised by the application of the upstream changeset.

        Override parent behaviour: with darcs, we need to execute a revert
        on the conflicted files, **trashing** local changes, but there should
        be none of them in tailor context.
        """

        self.log_info("Reverting changes to '%s', to solve the conflict" %
                      ' '.join(conflict))
        cmd = self.repository.command("revert", "--all")
        revert = ExternalCommand(cwd=self.basedir, command=cmd)
        revert.execute(conflict)

    def _checkoutUpstreamRevision(self, revision):
        """
        Concretely do the checkout of the upstream revision and return
        the last applied changeset.
        """

        from os.path import join, exists
        from os import mkdir
        from re import escape

        if revision == 'INITIAL':
            initial = True
            cmd = self.repository.command("changes", "--xml-output",
                                          "--repo", self.repository.repository)
            changes = ExternalCommand(command=cmd)
            output = changes.execute(stdout=PIPE, stderr=STDOUT)[0]

            if changes.exit_status:
                raise ChangesetApplicationFailure(
                    "%s returned status %d saying \"%s\"" %
                    (str(changes), changes.exit_status,
                     output and output.read() or ''))

            csets = changesets_from_darcschanges(output)
            changeset = csets[0]

            revision = 'hash %s' % changeset.darcs_hash
        else:
            initial = False

        if self.repository.subdir == '.':
            # This is currently *very* slow, compared to the darcs get
            # below!
            if not exists(join(self.basedir, '_darcs')):
                if not exists(self.basedir):
                    mkdir(self.basedir)

                cmd = self.repository.command("initialize")
                init = ExternalCommand(cwd=self.basedir, command=cmd)
                init.execute()

                if init.exit_status:
                    raise TargetInitializationFailure(
                        "%s returned status %s" % (str(init),
                                                   init.exit_status))

                cmd = self.repository.command("pull", "--all", "--quiet")
                if revision and revision<>'HEAD':
                    cmd.extend([initial and "--match" or "--tag", revision])
                dpull = ExternalCommand(cwd=self.basedir, command=cmd)
                output = dpull.execute(self.repository.repository,
                                       stdout=PIPE, stderr=STDOUT)[0]

                if dpull.exit_status:
                    raise TargetInitializationFailure(
                        "%s returned status %d saying \"%s\"" %
                        (str(dpull), dpull.exit_status, output.read()))
        else:
            # Use much faster 'darcs get'
            cmd = self.repository.command("get", "--quiet")
            if revision and revision<>'HEAD':
                cmd.extend([initial and "--to-match" or "--tag", revision])
            else:
                cmd.append("--partial")
            dget = ExternalCommand(command=cmd)
            output = dget.execute(self.repository.repository, self.basedir,
                                  stdout=PIPE, stderr=STDOUT)[0]

            if dget.exit_status:
                raise TargetInitializationFailure(
                    "%s returned status %d saying \"%s\"" %
                    (str(dget), dget.exit_status, output.read()))

        cmd = self.repository.command("changes", "--last", "1",
                                      "--xml-output")
        changes = ExternalCommand(cwd=self.basedir, command=cmd)
        output = changes.execute(stdout=PIPE, stderr=STDOUT)[0]

        if changes.exit_status:
            raise ChangesetApplicationFailure(
                "%s returned status %d saying \"%s\"" %
                (str(changes), changes.exit_status, output.read()))

        last = changesets_from_darcschanges(output)

        return last[0]


    ## SyncronizableTargetWorkingDir

    def _addPathnames(self, names):
        """
        Add some new filesystems objects.
        """

        cmd = self.repository.command("add", "--case-ok", "--not-recursive",
                                      "--quiet")
        ExternalCommand(cwd=self.basedir, command=cmd).execute(names)

    def _addSubtree(self, subdir):
        """
        Use the --recursive variant of ``darcs add`` to add a subtree.
        """

        cmd = self.repository.command("add", "--case-ok", "--recursive",
                                      "--quiet")
        ExternalCommand(cwd=self.basedir, command=cmd).execute(subdir)

    def _commit(self, date, author, patchname, changelog=None, entries=None):
        """
        Commit the changeset.
        """

        from sys import getdefaultencoding

        logmessage = []

        logmessage.append(date.strftime('%Y/%m/%d %H:%M:%S UTC'))
        logmessage.append(author)
        if patchname:
            logmessage.append(patchname)
        if changelog:
            logmessage.append(changelog)
        if not patchname and not changelog:
            logmessage.append('Unnamed patch')

        cmd = self.repository.command("record", "--all", "--pipe")
        if not entries:
            entries = ['.']

        record = ExternalCommand(cwd=self.basedir, command=cmd)
        record.execute(entries, input='\n'.join(logmessage))

        if record.exit_status:
            raise ChangesetApplicationFailure(
                "%s returned status %d" % (str(record), record.exit_status))

    def _removePathnames(self, names):
        """
        Remove some filesystem object.
        """

        from os.path import join, exists

        # darcs raises status 512 when it does not finding the entry,
        # removed by source. Since sometime a directory is left there
        # because it's not empty, darcs fails. So, do an explicit
        # remove on items that are still there.

        c = ExternalCommand(cwd=self.basedir,
                            command=self.repository.command("remove"))
        c.execute([n for n in names if exists(join(self.basedir, n))])


    def _renamePathname(self, oldname, newname):
        """
        Rename a filesystem object.
        """

        from os.path import join, exists
        from os import rename

        # Check to see if the oldentry is still there. If it is,
        # that probably means one thing: it's been moved and then
        # replaced, see svn 'R' event. In this case, rename the
        # existing old entry to something else to trick "darcs mv"
        # (that will assume the move was already done manually) and
        # finally restore its name.

        absold = join(self.basedir, oldname)
        renamed = exists(absold)
        if renamed:
            rename(absold, absold + '-TAILOR-HACKED-TEMP-NAME')

        try:
            cmd = self.repository.command("mv")
            ExternalCommand(cwd=self.basedir, command=cmd).execute(oldname,
                                                                   newname)
        finally:
            if renamed:
                rename(absold + '-TAILOR-HACKED-TEMP-NAME', absold)

    def _prepareTargetRepository(self):
        """
        Create the base directory if it doesn't exist, and execute
        ``darcs initialize`` if needed.
        """

        from os.path import join, exists
        from re import escape, compile
        from dualwd import IGNORED_METADIRS

        if not exists(join(self.basedir, self.repository.METADIR)):
            cmd = self.repository.command("initialize")
            init = ExternalCommand(cwd=self.basedir, command=cmd)
            init.execute()

            if init.exit_status:
                raise TargetInitializationFailure(
                    "%s returned status %s" % (str(init), init.exit_status))

            boring = open(join(self.basedir, '_darcs/prefs/boring'), 'rU')
            ignored = boring.read().split('\n')
            boring.close()

            # Augment the boring file, that contains a regexp per line
            # with all known VCs metadirs to be skipped.
            ignored.extend(['(^|/)%s($|/)' % escape(md)
                            for md in IGNORED_METADIRS])

            # Eventually omit our own log...
            logfile = self.repository.project.logfile
            if logfile.startswith(self.basedir):
                ignored.append('^%s$' %
                               escape(logfile[len(self.basedir)+1:]))

            # ... and state file
            sfname = self.repository.project.state_file.filename
            if sfname.startswith(self.basedir):
                sfrelname = sfname[len(self.basedir)+1:]
                ignored.append('^%s$' % escape(sfrelname))
                ignored.append('^%s$' % escape(sfrelname+'.journal'))

            boring = open(join(self.basedir, '_darcs/prefs/boring'), 'wU')
            boring.write('\n'.join(ignored))
            boring.close()
        else:
            boring = open(join(self.basedir, '_darcs/prefs/boring'), 'rU')
            ignored = boring.read().split('\n')
            boring.close()

        # Build a list of compiled regular expressions, that will be
        # used later to filter the entries.
        self.__unwanted_entries = [compile(rx) for rx in ignored
                                   if rx and not rx.startswith('#')]

    def _prepareWorkingDirectory(self, source_repo):
        """
        Tweak the default settings of the repository.
        """

        from os.path import join

        motd = open(join(self.basedir, '_darcs/prefs/motd'), 'w')
        motd.write(MOTD % str(source_repo))
        motd.close()

    def _adaptEntries(self, changeset):
        """
        Filter out boring files.
        """

        from copy import copy

        adapted = SyncronizableTargetWorkingDir._adaptEntries(self, changeset)

        # If there are no entries or no rules, there's nothing to do
        if not adapted or not adapted.entries or not self.__unwanted_entries:
            return adapted

        entries = []
        skipped = False
        for e in adapted.entries:
            skip = False
            for rx in self.__unwanted_entries:
                if rx.search(e.name):
                    skip = True
                    break
            if skip:
                self.log_info('Entry %r skipped per boring rules' %
                              e.name)
                skipped = True
            else:
                entries.append(e)

        # All entries are gone, don't commit this changeset
        if not entries:
            self.log_info('All entries ignored, skipping whole '
                          'changeset %r' % changeset.revision)
            return None

        if skipped:
            adapted = copy(adapted)
            adapted.entries = entries

        return adapted
