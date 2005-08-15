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
This is the Darcs equivalent of
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

                if self.darcsdiff:
                    cset.unidiff = self.darcsdiff.execute(
                        stdout=PIPE, patchname=cset.revision).read()

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

        cmd = [self.repository.DARCS_CMD, "pull", "--dry-run"]
        pull = ExternalCommand(cwd=self.basedir, command=cmd)
        output = pull.execute(self.repository.repository,
                              stdout=PIPE, stderr=STDOUT, TZ='UTC')

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
                while l.startswith(' '):
                    changelog.append(l.strip())
                    l = output.readline()

                changesets.append(Changeset(name, date, author, '\n'.join(changelog)))

                while not l.strip():
                    l = output.readline()

        return changesets

    def _applyChangeset(self, changeset):
        """
        Do the actual work of applying the changeset to the working copy.
        """

        from re import escape

        if changeset.revision.startswith('tagged '):
            selector = '--tags'
            revtag = changeset.revision[7:]
        else:
            selector = '--match'
            revtag = 'date "%s" && author "%s" && exact "%s"' % (
                changeset.date.strftime("%a %b %d %H:%M:%S UTC %Y"),
                changeset.author,
                changeset.revision)

        cmd = [self.repository.DARCS_CMD, "pull", "--all", selector, revtag]
        pull = ExternalCommand(cwd=self.basedir, command=cmd)
        output = pull.execute(stdout=PIPE, stderr=STDOUT)

        if pull.exit_status:
            raise ChangesetApplicationFailure(
                "%s returned status %d saying \"%s\"" %
                (str(pull), pull.exit_status, output.read()))

        cmd = [self.repository.DARCS_CMD, "changes", selector, revtag,
               "--xml-output", "--summ"]
        changes = ExternalCommand(cwd=self.basedir, command=cmd)
        last = changesets_from_darcschanges(changes.execute(stdout=PIPE))
        if last:
            changeset.entries.extend(last[0].entries)

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
            cmd = [self.repository.DARCS_CMD, "changes", "--xml-output",
                   "--repo", self.repository.repository]
            changes = ExternalCommand(command=cmd)
            output = changes.execute(stdout=PIPE, stderr=STDOUT)

            if changes.exit_status:
                raise ChangesetApplicationFailure(
                    "%s returned status %d saying \"%s\"" %
                    (str(changes), changes.exit_status,
                     output and output.read() or ''))

            csets = changesets_from_darcschanges(output)
            changeset = csets[0]
            revision = 'date "%s" && author "%s" && exact "%s"' % (
                changeset.date.strftime("%a %b %d %H:%M:%S UTC %Y"),
                changeset.author,
                changeset.revision)
        else:
            initial = False

        if self.repository.subdir == '.':
            # This is currently *very* slow, compared to the darcs get
            # below!
            if not exists(join(self.basedir, '_darcs')):
                if not exists(self.basedir):
                    mkdir(self.basedir)

                init = ExternalCommand(cwd=self.basedir,
                                       command=[self.repository.DARCS_CMD,
                                                "initialize"])
                init.execute()

                if init.exit_status:
                    raise TargetInitializationFailure(
                        "%s returned status %s" % (str(init),
                                                   init.exit_status))

                cmd = [self.repository.DARCS_CMD, "pull", "--all", "--verbose"]
                if revision and revision<>'HEAD':
                    cmd.extend([initial and "--match" or "--tag", revision])
                dpull = ExternalCommand(cwd=self.basedir, command=cmd)
                output = dpull.execute(self.repository.repository,
                                       stdout=PIPE, stderr=STDOUT)

                if dpull.exit_status:
                    raise TargetInitializationFailure(
                        "%s returned status %d saying \"%s\"" %
                        (str(dpull), dpull.exit_status, output.read()))
        else:
            # Use much faster 'darcs get'
            cmd = [self.repository.DARCS_CMD, "get", "--partial", "--verbose"]
            if revision and revision<>'HEAD':
                cmd.extend([initial and "--to-patch" or "--tag", revision])
            dget = ExternalCommand(command=cmd)
            output = dget.execute(self.repository.repository, self.basedir,
                                  stdout=PIPE, stderr=STDOUT)

            if dget.exit_status:
                raise TargetInitializationFailure(
                    "%s returned status %d saying \"%s\"" %
                    (str(dget), dget.exit_status, output.read()))

        cmd = [self.repository.DARCS_CMD, "changes", "--last", "1",
               "--xml-output"]
        changes = ExternalCommand(cwd=self.basedir, command=cmd)
        output = changes.execute(stdout=PIPE, stderr=STDOUT)

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

        cmd = [self.repository.DARCS_CMD, "add", "--case-ok",
               "--not-recursive", "--quiet"]
        ExternalCommand(cwd=self.basedir, command=cmd).execute(names)

    def _addSubtree(self, subdir):
        """
        Use the --recursive variant of ``darcs add`` to add a subtree.
        """

        cmd = [self.repository.DARCS_CMD, "add", "--case-ok", "--recursive",
               "--quiet"]
        ExternalCommand(cwd=self.basedir, command=cmd).execute(subdir)

    def _commit(self, date, author, patchname, changelog=None, entries=None):
        """
        Commit the changeset.
        """

        from sys import getdefaultencoding

        encoding = ExternalCommand.FORCE_ENCODING or getdefaultencoding()

        logmessage = []

        logmessage.append(date.strftime('%Y/%m/%d %H:%M:%S UTC'))
        logmessage.append(author.encode(encoding))
        logmessage.append(patchname and patchname.encode(encoding) or 'Unnamed patch')
        logmessage.append(changelog and changelog.encode(encoding) or '')
        logmessage.append('')

        cmd = [self.repository.DARCS_CMD, "record", "--all", "--pipe"]
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

        # Since the source VCS already deleted the entry, and given that
        # darcs will do the right thing with it, do nothing here, instead
        # of
        #         c = ExternalCommand(cwd=self.basedir,
        #                             command=[self.repository.DARCS_CMD,
        #                                      "remove"])
        #         c.execute(entries)
        # that raises status 512 on darcs not finding the entry.

        pass

    def _renamePathname(self, oldname, newname):
        """
        Rename a filesystem object.
        """

        from os.path import join, exists
        from os import rename

        # Check to see if the oldentry is still there. If it does,
        # that probably means one thing: it's been moved and then
        # replaced, see svn 'R' event. In this case, rename the
        # existing old entry to something else to trick "darcs mv"
        # (that will assume the move was already done manually) and
        # finally restore its name.

        renamed = exists(join(self.basedir, oldname))
        if renamed:
            rename(oldname, oldname + '-TAILOR-HACKED-TEMP-NAME')

        try:
            cmd = [self.repository.DARCS_CMD, "mv"]
            ExternalCommand(cwd=self.basedir, command=cmd).execute(oldname,
                                                                   newname)
        finally:
            if renamed:
                rename(oldname + '-TAILOR-HACKED-TEMP-NAME', oldname)

    def _prepareTargetRepository(self, source_repo):
        """
        Execute ``darcs initialize``.
        """

        from os import makedirs
        from os.path import join, exists

        if not exists(self.basedir):
            makedirs(self.basedir)
        elif exists(join(self.basedir, self.repository.METADIR)):
            return

        init = ExternalCommand(cwd=self.basedir,
                               command=[self.repository.DARCS_CMD,
                                        "initialize"])
        init.execute()

        if init.exit_status:
            raise TargetInitializationFailure(
                "%s returned status %s" % (str(init), init.exit_status))

    def _prepareWorkingDirectory(self, source_repo):
        """
        Tweak the default settings of the repository.
        """

        from os.path import join
        from re import escape
        from dualwd import IGNORED_METADIRS

        motd = open(join(self.basedir, '_darcs/prefs/motd'), 'w')
        motd.write(MOTD % str(source_repo))
        motd.close()

        # Remove .cvsignore from default boring file
        boring = open(join(self.basedir, '_darcs/prefs/boring'), 'r')
        ignored = [line for line in boring if line <> '\.cvsignore$\n']
        boring.close()

        # Augment the boring file, that contains a regexp per line
        # with all known VCs metadirs to be skipped.
        boring = open(join(self.basedir, '_darcs/prefs/boring'), 'w')
        boring.write(''.join(ignored))
        boring.write('\n'.join(['(^|/)%s($|/)' % escape(md)
                                for md in IGNORED_METADIRS]))
        boring.write('\n')
        if self.logfile.startswith(self.basedir):
            boring.write('^')
            boring.write(self.logfile[len(self.basedir)+1:])
            boring.write('$\n')
        if self.state_file.filename.startswith(self.basedir):
            boring.write('^')
            boring.write(self.state_file.filename[len(self.basedir)+1:])
            boring.write('$\n')
        boring.close()
