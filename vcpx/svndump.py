# -*- mode: python; coding: utf-8 -*-
# :Progetto: vcpx -- Source backend reading an svndump file
# :Creato:   mer 31 ago 2005 13:17:06 CEST
# :Autore:   Lele Gaifax <lele@nautilus.homeip.net>
# :Licenza:  GNU General Public License
#

"""
This is an alternative source backend for Subversion, that incidentally
may even be better than CVS one thru the use of the ``cvs2svn`` tool.
"""

__docformat__ = 'reStructuredText'

from source import UpdatableSourceWorkingDir, \
     ChangesetApplicationFailure, GetUpstreamChangesetsFailure
from changes import ChangesetEntry, Changeset
from datetime import datetime

def changesets_from_svndump(dump, sincerev=None, module=None):
    """
    Parse a Subversion dump file and return a sequence of changesets.
    """

    def parse_field(line):
        name,value = line[:-1].split(': ')
        return name,value

    def parse_fields(line):
        fields = {}
        while line <> "\n":
            name,value = parse_field(line)
            fields[name] = value
            line = dump.readline()
        return fields

    def parse_prop(line):
        type,length = line[:-1].split(' ')
        assert type=='K'
        name = dump.read(int(length))
        dump.read(1)
        line = dump.readline()
        type,length = line[:-1].split(' ')
        assert type=='V'
        value = dump.read(int(length))
        assert dump.read(1) == '\n'
        return name,value

    def parse_props():
        props = {}
        line = dump.readline()
        while not line.startswith('PROPS-END'):
            name,value = parse_prop(line)
            props[name] = value
            line = dump.readline()
        return props

    def parse_entries():
        entries = []
        copied = {}
        end = dump.tell()
        line = dump.readline()
        while not line.startswith('Node-'):
            if line.startswith('Revision-number:'):
                dump.seek(end)
                return []
            end = dump.tell()
            line = dump.readline()

        while line.startswith('Node-path'):
            fields = parse_fields(line)
            if 'Prop-content-length' in fields:
                props = parse_props()
            if 'Text-content-length' in fields:
                textoffset = dump.tell()
                textlength = int(fields['Text-content-length'])
                dump.seek(textlength, 1)
                line = dump.readline()
                end = dump.tell()
                line = dump.readline()
            else:
                textoffset = None
                textlength = None
                end = dump.tell()
                line = dump.readline()

            entry = ChangesetEntry(fields['Node-path'])
            action = fields['Node-action']
            entry.action_kind = {'change': ChangesetEntry.UPDATED,
                                 'add': ChangesetEntry.ADDED,
                                 'delete': ChangesetEntry.DELETED}[action]
            entry.text_offset = textoffset
            entry.text_length = textlength

            if 'Node-copyfrom-path' in fields:
                entry.old_name = fields['Node-copyfrom-path']
                copied[entry.old_name] = entry

            if action == 'delete' and entry.name in copied:
                renamed = copied[entry.name]
                renamed.action_kind = ChangesetEntry.RENAMED
            else:
                if module is None or entry.name.startswith(module):
                    if module is not None:
                        # remove the module prefix
                        entry.name = entry.name[len(module):]
                        if entry.old_name and entry.old_name.startswith(module):
                            entry.old_name = entry.old_name[len(module):]
                    entries.append(entry)

            while line == '\n':
                end = dump.tell()
                line = dump.readline()

        dump.seek(end)

        return entries

    def parse_revision(rev):
        fname, proplength = parse_field(dump.readline())
        assert fname=='Prop-content-length', fname
        fname, contentlength = parse_field(dump.readline())
        assert dump.readline() == '\n'

        props = parse_props()
        assert dump.readline() == '\n'
        entries = parse_entries()
        if entries:
            svndate = props['svn:date']
            y,m,d = map(int, svndate[:10].split('-'))
            hh,mm,ss = map(int, svndate[11:19].split(':'))
            ms = int(svndate[20:-1])
            timestamp = datetime(y, m, d, hh, mm, ss, ms)
            cs = Changeset(rev, timestamp, props.get('svn:author'),
                           props.get('svn:log', ''), entries)
            return cs

    dump.seek(0)
    format = dump.readline()
    assert format=="SVN-fs-dump-format-version: 2\n", format
    dump.readline()
    line = dump.readline()
    if line.startswith('UUID'):
        dump.readline()
        line = dump.readline()

    csets = []
    while True:
        if line.startswith('Revision-number:'):
            fname, rev = parse_field(line)
            rev = int(rev)
            cs = parse_revision(rev)
            if cs is not None and (sincerev is None or rev>=sincerev):
                csets.append(cs)
            line = dump.readline()
            while line and line=='\n':
                line = dump.readline()
        else:
            break
    return csets

class SvndumpWorkingDir(UpdatableSourceWorkingDir):

    ## UpdatableSourceWorkingDir

    def _getUpstreamChangesets(self, sincerev=None):
        if sincerev is None or sincerev == 'INITIAL':
            sincerev = 1
        else:
            sincerev = int(sincerev)

        return changesets_from_svndump(self.svndump, sincerev,
                                       self.repository.module)

    def __getEntryContent(self, entry):
        if entry.text_length:
            self.svndump.seek(entry.text_offset)
            return self.svndump.read(entry.text_length)
        else:
            return ""

    def _applyChangeset(self, changeset):
        from os.path import join, exists, dirname, split, isdir
        from os import listdir, makedirs, unlink, rename
        from shutil import rmtree

        for e in changeset.entries:
            content = self.__getEntryContent(e)
            path = join(self.basedir, e.name)
            dir = split(path)[0]

            if e.action_kind == e.UPDATED:
                if not exists(dir):
                    makedirs(dir)
                if not isdir(path):
                    file = open(path, 'w')
                    file.write(content)
                    file.close()
            elif e.action_kind == e.DELETED:
                if exists(path):
                    if isdir(path):
                        rmtree(path)
                    else:
                        unlink(path)
            elif e.action_kind in (e.ADDED, e.RENAMED):
                if not exists(dir):
                    makedirs(dir)
                if e.text_length is None:
                    if e.action_kind == e.RENAMED:
                        rename(join(self.basedir, e.old_name), path)
                    else:
                        if not exists(path):
                            makedirs(path)
                else:
                    file = open(path, 'w')
                    file.write(content)
                    file.close()
                    if e.action_kind == e.RENAMED:
                        if exists(join(self.basedir, e.old_name)):
                            unlink(join(self.basedir, e.old_name))

    def _checkoutUpstreamRevision(self, revision):
        if revision is None or revision == 'INITIAL':
            torev = -1
        else:
            torev = int(revision)
        last = None
        for cs in self._getUpstreamChangesets():
            if torev>=0 and cs.revision>torev:
                break
            self._applyChangeset(cs)
            last = cs
            if torev==-1:
                break

        if last is None:
            from vcpx.target import TargetInitializationFailure
            raise TargetInitializationFailure(
                "Couldn't initialize the source working copy at %d, "
                "no changesets found." % torev)

        self.log_info("Working copy up to svndump revision %s" % last.revision)
        return last

    def _prepareSourceRepository(self):
        self.svndump = open(self.repository.repository, 'rU')
