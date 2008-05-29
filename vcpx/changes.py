# -*- mode: python; coding: utf-8 -*-
# :Progetto: vcpx -- Changesets
# :Creato:   ven 11 giu 2004 15:31:18 CEST
# :Autore:   Lele Gaifax <lele@nautilus.homeip.net>
# :Licenza:  GNU General Public License
#

"""
Changesets are an object representation of a set of changes to some files.
"""

__docformat__ = 'reStructuredText'

from vcpx import TailorBug

class ChangesetEntry(object):
    """
    Represent a changed entry in a Changeset.

    For our scope, this simply means an entry ``name``, the original
    ``old_revision``, the ``new_revision`` after this change, an
    ``action_kind`` to denote the kind of change, and finally a ``status``
    to indicate possible conflicts.
    """

    ADDED = 'ADD'
    DELETED = 'DEL'
    UPDATED = 'UPD'
    RENAMED = 'REN'

    APPLIED = 'APPLIED'
    CONFLICT = 'CONFLICT'

    def __init__(self, name):
        self.name = name
        self.old_name = None
        self.old_revision = None
        self.new_revision = None
        self.action_kind = None
        self.status = None
        self.unidiff = None # This is the unidiff of this particular entry
        self.is_directory = False # This usually makes sense only on ADDs and DELs

    def __str__(self):
        s = self.name + '(' + self.action_kind
        if self.action_kind == self.ADDED:
            if self.new_revision:
                s += ' at ' + self.new_revision
        elif self.action_kind == self.UPDATED:
            if self.new_revision:
                s += ' to ' + self.new_revision
        elif self.action_kind == self.DELETED:
            if self.new_revision:
                s += ' at ' + self.new_revision
        elif self.action_kind == self.RENAMED:
            s += ' from ' + self.old_name
        else:
            s += '??'
        s += ')'
        if isinstance(s, unicode):
            s = s.encode('ascii', 'replace')
        return s

    def __eq__(self, other):
        return (self.name == other.name and
                self.old_name == other.old_name and
                self.old_revision == other.old_revision and
                self.new_revision == other.new_revision and
                self.action_kind == other.action_kind)

    def __ne__(self, other):
        return (self.name != other.name or
                self.old_name != other.old_name or
                self.old_revision != other.old_revision or
                self.new_revision != other.new_revision or
                self.action_kind != other.action_kind)

from textwrap import TextWrapper
from re import compile, MULTILINE

itemize_re = compile('^[ ]*[-*] ', MULTILINE)

def refill(msg):
    """
    Refill a changelog message.

    Normalize the message reducing multiple spaces and newlines to single
    spaces, recognizing common form of ``bullet lists``, that is paragraphs
    starting with either a dash "-" or an asterisk "*".
    """

    wrapper = TextWrapper()
    res = []
    items = itemize_re.split(msg.strip())

    if len(items)>1:
        # Remove possible first empty split, when the message immediately
        # starts with a bullet
        if not items[0]:
            del items[0]

        if len(items)>1:
            wrapper.initial_indent = '- '
            wrapper.subsequent_indent = ' '*2

    for item in items:
        if item:
            words = filter(None, item.strip().replace('\n', ' ').split(' '))
            normalized = ' '.join(words)
            res.append(wrapper.fill(normalized))

    return '\n\n'.join(res)


class Changeset(object):
    """
    Represent a single upstream Changeset.

    This is a container of each file affected by this revision of the tree.
    """

    ANONYMOUS_USER = "anonymous"
    """Author name when it is not known"""

    REFILL_MESSAGE = False
    """Refill changelogs"""

    def _get_date(self):
        try:
            return self.__date
        except AttributeError, e:
            # handle state-file Changesets created with previous versions of tailor
            from vcpx.tzinfo import UTC
            self.__date = self.__dict__['date'].replace(tzinfo=UTC)
            return self.__date

    def _set_date(self, date):
        if date and date.tzinfo is None:
            raise TailorBug("Changeset dates must have a timezone!")
        self.__date = date

    # date has to be a property because some backends (eg. monotone)
    # update it after the constructor
    date = property(_get_date, _set_date)

    def __init__(self, revision, date, author, log, entries=None, **other):
        """
        Initialize a new Changeset.
        """

        self.revision = revision
        self.date = date
        # Author name may be missing, to mean a check in made by an
        # anonymous user.
        self.author = author or self.ANONYMOUS_USER
        self.setLog(log)
        self.entries = entries or []
        self.unidiff = None        # This is the unidiff of the whole changeset
        self.tags = other.get('tags', None)

    # Don't take into account the entries, to compare changesets, because they
    # may be loaded after changeset application: the not-yet-applied changeset
    # will be different from the same-but-just-applied one.

    def __eq__(self, other):
        return (self.revision == other.revision and
                self.date == other.date and
                self.author == other.author)

    def __ne__(self, other):
        return (self.revision <> other.revision or
                self.date <> other.date or
                self.author <> other.author)

    def setLog(self, log):
        if self.REFILL_MESSAGE:
            self.log = refill(log)
        else:
            self.log = log

    def addEntry(self, entry, revision, before=None):
        """
        Facility to add an entry, eventually before another one.
        """

        e = ChangesetEntry(entry)
        e.new_revision = revision
        if before is None:
            self.entries.append(e)
        else:
            self.entries.insert(self.entries.index(before), e)
        return e

    def __str__(self):
        s = []
        s.append('Revision: %s' % self.revision)
        s.append('Date: %s' % str(self.date))
        s.append('Author: %s' % self.author)
        s.append('Entries: %s' % ', '.join([str(x) for x in self.entries]))
        s.append('Log: %s' % self.log)
        s = '\n'.join(s)
        if isinstance(s, unicode):
            s = s.encode('ascii', 'replace')
        return s

    def applyPatch(self, working_dir, patch_options="-p1"):
        """
        Apply the changeset using ``patch(1)`` to a given directory.
        """

        from shwrap import ExternalCommand
        from source import ChangesetApplicationFailure

        if self.unidiff:
            cmd = ["patch"]
            if patch_options:
                if isinstance(patch_options, basestring):
                    cmd.extend(patch_options.split(' '))
                else:
                    cmd.extend(patch_options)

            patch = ExternalCommand(cwd=working_dir, command=cmd)
            patch.execute(input=self.unidiff)

            if patch.exit_status:
                raise ChangesetApplicationFailure(
                    "%s returned status %s" % (str(patch), patch.exit_status))

    def addedEntries(self):
        """
        Facility to extract a list of added entries.
        """

        return [e for e in self.entries if e.action_kind == e.ADDED]

    def modifiedEntries(self):
        """
        Facility to extract a list of modified entries.
        """

        return [e for e in self.entries if e.action_kind == e.UPDATED]

    def removedEntries(self):
        """
        Facility to extract a list of deleted entries.
        """

        return [e for e in self.entries if e.action_kind == e.DELETED]

    def renamedEntries(self):
        """
        Facility to extract a list of renamed entries.
        """

        return [e for e in self.entries if e.action_kind == e.RENAMED]
