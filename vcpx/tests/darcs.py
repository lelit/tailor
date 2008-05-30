# -*- mode: python; coding: utf-8 -*-
# :Progetto: vcpx -- Darcs specific tests
# :Creato:   sab 17 lug 2004 02:33:41 CEST
# :Autore:   Lele Gaifax <lele@nautilus.homeip.net>
# :Licenza:  GNU General Public License
#

from datetime import datetime
from StringIO import StringIO
from unittest import TestCase
from vcpx.repository.darcs.source import changesets_from_darcschanges, \
     DarcsSourceWorkingDir
from vcpx.shwrap import ExternalCommand, PIPE
from vcpx.tzinfo import UTC


class DarcsParserTestCase(TestCase):

    def getDarcsOutput(self, testname, ext='.log'):
        from os.path import split, join

        logfilename = join(split(__file__)[0], 'data', testname+ext)
        return file(logfilename)


class DarcsChangesParser(DarcsParserTestCase):
    """Tests for the parser of darcs changes"""

    def testBasicBehaviour(self):
        """Verify basic darcs changes parser behaviour"""

        log = self.getDarcsOutput('darcs-simple_test')

        csets = changesets_from_darcschanges(log)

        cset = csets.next()
        self.assertEqual(cset.revision,
                         "Fix the CVS parser to omit already seen changesets")
        self.assertEqual(cset.author, "lele@nautilus.homeip.net")
        self.assertEqual(cset.date, datetime(2004, 7, 16, 12, 37, 37, 0, UTC))
        self.assertEqual(cset.log, "For some unknown reasons....")
        entry = cset.entries[0]
        self.assertEqual(entry.name, 'vcpx/cvs.py')
        self.assertEqual(entry.action_kind, entry.UPDATED)

        cset = csets.next()
        self.assertEqual(cset.revision,
                         "Svn log parser with test")
        self.assertEqual(cset.date, datetime(2004, 6, 1, 14, 5, 59, 0, UTC))
        self.assertEqual(len(cset.entries), 4)
        self.assertEqual(cset.darcs_hash,
                         '20040601140559-97f81-b669594864cb35290fbe4848e6645e73057a8caf.gz')

        entry = cset.entries[0]
        self.assertEqual(entry.name, 'cvsync/svn.py')
        self.assertEqual(entry.action_kind, entry.UPDATED)
        entry = cset.entries[1]
        self.assertEqual(entry.name, 'cvsync/tests/__init__.py')
        self.assertEqual(entry.action_kind, entry.UPDATED)
        entry = cset.entries[2]
        self.assertEqual(entry.name, 'cvsync/tests/svn.py')
        self.assertEqual(entry.action_kind, entry.ADDED)
        entry = cset.entries[3]
        self.assertEqual(entry.name, 'cvsync/tests/testrepo.dump')
        self.assertEqual(entry.action_kind, entry.ADDED)

    def testOnTailorOwnRepo(self):
        """Verify fetching unidiff of a darcs patch"""

        from os import getcwd

        patchname = 'more detailed diags on SAXException'
        changes = ExternalCommand(command=["darcs", "changes", "--xml", "--summary",
                                           "--patches", patchname])
        csets = changesets_from_darcschanges(changes.execute(stdout=PIPE, TZ='UTC')[0],
                                             unidiff=True,
                                             repodir=getcwd())
        unidiff = csets.next().unidiff
        head = unidiff.split('\n')[0]
        self.assertEqual(head, 'Thu Jun  9 20:17:11 UTC 2005  zooko@zooko.com')

    def testAllActions(self):
        """Verify darcs changes parser understand all actions"""

        log = self.getDarcsOutput('darcs-all_actions_test')

        csets = list(changesets_from_darcschanges(log))

        self.assertEqual(len(csets), 4)

        cset = csets[0]
        self.assertEqual(cset.revision, 'first')
        self.assertEqual(len(cset.entries), 2)

        entry = cset.entries[0]
        self.assertEqual(entry.name, 'a.txt')
        self.assertEqual(entry.action_kind, entry.ADDED)
        self.assertEqual(entry.is_directory, False)

        entry = cset.entries[1]
        self.assertEqual(entry.name, 'dir')
        self.assertEqual(entry.action_kind, entry.ADDED)
        self.assertEqual(entry.is_directory, True)

        cset = csets[1]
        self.assertEqual(cset.revision, 'removed')
        self.assertEqual(len(cset.entries), 1)

        entry = cset.entries[0]
        self.assertEqual(entry.name, 'dir')
        self.assertEqual(entry.action_kind, entry.DELETED)
        self.assertEqual(entry.is_directory, True)

        cset = csets[2]
        self.assertEqual(cset.revision, 'moved')
        self.assertEqual(len(cset.entries), 1)

        entry = cset.entries[0]
        self.assertEqual(entry.name, 'dir')
        self.assertEqual(entry.action_kind, entry.ADDED)
        self.assertEqual(entry.is_directory, True)

        entry = cset.entries[0]
        self.assertEqual(entry.name, 'dir')
        self.assertEqual(entry.action_kind, entry.ADDED)
        self.assertEqual(entry.is_directory, True)

        cset = csets[3]
        self.assertEqual(cset.revision, 'modified')
        self.assertEqual(len(cset.entries), 1)

        entry = cset.entries[0]
        self.assertEqual(entry.name, 'a.txt')
        self.assertEqual(entry.action_kind, entry.UPDATED)
        self.assertEqual(entry.is_directory, False)

    def testIncrementalParser(self):
        """Verify that the parser is effectively incremental"""

        log = self.getDarcsOutput('darcs-all_actions_test')

        csets = list(changesets_from_darcschanges(log, chunksize=100))
        self.assertEqual(len(csets), 4)

    def testOldDateFormat(self):
        """Verify that the parser understands date format used by old darcs"""

        log = self.getDarcsOutput('darcs-old_date_format_test')

        csets = changesets_from_darcschanges(log)

        cset = csets.next()
        self.assertEqual(cset.date, datetime(2003, 10, 14, 9, 42, 0, 0, UTC))

        cset = csets.next()
        self.assertEqual(cset.date, datetime(2003, 10, 14, 14, 2, 31, 0, UTC))

    def testRenameAndRemove(self):
        """Verify that the parser degrades rename A B+remove B to remove A"""

        log = self.getDarcsOutput('darcs-rename_then_remove_test')
        csets = changesets_from_darcschanges(log)

        cset = csets.next()
        self.assertEqual(len(cset.entries), 1)

        entry = cset.entries[0]
        self.assertEqual(entry.name, 'fileA')
        self.assertEqual(entry.action_kind, entry.DELETED)

    def testRenameAndAdd(self):
        """Verify that the parser reduce rename A B+add B to rename A B"""

        log = self.getDarcsOutput('darcs-rename_and_add_test')
        csets = changesets_from_darcschanges(log)

        cset = csets.next()
        self.assertEqual(len(cset.entries), 5)

        entry = cset.entries[0]
        self.assertEqual(entry.name, 'Autoconf.lhs.in')
        self.assertEqual(entry.action_kind, entry.ADDED)

        entry = cset.entries[1]
        self.assertEqual(entry.name, 'Makefile')
        self.assertEqual(entry.action_kind, entry.UPDATED)

        entry = cset.entries[2]
        self.assertEqual(entry.name, 'autoconf.mk.in')
        self.assertEqual(entry.action_kind, entry.UPDATED)

        entry = cset.entries[3]
        self.assertEqual(entry.name, 'configure.in')
        self.assertEqual(entry.action_kind, entry.UPDATED)

        entry = cset.entries[4]
        self.assertEqual(entry.name, 'darcs_cgi.lhs')
        self.assertEqual(entry.action_kind, entry.UPDATED)

    def testRenameAndAddDir(self):
        """Verify that the parser reduce rename A B+add B to rename A B"""

        log = self.getDarcsOutput('darcs-rename_and_add_dir_test')
        csets = changesets_from_darcschanges(log)

        cset = csets.next()
        self.assertEqual(len(cset.entries), 7)

        entry = cset.entries[0]
        self.assertEqual(entry.name, 'logos/plain_logo.png')
        self.assertEqual(entry.action_kind, entry.RENAMED)
        self.assertEqual(entry.old_name, 'logo.png')

        entry = cset.entries[1]
        self.assertEqual(entry.name, 'logos')
        self.assertEqual(entry.action_kind, entry.ADDED)

        entry = cset.entries[2]
        self.assertEqual(entry.name, 'logos/large_logo.png')
        self.assertEqual(entry.action_kind, entry.ADDED)

    def testBadOrderedXML(self):
        "Verify if the parser is able to correct the bad order produced by changes --xml"

        log = self.getDarcsOutput('darcs-bad_xml_order_test')
        csets = changesets_from_darcschanges(log)

        cset = csets.next()

        # Verify that each renamed entry is not within a directory added or renamed
        # by a following hunk
        for i,e in enumerate(cset.entries):
            if e.action_kind == e.RENAMED:
                postadds = [n.name for n in cset.entries[i+1:]
                            if ((e.name.startswith(n.name+'/') or (e.old_name==n.name)) and
                                (n.action_kind==n.ADDED or n.action_kind==n.RENAMED))]
                self.assertEqual(postadds, [])

    def testAddAndRename(self):
        "Verify if the parser degrades (add A)+(rename A B) to (add B)"

        log = self.getDarcsOutput('darcs-add_then_rename_test')
        csets = changesets_from_darcschanges(log)

        cset = csets.next()

        entry = cset.entries[2]
        self.assertEqual(entry.name, 'vcpx/repository/git/__init__.py')
        self.assertEqual(entry.action_kind, entry.ADDED)

        log = self.getDarcsOutput('darcs-mixed_test')
        csets = changesets_from_darcschanges(log)

        cset = csets.next()
        self.assertEqual([], [e for e in cset.entries if e.name == 'ancillary/mbox2rpc.py'])
        self.assertEqual([], [e for e in cset.entries if e.action_kind == e.RENAMED])

    def testAddRenameEdit(self):
        "Verify if the parser degrades (rename A B)+(add A)+(edit B) to (rename A B)+(edit B)"

        log = self.getDarcsOutput('darcs-rename_add_edit_test')
        csets = changesets_from_darcschanges(log)

        cset = csets.next()
        self.assertEqual(len(cset.entries), 5)

        entry = cset.entries[0]
        self.assertEqual(entry.name, 'vcpx/repository/git')
        self.assertEqual(entry.is_directory, True)
        self.assertEqual(entry.action_kind, entry.ADDED)

        entry = cset.entries[1]
        self.assertEqual(entry.name, 'vcpx/repository/git/target.py')
        self.assertEqual(entry.old_name, 'vcpx/repository/git.py')
        self.assertEqual(entry.action_kind, entry.RENAMED)

        entry = cset.entries[2]
        self.assertEqual(entry.name, 'vcpx/repository/git/__init__.py')
        self.assertEqual(entry.action_kind, entry.ADDED)

        entry = cset.entries[3]
        self.assertEqual(entry.name, 'vcpx/repository/git/source.py')
        self.assertEqual(entry.action_kind, entry.ADDED)

        entry = cset.entries[4]
        self.assertEqual(entry.name, 'vcpx/repository/git/target.py')
        self.assertEqual(entry.action_kind, entry.UPDATED)

    def testAddAndRemove(self):
        "Verify if the parser annihilate (add A)+(remove A)"

        log = self.getDarcsOutput('darcs-add_then_remove_test')
        csets = changesets_from_darcschanges(log)

        cset = csets.next()

        self.assertEqual([], [e for e in cset.entries
                              if e.name == 'Carpet/CarpetWeb/binaries/darcs-1.0.3-static-linux-i386.gz'])


class DarcsPullParser(DarcsParserTestCase):
    """Tests for the parser of darcs pull"""

    def testParsePull(self):
        """Verify basic darcs pull parser behaviour"""

        from vcpx.changes import Changeset

        output = self.getDarcsOutput('darcs-pull_parser_test')
        hashes = self.getDarcsOutput('darcs-pull_parser_test', ext='.hashes')

        class FauxRepository(object):
            name = 'foo'
        dswd = DarcsSourceWorkingDir(FauxRepository())
        results = list(dswd._parseDarcsPull(output))

        expected_changesets = [
            Changeset('Monotone add is no longer recursive by default '
                      '(as of 2006-11-02).',
                      datetime(2006,12,12,05,30,20, tzinfo=UTC),
                      'elb@elitists.net',
                      'Use add --recursive when adding subtrees.'),
            Changeset('Fix ticket #87',
                      datetime(2006,12,14,23,45,04, tzinfo=UTC),
                      'Edgar Alves <edgar.alves@gmail.com>',
                      ''),
            Changeset("Don't assume the timestamp in darcs log is exactly "
                      "28 chars long",
                      datetime(2006,11,17,20,26,28, tzinfo=UTC),
                      'lele@nautilus.homeip.net',
                      ''),
            Changeset('tagged Version 0.9.27',
                      datetime(2006,12,11,21,07,48, tzinfo=UTC),
                      'lele@nautilus.homeip.net',
                      ''),
            Changeset('darcs: factor parsing from process invocation in DarcsSourceWorkingDir._getUpstreamChangesets',
                      datetime(2007, 1, 6, 1,52,50, tzinfo=UTC),
                      'Kevin Turner <kevin@janrain.com>',
                      ''),
            ]
        for changeset, expected_hash in zip(expected_changesets, hashes):
            changeset.darcs_hash = expected_hash.strip()

        self.failUnlessEqual(len(expected_changesets), len(results))

        for expected, result in zip(expected_changesets, results):
            self.failUnlessEqual(expected, result,
                                 "%s != %s" % (expected, result))
            self.failUnlessEqual(expected.darcs_hash, result.darcs_hash,
                                 'hash failed for %s\n %s !=\n %s' %
                                 (result, expected.darcs_hash,
                                  result.darcs_hash))

        output = self.getDarcsOutput('darcs-pull_parser_test2')
        results = list(dswd._parseDarcsPull(output))
        first = results[0]
        self.failUnlessEqual(first.revision, 'Added some basic utility functions')
        self.failUnlessEqual(first.date, datetime(2003,10,10,16,23,44, tzinfo=UTC))
        self.failUnlessEqual(first.author, 'John Goerzen <jgoerzen@complete.org>')
        self.failUnlessEqual(first.log, '\n\n(jgoerzen@complete.org--projects/tla-buildpackage--head--1.0--patch-2)')
        last = results[-1]
        self.failUnlessEqual(last.log, 'Keywords:\n\nAdded some code in Python to get things going.\n')
