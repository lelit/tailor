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

PATCH_AUTHOR = "tailor@localhost"

class SyncronizableTargetWorkingDir(object):
    """
    This is an abstract working dir. Subclasses MUST override at least
    the _underscoredMethods.
    """

    def replayChangeset(self, root, changeset):
        """
        Do whatever is needed to replay the changes under the target
        VC, to register the already applied (under the other VC)
        changeset.
        """

        self._replayChangeset(root, changeset)
        
        remark = 'Upstream changeset %s' % changeset.revision
        changelog = changeset.log
        entries = [e.name for e in changeset.entries]
        self._commit(root, changeset.author, remark, changelog, entries)

    def _replayChangeset(self, root, changeset):
        """
        Replicate the actions performed by the changeset on the tree of
        files.
        """
        
        for e in changeset.entries:
            if e.action_kind == e.RENAMED:
                self._renameEntry(root, e.old_name, e.name)
            elif e.action_kind == e.ADDED:
                self._addEntry(root, e.name)
            elif e.action_kind == e.DELETED:
                self._removeEntry(root, e.name)
        
    def _addEntry(self, root, entry):
        """
        Add a new entry, maybe registering the directory as well.
        """

        raise "%s should override this method" % self.__class__

    def _commit(self, root, author, remark, changelog=None, entries=None):
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

    def initializeNewWorkingDir(self, root, repository, revision):
        """
        Initialize a new working directory, just extracted under
        some other VC system, importing everything's there.
        """

        self._initializeWorkingDir(root)
        self._commit(root, PATCH_AUTHOR,
                     'Tailorization of %s@%s' % (repository, revision))

    def _initializeWorkingDir(self, root):
        """
        Assuming the `root` directory is a new working copy extracted
        from some VC repository, add it and all its content to the
        target repository.
        """
        
        raise "%s should override this method" % self.__class__
