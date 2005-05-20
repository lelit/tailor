#! /usr/bin/python
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

from shwrap import SystemCommand, shrepr, ReopenableNamedTemporaryFile
from source import UpdatableSourceWorkingDir, ChangesetApplicationFailure, \
     InvocationError
from target import SyncronizableTargetWorkingDir, TargetInitializationFailure


class CvsPsLog(SystemCommand):
    COMMAND = "cvsps %(update)s-b %(branch)s 2>/dev/null"

    def __call__(self, output=None, dry_run=False, **kwargs):
        update = kwargs.get('update', '')
        if update:
            update = '-u '
        kwargs['update'] = update
        
        return SystemCommand.__call__(self, output=output,
                                      dry_run=dry_run, **kwargs)

    
class CvsUpdate(SystemCommand):
    COMMAND = 'cvs -q %(dry)supdate -d %(revision)s %(entry)s 2>&1'
    
    def __call__(self, output=None, dry_run=False, **kwargs):
        if dry_run:
            kwargs['dry'] = '-n '
        else:
            kwargs['dry'] = ''

        if kwargs['revision'] is None:
            kwargs['revision'] = ''
        else:
            kwargs['revision'] = '-r%s' % kwargs['revision']
            
        return SystemCommand.__call__(self, output=output,
                                      dry_run=False, **kwargs)


class CvsCommit(SystemCommand):
    COMMAND = "cvs -q ci -F %(logfile)s %(entries)s"
    

class CvsRemove(SystemCommand):
    COMMAND = "cvs -q remove %(entry)s"


class CvsCheckout(SystemCommand):
    COMMAND = "cvs -q -d%(repository)s checkout %(revision)s -d%(workingdir)s %(module)s"

    def __call__(self, output=None, dry_run=False, **kwargs):
        revision = kwargs['revision']
        if revision is None:
            revision = ''
        else:
            # If the revision contains a space, assume it really
            # specify a branch and a timestamp. If it starts with
            # a digit, assume it's a timestamp. Otherwise, it must
            # be a branch name
            if revision[0] in '0123456789':
                revision = "-D'%s'" % revision
            elif ' ' in revision:
                branch, timestamp =revision.split(' ', 1)
                revision = "-r%s -D'%s'" % (branch, timestamp)
            else:
                revision = '-r%s' % revision
        kwargs['revision'] = revision
        
        return SystemCommand.__call__(self, output=output,
                                      dry_run=False, **kwargs)


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

    log.seek(0)

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
    
    def getUpstreamChangesets(self, root, repository, module, sincerev=None):
        from os.path import join, exists
         
        cvsps = CvsPsLog(working_dir=root)
        
        branch="HEAD"
        fname = join(root, 'CVS', 'Tag')
        if exists(fname):
            tag = open(fname).read()
            if tag.startswith('T'):
                branch=tag[1:-1]

        if sincerev:
            sincerev = int(sincerev)
            
        changesets = []
        log = cvsps(output=True, update=True, branch=branch)
        for cs in changesets_from_cvsps(log, sincerev):
            changesets.append(cs)

        return changesets

    def __maybeDeleteDirectory(self, root, entrydir, changeset):
        from os.path import join, exists
        from os import listdir
        
        if not entrydir:
            return

        try:
            cache = self.__deletedDirsCache
        except AttributeError:
            cache = self.__deletedDirsCache = {}

        if entrydir in cache:
            return
        
        absentrydir = join(root, entrydir)
        if not exists(absentrydir) or listdir(absentrydir) == ['CVS']:
            deldir = changeset.addEntry(entrydir, None)
            deldir.action_kind = deldir.DELETED

        cache[entrydir] = True
        
    def _applyChangeset(self, root, changeset, logger=None):
        from os.path import join, exists, dirname, split
        from os import makedirs, listdir
        from cvs import CvsEntries
        from time import sleep
        
        entries = CvsEntries(root)
        
        cvsup = CvsUpdate(working_dir=root)
        for e in changeset.entries:
            if e.action_kind == e.UPDATED:
                info = entries.getFileInfo(e.name)
                if info and info.cvs_version == e.new_revision:
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
            
            cvsup(output=True, entry=shrepr(e.name), revision=e.new_revision)
            
            if cvsup.exit_status:
                if logger: logger.warning("'cvs update' on %s exited "
                                          "with status %d, retrying once..." %
                                          (e.name, cvsup.exit_status))
                sleep(2)
                cvsup(output=True, entry=e.name, revision=e.new_revision)
                if cvsup.exit_status:
                    if logger: logger.warning("'cvs update' on %s exited "
                                              "with status %d, retrying "
                                              "one last time..." %
                                              (e.name, cvsup.exit_status))
                    sleep(8)
                    cvsup(output=True, entry=e.name, revision=e.new_revision)
                    
            if cvsup.exit_status:
                raise ChangesetApplicationFailure(
                    "'cvs update' returned status %s" % cvsup.exit_status)
            
            if logger: logger.info("%s updated to %s" % (e.name,
                                                         e.new_revision))
            
            if e.action_kind == e.DELETED:
                self.__maybeDeleteDirectory(root, split(e.name)[0],
                                            changeset)
                
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

        wdir = join(basedir, subdir)
        if not exists(join(wdir, 'CVS')):
            c = CvsCheckout(working_dir=basedir)
            c(output=True,
              repository=repository,
              module=module,
              revision=revision,
              workingdir=shrepr(subdir))
            if c.exit_status:
                raise TargetInitializationFailure(
                    "'cvs checkout' returned status %s" % c.exit_status)
        else:
            if logger: logger.info("Using existing %s", wdir)
            
        self.__forceTagOnEachEntry(wdir)
        
        entries = CvsEntries(wdir)
        
        # update cvsps cache, then loop over the changesets and find the
        # last applied, to find out the actual cvsps revision

        csets = self.getUpstreamChangesets(wdir, repository, module)
        csets.reverse()
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

        c = SystemCommand(working_dir=root, command="cvs -q add %(names)s")
        c(names=' '.join([shrepr(n) for n in names]))

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
        
        rontf = ReopenableNamedTemporaryFile('cvs', 'tailor')
        log = open(rontf.name, "w")
        log.write(remark)
        log.write('\n')
        if changelog:
            log.write(changelog)
            log.write('\n')
        log.close()
       
        c = CvsCommit(working_dir=root)

        if entries:
            entries = ' '.join([shrepr(e) for e in entries])
        else:
            entries = '.'
          
        c(entries=entries, logfile=rontf.name)
       
    def _removePathnames(self, root, names):
        """
        Remove some filesystem objects.
        """

        c = CvsRemove(working_dir=root)
        c(entry=' '.join([shrepr(n) for n in names]))

    def _renamePathname(self, root, oldname, newname):
        """
        Rename a filesystem object.
        """

        self._removePathnames(root, [oldname])
        self._addPathnames(root, [newname])
