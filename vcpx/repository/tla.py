# -*- mode: python; coding: utf-8 -*-
# :Progetto: vcpx -- tla (Arch 1.x) backend
# :Creato:   sab 13 ago 2005 12:16:16 CEST
# :Autore:   Robin Farine <robin.farine@terminus.org>
# :Licenza:  GNU General Public License
#

# Current limitations and pitfalls.
#
# - Target backend not implemented.
#
# - In-version continuations not supported (raises an exception); this
#   would probably require to compute a changeset with 'tla delta'
#   instead of using update.
#
# - Pika escaped file names. This implementations requires a version
#   of tla that supports pika escapes. For changesets created with a
#   version of tla that did not support pika escapes, if one of these
#   changeset contains a file name with a valid embedded pika escape
#   sequence, things will break.

"""
This module implements the backends for tla (Arch 1.x).

This backend interprets tailor's repository, module and revision arguments
as follows:

repository
  a registered archive name

module
  <category>--<branch>--<version>

revision
  <revision>
"""

__docformat__ = 'reStructuredText'

import os
from datetime import datetime
from time import strptime
from tempfile import mkdtemp
from email.Parser import Parser

from vcpx.repository import Repository
from vcpx.changes import Changeset
from vcpx.shwrap import ExternalCommand, PIPE
from vcpx.source import UpdatableSourceWorkingDir, ChangesetApplicationFailure, \
                        GetUpstreamChangesetsFailure
from vcpx.target import TargetInitializationFailure
from vcpx.tzinfo import UTC, FixedOffset


class TlaRepository(Repository):
    METADIR = '{arch}'

    def _load(self, project):
        Repository._load(self, project)
        self.EXECUTABLE = project.config.get(self.name, 'tla-command', 'tla')
        self.IGNORE_IDS = project.config.get(self.name, 'ignore-ids', False)
        if self.IGNORE_IDS:
            self.EXTRA_METADIRS = ['.arch-ids']


class TlaWorkingDir(UpdatableSourceWorkingDir):
    """
    A working directory under ``tla``.
    """

    ## UpdatableSourceWorkingDir

    def _getUpstreamChangesets(self, sincerev):
        """
        Build the list of upstream changesets missing in the working directory.
        """

        changesets = []
        self.fqversion = '/'.join([self.repository.repository,
                                   self.repository.module])
        c = ExternalCommand(cwd=self.repository.basedir,
                            command=self.repository.command("missing", "-f"))
        out, err = c.execute(stdout=PIPE, stderr=PIPE)
        if c.exit_status:
            raise GetUpstreamChangesetsFailure(
                "%s returned status %d saying\n%s" %
                (str(c), c.exit_status, err.read()))
        changesets = self.__parse_revision_logs(out.read().split())
        return changesets

    def _applyChangeset(self, changeset):
        """
        Do the actual work of applying the changeset to the working copy and
        record the changes in ``changeset``. Return a list of files involved
        in conflicts.
        """

        if self.shared_basedirs:
            tempdir = self.__hide_foreign_entries()
            try:
                conflicts = self.__apply_changeset(changeset)
            finally:
                if tempdir:
                    self.__restore_foreign_entries(tempdir)
        else:
            conflicts = self.__apply_changeset(changeset)
        return conflicts

    def _checkoutUpstreamRevision(self, revision):
        """
        Create the initial working directory during bootstrap.
        """

        fqrev = self.__initial_revision(revision)
        if self.shared_basedirs:
            tempdir = mkdtemp("", ",,tailor-", self.repository.basedir)
            try:
                self.__checkout_initial_revision(fqrev, tempdir, "t")
            finally:
                newtree = os.path.join(tempdir, "t")
                if os.path.exists(newtree):
                    for e in os.listdir(newtree):
                        os.rename(os.path.join(newtree, e),
                                  os.path.join(self.repository.basedir, e))
                    os.rmdir(newtree)
                os.rmdir(tempdir)
        else:
            root, destdir = os.path.split(self.repository.basedir)
            self.__checkout_initial_revision(fqrev, root, destdir)
        return self.__parse_revision_logs([fqrev], False)[0]

    ## TlaWorkingDir private helper functions

    def __checkout_initial_revision(self, fqrev, root, destdir):
        if not os.path.exists(root):
            os.makedirs(root)
        cmd = self.repository.command("get", "--no-pristine", fqrev, destdir)
        c = ExternalCommand(cwd=root, command=cmd)
        out, err = c.execute(stdout=PIPE, stderr=PIPE)
        if c.exit_status:
            raise TargetInitializationFailure(
                "%s returned status %d saying\n%s" %
                (str(c), c.exit_status, err.read()))

    def __apply_changeset(self, changeset):
        c = ExternalCommand(cwd=self.repository.basedir,
                            command=self.repository.command("update"))
        out, err = c.execute(changeset.revision, stdout=PIPE, stderr=PIPE)
        if not c.exit_status in [0, 1]:
            raise ChangesetApplicationFailure(
                "%s returned status %d saying\n%s" %
                (str(c), c.exit_status, err.read()))
        return self.__parse_apply_changeset_output(changeset, out)

    def __normalize_path(self, path):
        if len(path) > 2:
            if path[0:2] == "./":
                path = path[2:]
        if path.find("\(") != -1:
            cmd = self.repository.command("escape", "--unescaped", path)
            c = ExternalCommand(command=cmd)
            out, err = c.execute(stdout=PIPE, stderr=PIPE)
            if c.exit_status:
                raise GetUpstreamChangesetsFailure(
                    "%s returned status %d saying\n%s" %
                    (str(c), c.exit_status, err.read()))
            path = out.read()
        return path

    def __initial_revision(self, revision):
        fqversion = '/'.join([self.repository.repository,
                              self.repository.module])
        if revision in ['HEAD', 'INITIAL']:
            cmd = self.repository.command("revisions")
            if revision == 'HEAD':
                cmd.append("-r")
            cmd.append(fqversion)
            c = ExternalCommand(command=cmd)
            out, err = c.execute(stdout=PIPE, stderr=PIPE)
            if c.exit_status:
                raise TargetInitializationFailure(
                    "%s returned status %d saying\n%s" %
                    (str(c), c.exit_status, err.read()))
            revision = out.readline().strip()
        return '--'.join([fqversion, revision])

    def __parse_revision_logs(self, fqrevlist, update=True):
        changesets = []
        logparser = Parser()
        c = ExternalCommand(cwd=self.repository.basedir,
                            command=self.repository.command("cat-archive-log"))
        for fqrev in fqrevlist:
            out, err = c.execute(fqrev, stdout=PIPE, stderr=PIPE)
            if c.exit_status:
                raise GetUpstreamChangesetsFailure(
                    "%s returned status %d saying\n%s" %
                    (str(c), c.exit_status, err.read()))
            err = None
            try:
                msg = logparser.parse(out)
            except Exception, err:
                pass
            if not err and msg.is_multipart():
                err = "unable to parse log description"
            if not err and update and msg.has_key('Continuation-of'):
                err = "in-version continuations not supported"
            if err:
                raise GetUpstreamChangesetsFailure(str(err))

            date = self.__parse_date(msg['Date'], msg['Standard-date'])
            author = msg['Creator']
            revision = fqrev
            logmsg = [msg['Summary']]
            s  = msg.get('Keywords', "").strip()
            if s:
                logmsg.append('Keywords: ' + s)
            s = msg.get_payload().strip()
            if s:
                logmsg.append(s)
            logmsg = '\n'.join(logmsg)
            changesets.append(Changeset(revision, date, author, logmsg))
        return changesets

    def __parse_date(self, d1, d2):
        # d1: Wed Dec 10 15:01:28 EST 2003
        # d2: 2003-12-10 04:01:28 GMT

        d1 = datetime(*strptime(d1[:19] + d1[-5:], '%a %b %d %H:%M:%S %Y')[:6]).replace(tzinfo=UTC)
        d2 = datetime(*strptime(d2[:19], '%Y-%m-%d %H:%M:%S')[:6]).replace(tzinfo=UTC)

        offset = d1 - d2
        offset = offset.seconds + offset.days * 24 * 3600

        return d1.replace(tzinfo=FixedOffset(offset/60))

    def __hide_foreign_entries(self):
        c = ExternalCommand(cwd=self.repository.basedir,
                            command=self.repository.command("tree-lint", "-tu"))
        out = c.execute(stdout=PIPE)[0]
        tempdir = mkdtemp("", "++tailor-", self.repository.basedir)
        try:
            for e in out:
                e = e.strip()
                ht = os.path.split(e)
                # only move inventory violations at the root
                if ht[0] and ht[1]:
                    continue
                os.rename(os.path.join(self.repository.basedir, e),
                          os.path.join(tempdir, e))
        except:
            self.__restore_foreign_entries(tempdir)
            raise
        return tempdir

    def __restore_foreign_entries(self, tempdir):
        for e in os.listdir(tempdir):
            os.rename(os.path.join(tempdir, e), os.path.join(self.repository.basedir, e))
        os.rmdir(tempdir)

    def __parse_apply_changeset_output(self, changeset, output):
        conflicts = []
        skip = True
        for line in output:
            # skip comment lines, detect beginning and end of change list
            if line[0] == '*':
                if line.startswith("* applying changeset"):
                    skip = False
                elif line.startswith("* reapplying local changes"):
                    break
                continue
            if skip:
                continue
            l = line.split()
            l1 = self.__normalize_path(l[1])
            l2 = None
            if len(l) > 2:
                l2 = self.__normalize_path(l[2])

            # ignore permission changes and changes in the {arch} directory
            if l[0] in ['--', '-/'] or l1.startswith("{arch}"):
                continue
            if self.repository.IGNORE_IDS and l1.find('.arch-ids') >= 0:
                continue
            rev = changeset.revision
            if l[0][0] == 'M' or l[0] in ['ch', 'cl']:
                # 'ch': file <-> symlink, 'cl': ChangeLog updated
                e = changeset.addEntry(l1, rev)
                e.action_kind = e.UPDATED
            elif l[0][0] == 'A':
                e = changeset.addEntry(l1, rev)
                e.action_kind = e.ADDED
            elif l[0][0] == 'D':
                e = changeset.addEntry(l1, rev)
                e.action_kind = e.DELETED
            elif l[0] in ['=>', '/>']:
                e = changeset.addEntry(l2, rev)
                e.old_name = l1
                e.action_kind = e.RENAMED
            elif l[0] in ['C', '?']:
                conflicts.append(l1)
                if l2:
                    conflicts.append(l2)
            else:
                raise ChangesetApplicationFailure(
                        "unhandled changeset operation: \"%s\"" %
                        line.strip())
        return conflicts
