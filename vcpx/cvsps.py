# -*- mode: python; coding: utf-8 -*-
# :Progetto: vcpx -- CVS details
# :Creato:   mer 16 giu 2004 00:46:12 CEST
# :Autore:   Lele Gaifax <lele@nautilus.homeip.net>
# :Licenza:  GNU General Public License
#

"""
This module contains supporting classes for CVS. To get a
cross-repository revision number a la Subversion, the implementation
uses `cvsps` to fetch the changes from the upstream repository.
"""

__docformat__ = 'reStructuredText'

from shwrap import ExternalCommand, PIPE, STDOUT
from source import UpdatableSourceWorkingDir, ChangesetApplicationFailure, \
     InvocationError
from target import SyncronizableTargetWorkingDir, TargetInitializationFailure

class EmptyRepositoriesFoolsMe(Exception):
    "Cannot handle empty repositories. Maybe wrong module/repository?"

    # This is the exception raised when we try to tailor an empty CVS
    # repository. This is more a shortcoming of tailor, rather than a
    # real problem with those repositories.

def changesets_from_cvsps(log, sincerev=None):
    """
    Parse CVSps log.
    """

    from changes import Changeset, ChangesetEntry
    from datetime import datetime
    from cvs import compare_cvs_revs

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
        seen = {}
        while l.startswith('\t'):
            if not sincerev or (sincerev<int(pset['revision'])):
                file,revs = l[1:-1].split(':')
                fromrev,torev = revs.strip().split('->')

                # Due to the fuzzy mechanism, cvsps may group
                # together two commits on a single entry, thus
                # giving something like:
                #
                #   Normalizer.py:1.12->1.13
                #   Registry.py:1.22->1.23
                #   Registry.py:1.21->1.22
                #   Stopwords.py:1.9->1.10
                #
                # Collapse those into a single one.

                e = seen.get(file)
                if not e:
                    e = ChangesetEntry(file)
                    e.old_revision = fromrev
                    e.new_revision = torev
                    seen[file] = e
                    entries.append(e)
                else:
                    if compare_cvs_revs(e.old_revision, fromrev)>0:
                        e.old_revision = fromrev

                    if compare_cvs_revs(e.new_revision, torev)<0:
                        e.new_revision = torev

                if fromrev=='INITIAL':
                    e.action_kind = e.ADDED
                elif "(DEAD)" in torev:
                    e.action_kind = e.DELETED
                    e.new_revision = torev[:torev.index('(DEAD)')]
                else:
                    e.action_kind = e.UPDATED

            l = log.readline()

        if not sincerev or (sincerev<int(pset['revision'])):
            cvsdate = pset['date']
            y,m,d = map(int, cvsdate[:10].split('/'))
            hh,mm,ss = map(int, cvsdate[11:19].split(':'))
            timestamp = datetime(y, m, d, hh, mm, ss)
            pset['date'] = timestamp

            yield Changeset(**pset)


class CvspsWorkingDir(UpdatableSourceWorkingDir,
                      SyncronizableTargetWorkingDir):

    """
    An instance of this class represents a read/write CVS working
    directory, so that it can be used both as a source of patches and
    as a target repository.

    It uses `cvsps` to do the actual fetch of the changesets metadata
    from the server, so that we can reasonably group together related
    changes that would otherwise be sparsed, as CVS is file-centric.
    """

    ## UpdatableSourceWorkingDir

    def _getUpstreamChangesets(self, sincerev=None):
        from os.path import join, exists

        branch="HEAD"
        fname = join(self.basedir, 'CVS', 'Tag')
        if exists(fname):
            tag = open(fname).read()
            if tag.startswith('T'):
                branch=tag[1:-1]

        if sincerev:
            sincerev = int(sincerev)

        changesets = []
        cmd = self.repository.command("--cvs-direct", "-u", "-b", branch,
                                      "--root", self.repository.repository,
                                      cvsps=True)
        cvsps = ExternalCommand(command=cmd)
        log = cvsps.execute(self.repository.module, stdout=PIPE, TZ='UTC')[0]

        for cs in changesets_from_cvsps(log, sincerev):
            changesets.append(cs)

        return changesets

    def __maybeDeleteDirectory(self, entrydir, changeset):
        from os.path import join, exists
        from os import listdir

        if not entrydir:
            return

        absentrydir = join(self.basedir, entrydir)
        if not exists(absentrydir) or listdir(absentrydir) == ['CVS']:
            deldir = changeset.addEntry(entrydir, None)
            deldir.action_kind = deldir.DELETED

    def _applyChangeset(self, changeset):
        from os.path import join, exists, dirname, split
        from os import listdir
        from shutil import rmtree
        from cvs import CvsEntries
        from time import sleep

        entries = CvsEntries(self.basedir)

        for e in changeset.entries:
            if e.action_kind == e.UPDATED:
                info = entries.getFileInfo(e.name)
                if not info:
                    self.log_info("promoting '%s' to ADDED at "
                                  "revision %s" % (e.name, e.new_revision))
                    e.action_kind = e.ADDED
                    self.__createParentCVSDirectories(changeset, e.name)
                elif info.cvs_version == e.new_revision:
                    self.log_info("skipping '%s' since it's already "
                                  "at revision %s" % (e.name, e.new_revision))
                    continue
            elif e.action_kind == e.DELETED:
                if not exists(join(self.basedir, e.name)):
                    self.log_info("skipping '%s' since it's already "
                                  "deleted" % e.name)
                    self.__maybeDeleteDirectory(split(e.name)[0], changeset)
                    continue
            elif e.action_kind == e.ADDED and e.new_revision is None:
                # This is a new directory entry, there is no need to update it
                continue

            # If this is a directory (CVS does not version directories,
            # and thus new_revision is always None for them), and it's
            # going to be deleted, do not execute a 'cvs update', that
            # in some cases does not do what one would expect. Instead,
            # remove it with everything it contains (that should be
            # just a single "CVS" subdir, btw)

            if e.action_kind == e.DELETED and e.new_revision is None:
                assert listdir(join(self.basedir, e.name)) == ['CVS'], '%s should be empty' % e.name
                rmtree(join(self.basedir, e.name))
            else:
                cmd = self.repository.command("-q", "update", "-d",
                                              "-r", e.new_revision)
                cvsup = ExternalCommand(cwd=self.basedir, command=cmd)
                retry = 0
                while True:
                    cvsup.execute(e.name)

                    if cvsup.exit_status:
                        retry += 1
                        if retry>3:
                            break
                        delay = 2**retry
                        self.log_info("%s returned status %s, "
                                      "retrying in %d seconds..." %
                                      (str(cvsup), cvsup.exit_status,
                                       delay))
                        sleep(retry)
                    else:
                        break

                if cvsup.exit_status:
                    raise ChangesetApplicationFailure(
                        "%s returned status %s" % (str(cvsup),
                                                   cvsup.exit_status))

                self.log_info("%s updated to %s" % (e.name, e.new_revision))

            if e.action_kind == e.DELETED:
                self.__maybeDeleteDirectory(split(e.name)[0], changeset)

    def _checkoutUpstreamRevision(self, revision):
        """
        Concretely do the checkout of the upstream sources. Use
        `revision` as the name of the tag to get, or as a date if it
        starts with a number.

        Return the last applied changeset.
        """

        from os.path import join, exists, split
        from cvs import CvsEntries, compare_cvs_revs
        from time import sleep

        if not self.repository.module:
            raise InvocationError("Must specify a module name")

        timestamp = None
        if revision is not None:
            # If the revision contains a space, assume it really
            # specify a branch and a timestamp. If it starts with
            # a digit, assume it's a timestamp. Otherwise, it must
            # be a branch name
            if revision[0] in '0123456789' or revision == 'INITIAL':
                timestamp = revision
                revision = None
            elif ' ' in revision:
                revision, timestamp = revision.split(' ', 1)

        # Trasform the whole history in a list, since we need to
        # visit it beginning from the last element
        csets = list(self.getPendingChangesets(revision))
        if not csets:
            raise TargetInitializationFailure(
                "Something went wrong: there are no changesets since "
                "revision '%s'" % revision)
        if timestamp == 'INITIAL':
            cset = csets[0]
            timestamp = cset.date.isoformat(sep=' ')
        else:
            cset = None

        if not exists(join(self.basedir, 'CVS')):
            # CVS does not handle "checkout -d multi/level/subdir", so
            # split the basedir and use it's parentdir as cwd below.
            parentdir, subdir = split(self.basedir)
            cmd = self.repository.command("-q",
                                          "-d", self.repository.repository,
                                          "checkout",
                                          "-d", subdir)
            if revision:
                cmd.extend(["-r", revision])
            if timestamp:
                cmd.extend(["-D", "%s UTC" % timestamp])

            checkout = ExternalCommand(cwd=parentdir, command=cmd)
            retry = 0
            while True:
                checkout.execute(self.repository.module)
                if checkout.exit_status:
                    retry += 1
                    if retry>3:
                        break
                    delay = 2**retry
                    self.log_info("%s returned status %s, "
                                  "retrying in %d seconds..." %
                                  (str(checkout), checkout.exit_status,
                                   delay))
                    sleep(retry)
                else:
                    break

            if checkout.exit_status:
                raise TargetInitializationFailure(
                    "%s returned status %s" % (str(checkout),
                                               checkout.exit_status))
        else:
            self.log_info("Using existing %s" % self.basedir)

        if self.repository.tag_entries:
            self.__forceTagOnEachEntry()

        entries = CvsEntries(self.basedir)
        youngest_entry = entries.getYoungestEntry()
        if youngest_entry is None:
            raise EmptyRepositoriesFoolsMe("The working copy '%s' of the "
                                           "CVS repository seems empty, "
                                           "don't know how to deal with "
                                           "that." % self.basedir)

        # loop over the changesets and find the last applied, to find
        # out the actual cvsps revision

        found = False
        if cset is None and csets:
            cset = csets.pop()
        while cset is not None:
            for m in cset.entries:
                info = entries.getFileInfo(m.name)
                if info:
                    actualversion = info.cvs_version
                    found = compare_cvs_revs(actualversion,m.new_revision) >= 0
                    if not found:
                        break

            if found:
                last = cset
                break

            if csets:
                cset = csets.pop()
            else:
                cset = None

        if not found:
            raise TargetInitializationFailure(
                "Something went wrong: unable to determine the exact upstream "
                "revision of the checked out tree in '%s'" % self.basedir)
        else:
            self.log_info("working copy up to cvs revision %s" % last.revision)

        return last

    def _willApplyChangeset(self, changeset, applyable=None):
        """
        This gets called just before applying each changeset.

        Since CVS has no "createdir" event, we have to take care
        of new directories, creating empty-but-reasonable CVS dirs.
        """

        if UpdatableSourceWorkingDir._willApplyChangeset(self, changeset,
                                                         applyable):
            for m in changeset.entries:
                if m.action_kind == m.ADDED:
                    self.__createParentCVSDirectories(changeset, m.name)

            return True
        else:
            return False

    def __createParentCVSDirectories(self, changeset, entry):
        """
        Verify that the hierarchy down to the entry is under CVS.

        If the directory containing the entry does not exist,
        create it and make it appear as under CVS so that a subsequent
        'cvs update' will work.
        """

        from os.path import split, join, exists
        from os import mkdir

        path = split(entry)[0]
        if path:
            basedir = join(self.basedir, path)
        else:
            basedir = self.basedir
        cvsarea = join(basedir, 'CVS')

        if path and not exists(cvsarea):
            parentcvs = self.__createParentCVSDirectories(changeset, path)

            assert exists(parentcvs), "Uhm, strange things happen: " \
                "unable to find or create parent CVS area for %r" % path

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

            # Add the "new" directory to the changeset, so that the
            # replayer gets its name

            entry = changeset.addEntry(path, None)
            entry.action_kind = entry.ADDED

        return cvsarea

    ## SyncronizableTargetWorkingDir

    def _addPathnames(self, names):
        """
        Add some new filesystem objects.
        """

        cmd = self.repository.command("-q", "add")
        ExternalCommand(cwd=self.basedir, command=cmd).execute(names)

    def __forceTagOnEachEntry(self):
        """
        Massage each CVS/Entries file, locking (ie, tagging) each
        entry to its current CVS version.

        This is to prevent silly errors such those that could arise
        after a manual ``cvs update`` in the working directory.
        """

        from os import walk, rename
        from os.path import join

        for dir, subdirs, files in walk(self.basedir):
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

    def _getCommitEntries(self, changeset):
        """
        Extract the names of the entries for the commit phase.  Since CVS
        does not have a "rename" operation, this is simulated by a
        remove+add, and both entries must be committed.
        """

        entries = SyncronizableTargetWorkingDir._getCommitEntries(self,
                                                                  changeset)
        entries.extend([e.old_name for e in changeset.renamedEntries()])

        return entries

    def _commit(self, date, author, patchname, changelog=None, entries=None):
        """
        Commit the changeset.
        """

        from shwrap import ReopenableNamedTemporaryFile
        from locale import getpreferredencoding

        encoding = ExternalCommand.FORCE_ENCODING or getpreferredencoding()

        logmessage = []
        if patchname:
            logmessage.append(patchname.encode(encoding))
        if changelog:
            logmessage.append(changelog.encode(encoding))
        logmessage.append('')
        logmessage.append('Original author: %s' % author.encode(encoding))
        logmessage.append('Date: %s' % date)

        rontf = ReopenableNamedTemporaryFile('cvs', 'tailor')
        log = open(rontf.name, "w")
        log.write('\n'.join(logmessage))
        log.close()

        cmd = self.repository.command("-q", "ci", "-F", rontf.name)
        if not entries:
            entries = ['.']

        c = ExternalCommand(cwd=self.basedir, command=cmd)
        c.execute(entries)

        if c.exit_status:
            raise ChangesetApplicationFailure("%s returned status %d" %
                                              (str(c), c.exit_status))

    def _removePathnames(self, names):
        """
        Remove some filesystem objects.
        """

        cmd = self.repository.command("-q", "remove")
        ExternalCommand(cwd=self.basedir, command=cmd).execute(names)

    def _renamePathname(self, oldname, newname):
        """
        Rename a filesystem object.
        """

        self._removePathnames([oldname])
        self._addPathnames([newname])

    def _tag(self, tagname):
        """
        Apply a tag.
        """

        cmd = self.repository.command("tag")
        c = ExternalCommand(cwd=self.basedir, command=cmd)
        c.execute(tagname)
        if c.exit_status:
            raise ChangesetApplicationFailure("%s returned status %d" %
                                              (str(c), c.exit_status))
