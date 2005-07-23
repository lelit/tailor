# -*- mode: python; coding: utf-8 -*-
# :Progetto: vcpx -- CVS details
# :Creato:   mer 16 giu 2004 00:46:12 CEST
# :Autore:   Lele Gaifax <lele@nautilus.homeip.net>
# :Licenza:  GNU General Public License
# 

"""
This module contains supporting classes for CVS. To get a
cross-repository revision number ala Subversion, the implementation
uses `cvsps` to fetch the changes from the upstream repository.
"""

__docformat__ = 'reStructuredText'

from shwrap import ExternalCommand, PIPE, STDOUT
from source import UpdatableSourceWorkingDir, ChangesetApplicationFailure, \
     InvocationError
from target import SyncronizableTargetWorkingDir, TargetInitializationFailure

CVS_CMD = 'cvs'
CVSPS_CMD = 'cvsps'   

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
                fromrev,torev = revs.split('->')

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
    An instance of this class represent a read/write CVS working directory,
    so that it can be used both as source of patches, or as a target
    repository.

    It uses `cvsps` to do the actual fetch of the changesets metadata
    from the server, so that we can reasonably group together related
    changes that would otherwise be sparsed, as CVS is file-centric.
    """

    ## UpdatableSourceWorkingDir
    
    def getUpstreamChangesets(self, root, repository, module, sincerev=None,
                              branch=None):
        from os.path import join, exists

        if branch is None:
            branch="HEAD"
            fname = join(root, 'CVS', 'Tag')
            if exists(fname):
                tag = open(fname).read()
                if tag.startswith('T'):
                    branch=tag[1:-1]

        if sincerev:
            sincerev = int(sincerev)
            
        changesets = []
        cmd = [CVSPS_CMD, "-u", "-b", branch]
        cvsps = ExternalCommand(cwd=root, command=cmd)
        log = cvsps.execute(stdout=PIPE)
        
        for cs in changesets_from_cvsps(log, sincerev):
            changesets.append(cs)

        return changesets

    def __maybeDeleteDirectory(self, root, entrydir, changeset):
        from os.path import join, exists
        from os import listdir
        
        if not entrydir:
            return

        absentrydir = join(root, entrydir)
        if not exists(absentrydir) or listdir(absentrydir) == ['CVS']:
            deldir = changeset.addEntry(entrydir, None)
            deldir.action_kind = deldir.DELETED
        
    def _applyChangeset(self, root, changeset, logger=None):
        from os.path import join, exists, dirname, split
        from os import makedirs, listdir
        from shutil import rmtree
        from cvs import CvsEntries
        from time import sleep
        
        entries = CvsEntries(root)

        for e in changeset.entries:
            if e.action_kind == e.UPDATED:
                info = entries.getFileInfo(e.name)
                if not info:
                    if logger: logger.info("promoting '%s' to ADDED at "
                                           "revision %s", e.name,
                                           e.new_revision)
                    e.action_kind = e.ADDED
                    self.__createParentCVSDirectories(changeset, root, e.name)
                elif info.cvs_version == e.new_revision:
                    if logger: logger.debug("skipping '%s' since it's already "
                                            "at revision %s", e.name,
                                            e.new_revision)
                    continue
            elif e.action_kind == e.DELETED:
                if not exists(join(root, e.name)):
                    if logger: logger.debug("skipping '%s' since it's already "
                                            "deleted", e.name)
                    self.__maybeDeleteDirectory(root, split(e.name)[0],
                                                changeset)
                    continue
            elif e.action_kind == e.ADDED and e.new_revision is None:
                # This is a new directory entry, there is no need to update it
                continue

            # If this is a directory (CVS does not version directories,
            # and thus new_revision is always None for them), and it's
            # going to be deleted, do not execute a 'cvs update', that
            # in some cases does not what one would expect. Instead,
            # remove it with everything it contains (that should be
            # just a single "CVS" subdir, btw)
            
            if e.action_kind == e.DELETED and e.new_revision is None:
                assert listdir(join(root, e.name)) == ['CVS'], '%s should be empty' % e.name
                rmtree(join(root, e.name))
            else:
                cmd = [CVS_CMD, "-q", "update", "-d", "-r%s" % e.new_revision]
                cvsup = ExternalCommand(cwd=root, command=cmd)
                retry = 0
                while True:
                    cvsup.execute(e.name, stdout=PIPE)
            
                    if cvsup.exit_status:
                        retry += 1
                        if retry>3:
                            break
                        delay = 2**retry
                        if logger:
                            logger.warning("%s returned status %s, "
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

                if logger: logger.info("%s updated to %s" % (e.name,
                                                             e.new_revision))

            if e.action_kind == e.DELETED:
                self.__maybeDeleteDirectory(root, split(e.name)[0], changeset)

    def _checkoutUpstreamRevision(self, basedir, repository, module, revision,
                                  subdir=None, logger=None, **kwargs):
        """
        Concretely do the checkout of the upstream sources. Use `revision` as
        the name of the tag to get, or as a date if it starts with a number.

        Return the effective cvsps revision.
        """

        from os.path import join, exists
        from cvs import CvsEntries, compare_cvs_revs

        if not module:
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

        wdir = join(basedir, subdir)
        csets = self.getUpstreamChangesets(wdir, repository, module,
                                           branch=revision or 'HEAD')
        csets.reverse()

        if timestamp == 'INITIAL':
            timestamp = csets[-1].date.isoformat(sep=' ')
            
        if not exists(join(wdir, 'CVS')):
            cmd = [CVS_CMD, "-q", "-d", repository, "checkout",
                   "-d", subdir]
            if revision:
                cmd.extend(["-r", revision])
            if timestamp:
                cmd.extend(["-D", "%s UTC" % timestamp])
            
            checkout = ExternalCommand(cwd=basedir, command=cmd)
            checkout.execute(module)
            
            if checkout.exit_status:
                raise TargetInitializationFailure(
                    "%s returned status %s" % (str(checkout),
                                               checkout.exit_status))
        else:
            if logger: logger.info("Using existing %s", wdir)
            
        self.__forceTagOnEachEntry(wdir)
        
        entries = CvsEntries(wdir)
        
        # update cvsps cache, then loop over the changesets and find the
        # last applied, to find out the actual cvsps revision

        found = False
        for cset in csets:
            for m in cset.entries:
                info = entries.getFileInfo(m.name)
                if info:
                    actualversion = info.cvs_version
                    found = compare_cvs_revs(actualversion,m.new_revision)>=0
                    if not found:
                        break
                
            if found:
                last = cset
                break

        if not found:
            raise TargetInitializationFailure(
                "Something went wrong: unable to determine the exact upstream "
                "revision of the checked out tree in '%s'" % wdir)
        else:
            if logger: logger.info("working copy up to cvsps revision %s",
                                   last.revision)
            
        return last.revision
    
    def _willApplyChangeset(self, root, changeset, applyable=None):
        """
        This gets called just before applying each changeset.
        
        Since CVS has no "createdir" event, we have to take care
        of new directories, creating empty-but-reasonable CVS dirs.
        """

        if UpdatableSourceWorkingDir._willApplyChangeset(self, root, changeset,
                                                         applyable):
            for m in changeset.entries:
                if m.action_kind == m.ADDED:
                    self.__createParentCVSDirectories(changeset, root, m.name)
            
            return True
        else:
            return False
        
    def __createParentCVSDirectories(self, changeset, root, entry):
        """
        Verify that the hierarchy down to the entry is under CVS.

        If the directory containing the entry does not exists,
        create it and make it appear as under CVS so that succeding
        'cvs update' will work.
        """
        
        from os.path import split, join, exists
        from os import mkdir

        path = split(entry)[0]
        if path:
            basedir = join(root, path)
        else:
            basedir = root            
        cvsarea = join(basedir, 'CVS')
        
        if path and not exists(cvsarea):
            parentcvs = self.__createParentCVSDirectories(changeset,
                                                          root, path)

            assert exists(parentcvs), "Uhm, strange things happen"
            
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
            # replayer get its name

            entry = changeset.addEntry(path, None)
            entry.action_kind = entry.ADDED
            
        return cvsarea
    
    ## SyncronizableTargetWorkingDir

    def _addPathnames(self, root, names):
        """
        Add some new filesystem objects.
        """

        cmd = [CVS_CMD, "-q", "add"]
        ExternalCommand(cwd=root, command=cmd).execute(names)

    def __forceTagOnEachEntry(self, root):
        """
        Massage each CVS/Entries file, locking (ie, tagging) each
        entry to its current CVS version.

        This is to prevent silly errors such those that could arise
        after a manual ``cvs update`` in the working directory.
        """
        
        from os import walk, rename
        from os.path import join

        for dir, subdirs, files in walk(root):
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
        
    def _commit(self,root, date, author, remark, changelog=None, entries=None):
        """
        Commit the changeset.
        """

        from shwrap import ReopenableNamedTemporaryFile
        from sys import getdefaultencoding
        
        encoding = ExternalCommand.FORCE_ENCODING or getdefaultencoding()
        
        rontf = ReopenableNamedTemporaryFile('cvs', 'tailor')
        log = open(rontf.name, "w")
        log.write(remark.encode(encoding))
        if changelog:
            log.write('\n')
            log.write(changelog.encode(encoding))
        log.write("\n\nOriginal author: %s\nDate: %s\n" % (
            author.encode(encoding), date))
        log.close()            

        cmd = [CVS_CMD, "-q", "ci", "-F", rontf.name]
        if not entries:
            entries = ['.']
          
        ExternalCommand(cwd=root, command=cmd).execute(entries)
       
    def _removePathnames(self, root, names):
        """
        Remove some filesystem objects.
        """

        cmd = [CVS_CMD, "-q", "remove"]
        ExternalCommand(cwd=root, command=cmd).execute(names)

    def _renamePathname(self, root, oldname, newname):
        """
        Rename a filesystem object.
        """

        self._removePathnames(root, [oldname])
        self._addPathnames(root, [newname])
