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

DARCS_CMD = 'darcs'

MOTD = """\
This is the Darcs equivalent of
%s/%s
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
            elif name in ['name', 'comment',
                          'add_file', 'add_directory',
                          'modify_file', 'remove_file']:
                self.current_field = []
            elif name == 'move':
                self.old_name = attributes['from']
                self.new_name = attributes['to']

        def endElement(self, name):
            if name == 'patch':
                # Sort the paths to make tests easier
                self.current['entries'].sort(lambda x,y: cmp(x.name, y.name))
                cset = Changeset(self.current['name'],
                                 self.current['date'],
                                 self.current['author'],
                                 self.current['comment'],
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
            elif name in ['add_file', 'add_directory',
                          'modify_file', 'remove_file']:
                entry = ChangesetEntry(''.join(self.current_field).strip())
                entry.action_kind = { 'add_file': entry.ADDED,
                                      'add_directory': entry.ADDED,
                                      'modify_file': entry.UPDATED,
                                      'remove_file': entry.DELETED,
                                      'rename_file': entry.RENAMED
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

    def getUpstreamChangesets(self, root, repository, module, sincerev=None):
        """
        Do the actual work of fetching the upstream changeset.
        """

        from datetime import datetime
        from time import strptime
        from changes import Changeset

        cmd = [DARCS_CMD, "pull", "--dry-run"]
        pull = ExternalCommand(cwd=root, command=cmd)
        output = pull.execute(repository, stdout=PIPE, stderr=STDOUT, TZ='UTC')

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
            ##   * Refix getUpstreamChangesets for darcs

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

    def _applyChangeset(self, root, changeset, logger=None):
        """
        Do the actual work of applying the changeset to the working copy.
        """

        from re import escape

        if changeset.revision.startswith('tagged '):
            selector = '--tags'
            revtag = changeset.revision[7:]
        else:
            selector = '--patches'
            revtag = escape(changeset.revision)

        cmd = [DARCS_CMD, "pull", "--all", selector, revtag]
        pull = ExternalCommand(cwd=root, command=cmd)
        output = pull.execute(stdout=PIPE, stderr=STDOUT)

        if pull.exit_status:
            raise ChangesetApplicationFailure(
                "%s returned status %d saying \"%s\"" %
                (str(pull), pull.exit_status, output.read()))

        cmd = [DARCS_CMD, "changes", selector, revtag,
               "--xml-output", "--summ"]
        changes = ExternalCommand(cwd=root, command=cmd)
        last = changesets_from_darcschanges(changes.execute(stdout=PIPE))
        if last:
            changeset.entries.extend(last[0].entries)

    def _checkoutUpstreamRevision(self, basedir, repository, module, revision,
                                  subdir=None, logger=None, **kwargs):
        """
        Concretely do the checkout of the upstream revision and return
        the last applied changeset.
        """

        from os.path import join, exists
        from os import mkdir
        from re import escape

        if revision == 'INITIAL':
            initial = True
            cmd = [DARCS_CMD, "changes", "--xml-output", "--repo", repository]
            changes = ExternalCommand(command=cmd)
            output = changes.execute(stdout=PIPE, stderr=STDOUT)

            if changes.exit_status:
                raise ChangesetApplicationFailure(
                    "%s returned status %d saying \"%s\"" %
                    (str(changes), changes.exit_status, output.read()))

            csets = changesets_from_darcschanges(output)
            revision = escape(csets[0].revision)
        else:
            initial = False

        wdir = join(basedir, subdir)
        if subdir == '.':
            # This is currently *very* slow, compared to the darcs get
            # below!
            if not exists(join(wdir, '_darcs')):
                if not exists(wdir):
                    mkdir(wdir)

                init = ExternalCommand(cwd=wdir,
                                       command=[DARCS_CMD, "initialize"])
                init.execute(stdout=PIPE)

                if init.exit_status:
                    raise TargetInitializationFailure(
                        "%s returned status %s" % (str(init),
                                                   init.exit_status))

                cmd = [DARCS_CMD, "pull", "--all", "--verbose"]
                if revision and revision<>'HEAD':
                    cmd.extend([initial and "--patches" or "--tags", revision])
                dpull = ExternalCommand(cwd=wdir, command=cmd)
                output = dpull.execute(repository, stdout=PIPE, stderr=STDOUT)

                if dpull.exit_status:
                    raise TargetInitializationFailure(
                        "%s returned status %d saying \"%s\"" %
                        (str(dpull), dpull.exit_status, output.read()))
        else:
            # Use much faster 'darcs get'
            cmd = [DARCS_CMD, "get", "--partial", "--verbose"]
            if revision and revision<>'HEAD':
                cmd.extend([initial and "--to-patch" or "--tag", revision])
            dget = ExternalCommand(cwd=basedir, command=cmd)
            output = dget.execute(repository, subdir,
                                  stdout=PIPE, stderr=STDOUT)

            if dget.exit_status:
                raise TargetInitializationFailure(
                    "%s returned status %d saying \"%s\"" %
                    (str(dget), dget.exit_status, output.read()))

        cmd = [DARCS_CMD, "changes", "--last", "1", "--xml-output"]
        changes = ExternalCommand(cwd=wdir, command=cmd)
        output = changes.execute(stdout=PIPE, stderr=STDOUT)

        if changes.exit_status:
            raise ChangesetApplicationFailure(
                "%s returned status %d saying \"%s\"" %
                (str(changes), changes.exit_status, output.read()))

        last = changesets_from_darcschanges(output)

        return last[0]


    ## SyncronizableTargetWorkingDir

    def _addPathnames(self, root, names):
        """
        Add some new filesystems objects.
        """

        cmd = [DARCS_CMD, "add", "--case-ok", "--not-recursive", "--quiet"]
        ExternalCommand(cwd=root, command=cmd).execute(names)

    def _addSubtree(self, root, subdir):
        """
        Use the --recursive variant of ``darcs add`` to add a subtree.
        """

        cmd = [DARCS_CMD, "add", "--case-ok", "--recursive", "--quiet"]
        ExternalCommand(cwd=root, command=cmd).execute(subdir)

    def _commit(self, root, date, author, remark, changelog=None, entries=None):
        """
        Commit the changeset.
        """

        from sys import getdefaultencoding

        encoding = ExternalCommand.FORCE_ENCODING or getdefaultencoding()

        logmessage = []

        logmessage.append(date.strftime('%Y/%m/%d %H:%M:%S UTC'))
        logmessage.append(author.encode(encoding))
        logmessage.append(remark and remark.encode(encoding) or 'Unnamed patch')
        logmessage.append(changelog and changelog.encode(encoding) or '')
        logmessage.append('')

        cmd = [DARCS_CMD, "record", "--all", "--pipe"]
        if not entries:
            entries = ['.']

        record = ExternalCommand(cwd=root, command=cmd)
        record.execute(entries, input='\n'.join(logmessage), stdout=PIPE)

        if record.exit_status:
            raise ChangesetApplicationFailure(
                "%s returned status %d" % (str(record), record.exit_status))

    def _removePathnames(self, root, names):
        """
        Remove some filesystem object.
        """

        # Since the source VCS already deleted the entry, and given that
        # darcs will do the right thing with it, do nothing here, instead
        # of
        #         c = ExternalCommand(cwd=root,
        #                             command=[DARCS_CMD, "remove"])
        #         c.execute(entries)
        # that raises status 512 on darcs not finding the entry.

        pass

    def _renamePathname(self, root, oldname, newname):
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

        renamed = exists(join(root, oldname))
        if renamed:
            rename(oldname, oldname + '-TAILOR-HACKED-TEMP-NAME')

        try:
            cmd = [DARCS_CMD, "mv"]
            ExternalCommand(cwd=root, command=cmd).execute(oldname, newname)
        finally:
            if renamed:
                rename(oldname + '-TAILOR-HACKED-TEMP-NAME', oldname)

    def _initializeWorkingDir(self, root, source_repository, source_module,
                              subdir):
        """
        Execute ``darcs initialize`` and tweak the default settings of
        the repository, then add the whole subtree.
        """

        from os.path import join
        from re import escape
        from dualwd import IGNORED_METADIRS

        init = ExternalCommand(cwd=root, command=[DARCS_CMD, "initialize"])
        init.execute(stdout=PIPE)

        if init.exit_status:
            raise TargetInitializationFailure(
                "%s returned status %s" % (str(init), init.exit_status))

        motd = open(join(root, '_darcs/prefs/motd'), 'w')
        motd.write(MOTD % (source_repository, source_module))
        motd.close()

        # Remove .cvsignore from default boring file
        boring = open(join(root, '_darcs/prefs/boring'), 'r')
        ignored = [line for line in boring if line <> '\.cvsignore$\n']
        boring.close()

        # Augment the boring file, that contains a regexp per line
        # with all known VCs metadirs to be skipped.
        boring = open(join(root, '_darcs/prefs/boring'), 'w')
        boring.write(''.join(ignored))
        boring.write('\n'.join(['(^|/)%s($|/)' % escape(md)
                                for md in IGNORED_METADIRS]))
        boring.write('\n^tailor.log$\n^tailor.info$\n')
        boring.close()

        SyncronizableTargetWorkingDir._initializeWorkingDir(self, root,
                                                            source_repository,
                                                            source_module,
                                                            subdir)
