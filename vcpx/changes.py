#! /usr/bin/python
# -*- mode: python; coding: utf-8 -*-
# :Progetto: vcpx -- Changesets 
# :Creato:   ven 11 giu 2004 15:31:18 CEST
# :Autore:   Lele Gaifax <lele@nautilus.homeip.net>
# 

"""
Changesets are an object representation of a set of changes to some files.
"""

__docformat__ = 'reStructuredText'

class ChangesetEntry(object):
    """
    Represent a changed entry in a Changeset.

    For our scope, this simply means an entry `name`, the original
    `old_revision`, the `new_revision` after this change, an
    `action_kind` to denote the kind of change, and finally a `status`
    to indicate possible conflicts.
    """
    
    ADDED = 'A'
    DELETED = 'D'
    UPDATED = 'U'
    RENAMED = 'R'

    APPLIED = 'A'
    CONFLICT = 'C'
    
    __slots__ = ('name', 'old_name',
                 'old_revision', 'new_revision',
                 'action_kind', 'status')

    def __init__(self, name):
        self.name = name
        self.old_name = None
        self.old_revision = None
        self.new_revision = None
        self.action_kind = None
        self.status = None

    def __str__(self):
        return "%s %s->%s" % (self.name, self.old_revision, self.new_revision)


from textwrap import TextWrapper
from re import compile, MULTILINE
    
itemize_re = compile('^[ ]*[-*] ', MULTILINE)

def refill(msg):
    wrapper = TextWrapper()
    s = []
    items = itemize_re.split(msg)
    if len(items)>1:
        if len(items)>2:
            if items[0]:
                wrapper.initial_indent = ' - '
                wrapper.subsequent_indent = ' '*3
            else:
                del items[0]
                
    for m in items:
        if m:
            s.append(wrapper.fill(' '.join(filter(None, m.split(' ')))))
            s.append('')

    return '\n'.join(s)


class Changeset(object):
    """
    Represent a single upstream Changeset.

    This is a container of each file affected by this revision of the tree.
    """

    def __init__(self, revision, date, author, log, entries, **other):
        """
        Initialize a new ChangeSet.
        """
        
        self.revision = revision
        self.date = date
        self.author = author
        self.log = refill(log)
        self.entries = entries

    def __str__(self):
        s = []
        s.append('Revision: %s' % self.revision)
        s.append('Date: %s' % str(self.date))
        s.append('Author: %s' % self.author)
        for ak in ['Added', 'Modified', 'Removed', 'Renamed']:
            entries = getattr(self, ak.lower()+'Entries')()
            if entries:
                s.append('%s: %s' % (ak, ','.join([e.name
                                                   for e in self.entries])))
        s.append('Log: %s' % self.log)
        return '\n'.join(s)

    def addedEntries(self):
        """
        Filter the changesets and extract the added entries.
        """
        
        return [e for e in self.entries if e.action_kind == e.ADDED]

    def modifiedEntries(self):
        """
        Filter the changesets and extract the modified entries.
        """

        return [e for e in self.entries if e.action_kind == e.UPDATED]

    def removedEntries(self):
        """
        Filter the changesets and extract the deleted entries.
        """

        return [e for e in self.entries if e.action_kind == e.DELETED]

    def renamedEntries(self):
        """
        Filter the changesets and extract the renamed entries.
        """

        return [e for e in self.entries if e.action_kind == e.RENAMED]
