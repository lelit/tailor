#! /usr/bin/python
# -*- mode: python; coding: utf-8 -*-
# :Progetto: vcpx -- Syncable targets
# :Creato:   ven 04 giu 2004 00:27:07 CEST
# :Autore:   Lele Gaifax <lele@nautilus.homeip.net>
# 

"""
Syncronizable targets are the simplest abstract wrappers around a
working directory under two different version control systems.
"""

__docformat__ = 'reStructuredText'

import socket

HOST = socket.getfqdn()
AUTHOR = "tailor"
BOOTSTRAP_PATCHNAME = 'Tailorization of %s'
BOOTSTRAP_CHANGELOG = """\
Import of the upstream sources from the repository

 %(repository)s

as of revision %(revision)s
"""

class TargetInitializationFailure(Exception):
    "Failure initializing the target VCS"
    
    pass

class SyncronizableTargetWorkingDir(object):
    """
    This is an abstract working dir usable as a *shadow* of another
    kind of VC, sharing the same working directory.

    Most interesting entry points are:

    replayChangeset
        to replay an already applied changeset, to mimic the actions
        performed by the upstream VC system on the tree such as
        renames, deletions and adds.  This is an useful argument to
        feed as `replay` to `applyUpstreamChangesets`

    initializeNewWorkingDir
        to initialize a pristine working directory tree under this VC
        system, possibly extracted under a different kind of VC
    
    Subclasses MUST override at least the _underscoredMethods.
    """

    def replayChangeset(self, root, module, changeset,
                        delayed_commit=False, logger=None):
        """
        Do whatever is needed to replay the changes under the target
        VC, to register the already applied (under the other VC)
        changeset.

        If `delayed_commit` is not True, the changeset is committed
        to the target VC right after a successful application; otherwise
        the various information get registered and will be reused later,
        by commitDelayedChangesets().
        """

        try:
            self._replayChangeset(root, changeset, logger)
        except:
            if logger: logger.critical(str(changeset))
            raise
        
        if delayed_commit:
            self.__registerAppliedChangeset(changeset)
        else:
            from os.path import split

            remark = '%s: changeset %s' % (module, changeset.revision)
            changelog = changeset.log
            entries = [e.name for e in changeset.entries]
            self._commit(root, changeset.date, changeset.author,
                         remark, changelog, entries)

    def commitDelayedChangesets(self, root, concatenate_logs=True):
        """
        If there are changesets pending to be committed, do a single
        commit of all changed entries.

        With `concatenate_logs` there's control over the folded
        changesets message log: if True every changelog is appended in
        order of application, otherwise it will contain just the name
        of the patches.
        """

        from datetime import datetime
        
        if not hasattr(self, '_registered_cs'):
            return

        mindate = maxdate = None
        combined_entries = {}
        combined_log = []
        combined_authors = {}
        for cs in self._registered_cs:
            if not mindate or mindate>cs.date:
                mindate = cs.date
            if not maxdate or maxdate<cs.date:
                maxdate = cs.date

            if concatenate_logs:
                msg = 'changeset %s by %s' % (cs.revision, cs.author)
                combined_log.append(msg)
                combined_log.append('=' * len(msg))
                combined_log.append(cs.log)
            else:
                combined_log.append('* changeset %s by %s' % (cs.revision,
                                                              cs.author))
            combined_authors[cs.author] = True
            
            for e in [e.name for e in cs.entries]:
                combined_entries[e] = True

        authors = ', '.join(combined_authors.keys())
        remark = 'Merged %d changesets from %s to %s' % (
            len(self._registered_cs), mindate, maxdate)
        changelog = '\n'.join(combined_log)
        entries = combined_entries.keys()
        self._commit(root, datetime.now(), authors,
                         remark, changelog, entries)
    
    def _replayChangeset(self, root, changeset, logger):
        """
        Replicate the actions performed by the changeset on the tree of
        files.
        """

        added = changeset.addedEntries()
        renamed = changeset.renamedEntries()
        removed = changeset.removedEntries()

        # Sort entries, to be sure added directories come before their
        # entries.
        added.sort(lambda x,y: cmp(x.name, y.name))

        # Likewise, sort removed one, but in reverse order
        removed.sort(lambda x,y: cmp(y.name, x.name))
                
        for e in added:
            self._addEntry(root, e.name)

        for e in renamed:
            self._renameEntry(root, e.old_name, e.name)

        for e in removed:
            self._removeEntry(root, e.name)
            
    def __registerAppliedChangeset(self, changeset):
        """
        Remember about an already applied but not committed changeset,
        to be done later.
        """
        
        if not hasattr(self, '_registered_cs'):
            self._registered_cs = []

        self._registered_cs.append(changeset)
        
    def _addEntry(self, root, entry):
        """
        Add a new entry.
        """

        raise "%s should override this method" % self.__class__

    def _commit(self, root, date, author, remark,
                changelog=None, entries=None):
        """
        Commit the changeset.
        """
        
        raise "%s should override this method" % self.__class__
        
    def _removeEntry(self, root, entry):
        """
        Remove an entry.
        """

        raise "%s should override this method" % self.__class__

    def _renameEntry(self, root, oldentry, newentry):
        """
        Rename an entry.
        """

        raise "%s should override this method" % self.__class__

    def initializeNewWorkingDir(self, root, repository, module, subdir, revision):
        """
        Initialize a new working directory, just extracted from
        some other VC system, importing everything's there.
        """

        from datetime import datetime

        now = datetime.now()
        self._initializeWorkingDir(root, repository, module, subdir)
        self._commit(root, now, '%s@%s' % (AUTHOR, HOST),
                     BOOTSTRAP_PATCHNAME % module,
                     BOOTSTRAP_CHANGELOG % locals(),
                     entries=[subdir])

    def _initializeWorkingDir(self, root, repository, module, subdir, addentry=None):
        """
        Assuming the `root` directory contains a working copy `module`
        extracted from some VC repository, add it and all its content
        to the target repository.

        This implementation first runs the given `addentry`
        *SystemCommand* on the `root` directory, then it walks down
        the `root` tree executing the same command on each entry
        excepted the usual VC-specific control directories such as
        ``.svn``, ``_darcs`` or ``CVS``.

        If this does make sense, subclasses should just call this
        method with the right `addentry` command.
        """

        assert addentry, "Subclass should have specified something as addentry"
        
        from os.path import split, join
        from os import walk

        if module:
            c = addentry(working_dir=root)
            c(entry=repr(module))

        for dir, subdirs, files in walk(join(root, module or '')):
            for excd in ['.svn', '_darcs', 'CVS']:
                if excd in subdirs:
                    subdirs.remove(excd)

            c = addentry(working_dir=dir)
            c(entry=' '.join([repr(e) for e in subdirs+files]))

