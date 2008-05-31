# -*- mode: python; coding: utf-8 -*-
# :Progetto: vcpx -- cvs specific tests
# :Creato:   dom 11 lug 2004 18:21:11 CEST
# :Autore:   Lele Gaifax <lele@nautilus.homeip.net>
# :Licenza:  GNU General Public License
#

from unittest import TestCase
from datetime import datetime
from StringIO import StringIO
from vcpx.repository.cvs import changesets_from_cvslog, compare_cvs_revs, \
                                cvs_revs_same_branch, normalize_cvs_rev
from vcpx.tzinfo import UTC


class CvsEntry(TestCase):
    """Tests for the CvsEntry class"""

    def testBasicCapabilities(self):
        """Verify CvsEntry parser"""

        from datetime import datetime, timedelta
        from vcpx.repository.cvs import CvsEntry

        tagline = "/version.txt/1.16.2.1/Tue Jul 13 12:49:02 2004//T1.16.2.1"
        e = CvsEntry(tagline)
        self.assertEqual(e.filename, 'version.txt')
        self.assertEqual(e.cvs_version, '1.16.2.1')
        self.assertEqual(e.timestamp, datetime(2004, 7, 13, 12, 49, 2, 0, UTC))
        self.assertEqual(e.cvs_tag, 'T1.16.2.1')

        tagline = "/Validator.py/1.31.2.5/Result of merge+Tue Jul 13 13:43:06 2004//T1.31.2.5"
        e = CvsEntry(tagline)
        self.assertEqual(e.filename, 'Validator.py')
        self.assertEqual(e.cvs_version, '1.31.2.5')
        self.assertEqual(e.timestamp, datetime(2004, 7, 13, 13, 43, 6, 0, UTC))
        self.assertEqual(e.cvs_tag, 'T1.31.2.5')

        tagline = "/Makefile.am/1.55/Result of merge//T1.55"
        e = CvsEntry(tagline)
        self.assertEqual(e.filename, 'Makefile.am')
        self.assertEqual(e.cvs_version, '1.55')
        self.assert_((datetime.now(tz=UTC) - e.timestamp) < timedelta(seconds=1))
        self.assertEqual(e.cvs_tag, 'T1.55')


class CvsLogParser(TestCase):
    """Ensure the cvs log parser does its job"""

    def getCvsLog(self, testname, encoding='utf-8'):
        from codecs import open
        from os.path import join, split

        logname = join(split(__file__)[0], 'data', testname)+'.log'
        return open(logname, 'r', encoding)

    def testBasicBehaviour(self):
        """Verify basic cvs log parser behaviour"""

        log = self.getCvsLog('cvs-simple_test')
        csets = list(changesets_from_cvslog(log, 'docutils'))

        self.assertEqual(len(csets), 2)

        cset = csets[0]
        self.assertEqual(cset.author, "goodger")
        self.assertEqual(cset.date, datetime(2004, 6, 3, 13, 50, 58, 0, UTC))
        self.assertEqual(cset.log, "Added to project (exctracted from "
                                   "HISTORY.txt)")
        entry = cset.entries[0]
        self.assertEqual(entry.name, 'THANKS.txt')
        self.assertEqual(entry.new_revision, '1.1')
        self.assertEqual(entry.action_kind, entry.ADDED)

        cset = csets[1]
        self.assertEqual(cset.author, "goodger")
        self.assertEqual(cset.date, datetime(2004, 6, 10, 2, 17, 20, 0, UTC))
        self.assertEqual(cset.log, "")
        entry = cset.entries[0]
        self.assertEqual(entry.name, 'THANKS.txt')
        self.assertEqual(entry.new_revision, '1.2')
        self.assertEqual(entry.action_kind, entry.UPDATED)

    def testGroupingCapability(self):
        """Verify cvs log parser grouping capability"""

        log = self.getCvsLog('cvs-double_test')
        csets = changesets_from_cvslog(log, 'docutils')

        cset = csets.next()
        self.assertEqual(cset.author, "goodger")
        self.assertEqual(cset.date, datetime(2004, 4, 27, 19, 51, 07, 0, UTC))

        cset = csets.next()
        self.assertEqual(cset.author, "goodger")
        self.assertEqual(cset.date, datetime(2004, 6, 17, 2, 8, 48, 0, UTC))

        cset = csets.next()
        self.assertEqual(cset.author, "goodger")
        self.assertEqual(cset.date, datetime(2004, 6, 17, 2, 51, 31, 0, UTC))

        cset = csets.next()
        self.assertEqual(cset.author, "goodger")
        self.assertEqual(cset.date, datetime(2004, 6, 17, 21, 46, 50, 0, UTC))
        self.assertEqual(cset.log,"support for CSV directive implementation")
        self.assertEqual(len(cset.entries), 2)

        entry = cset.entries[0]
        self.assertEqual(entry.name, 'docutils/statemachine.py')
        self.assertEqual(entry.new_revision, '1.16')

        entry = cset.entries[1]
        self.assertEqual(entry.name, 'docutils/utils.py')
        self.assertEqual(entry.new_revision, '1.34')

        cset = csets.next()
        self.assertEqual(cset.author, "felixwiemann")
        self.assertEqual(cset.date, datetime(2004, 6, 20, 16, 3, 17, 0, UTC))

    def testDeletedEntry(self):
        """Verify recognition of deleted entries in the cvs log"""

        log = self.getCvsLog('cvs-deleted_test')
        csets = list(changesets_from_cvslog(log, 'docutils'))

        self.assertEqual(len(csets), 2)

        cset = csets[0]
        entry = cset.entries[0]
        self.assertEqual(entry.action_kind, entry.ADDED)

        cset = csets[1]
        entry = cset.entries[0]
        self.assertEqual(entry.name, 'THANKS.txt')
        self.assertEqual(entry.action_kind, entry.DELETED)

    def testCollapsedChangeset(self):
        """Verify the mechanism used to collapse related changesets"""

        log = self.getCvsLog('cvs-collapse_test')
        csets = list(changesets_from_cvslog(log, 'PyObjC'))

        self.assertEqual(len(csets), 5)

        cset = csets[0]
        self.assertEqual(len(cset.entries), 2)
        self.assertEqual(cset.date, datetime(1996, 10, 7, 18, 32, 12, 0, UTC))

        cset = csets[1]
        self.assertEqual(len(cset.entries), 1)
        self.assertEqual(cset.date, datetime(1996, 10, 14, 13, 56, 50, 0, UTC))
        entry = cset.entries[0]
        self.assertEqual(entry.name, 'Doc/libObjCStreams.tex')

        cset = csets[2]
        self.assertEqual(len(cset.entries), 1)
        self.assertEqual(cset.date, datetime(1996, 10, 18, 12, 36, 4, 0, UTC))
        entry = cset.entries[0]
        self.assertEqual(entry.name, 'Doc/libPyObjC.tex')

        cset = csets[3]
        self.assertEqual(len(cset.entries), 2)
        self.assertEqual(cset.date, datetime(1996, 10, 18, 13, 48, 45, 0, UTC))

    def testBranchesInLog(self):
        """Verify the parser groks with the branches info on revision"""

        log = self.getCvsLog('cvs-branches_test')
        csets = list(changesets_from_cvslog(log, 'Archetypes'))

        self.assertEqual(len(csets), 3)

        cset = csets[0]
        self.assertEqual(cset.log,"Fixed deepcopy problem in validations")

    def testReposPath(self):
        """Verify the parser is right in determine working copy file paths"""

        log = self.getCvsLog('cvs-repospath_test')
        csets = changesets_from_cvslog(log, 'Zope')

        cset = csets.next()
        self.assertEqual(cset.log,"backported copy constructor from trunk")
        self.assertEqual(len(cset.entries), 1)
        entry = cset.entries[0]
        self.assertEqual(entry.name, 'lib/python/DateTime/DateTime.py')

    def testLongLog(self):
        """Stress the parser with a very long changelog"""

        log = self.getCvsLog('cvs-longlog_test')
        csets = changesets_from_cvslog(log, 'ATContentTypes')

        cset = csets.next()
        self.assertEqual(cset.author, "tiran")
        self.assertEqual(cset.date, datetime(2004, 8, 6, 20, 13, 30, 0, UTC))
        self.assertEqual(cset.log, "Added ExtendingType")
        entry = cset.entries[0]
        self.assertEqual(entry.name, 'docs/ExtendingType.txt')
        self.assertEqual(entry.new_revision, '1.1')
        self.assertEqual(entry.action_kind, entry.ADDED)

        cset = csets.next()
        self.assertEqual(cset.author, "tiran")
        self.assertEqual(cset.date, datetime(2004, 8, 9, 7, 44, 9, 0, UTC))
        self.assertEqual(cset.log, """\
Recoded migration walkers to use a generator instead returning a list to make them much more memory efficient.

Rewritten folder migration to use the depth inside the folder structur instead of recursing into the full side.

Added a findStaledObjects external method to ATCT to find staled objects. It is very useful to clean up a site before running the migration.""")
        entry = cset.entries[0]
        self.assertEqual(entry.name, 'Extensions/batchCreate.py')
        self.assertEqual(entry.new_revision, '1.2')
        self.assertEqual(entry.action_kind, entry.UPDATED)

        cset = csets.next()
        self.assertEqual(cset.author, "tiran")
        self.assertEqual(cset.date, datetime(2004, 8, 13, 13, 15, 46, 0, UTC))
        self.assertEqual(cset.log, "Fixed typo")

        cset = csets.next()
        self.assertEqual(cset.author, "tiran")
        self.assertEqual(cset.date, datetime(2004, 8, 13, 13, 21, 24, 0, UTC))
        self.assertEqual(cset.log, "Something went wrong ...")

        cset = csets.next()
        self.assertEqual(cset.author, "tiran")
        self.assertEqual(cset.date, datetime(2004, 8, 13, 13, 21, 53, 0, UTC))
        self.assertEqual(cset.log, "Somehow I mixed up two sentences")

        cset = csets.next()
        self.assertEqual(cset.author, "rochael")
        self.assertEqual(cset.date, datetime(2004, 8, 13, 13, 59, 55, 0, UTC))
        self.assertEqual(cset.log, "removed duplicated ENABLE_TEMPLATE_MIXIN")
        entry = cset.entries[0]
        self.assertEqual(entry.name, 'customconfig.py.example')
        self.assertEqual(entry.new_revision, '1.7')
        self.assertEqual(entry.action_kind, entry.UPDATED)

    SILLY_TEST = u"""\
RCS file: /cvsroot/docutils/docutils/THANKS.txt,v
head: 1.2
"""

    def testDirectoryMissing(self):
        """Verify how parser reacts on bad input"""

        log = StringIO(self.SILLY_TEST)
        csets = changesets_from_cvslog(log, 'docutils')
        self.assertRaises(AssertionError, csets.next)

    def testInitialCreationOnBranchBehaviour(self):
        """Verify cvs log parser skip spurious entries"""

        log = self.getCvsLog('cvs-created_in_branch_test')
        csets = list(changesets_from_cvslog(log, 'dsssl-utils'))

        self.assertEqual(len(csets), 1)

    def testInitialCreationOnBranchBehaviour2(self):
        """Verify cvs log parser skip spurious entries"""

        log = self.getCvsLog('cvs-created_in_branch_2_test')
        csets = list(changesets_from_cvslog(log, 'zsh'))

        self.assertEqual(len(csets), 4)

    def testDescriptionPresent(self):
        """Verify cvs log parser handle eventual description"""

        log = self.getCvsLog('cvs-description_test')
        csets = changesets_from_cvslog(log, 'zope')

    def testAddDelAddAgain(self):
        """Verify add->delete->add/modify->modify CVS case"""

        log = self.getCvsLog('cvs-add_del_add_again_test')
        csets = list(changesets_from_cvslog(log, 'test'))

        self.assertEqual(len(csets), 6)

        cset = csets[0]
        entry = cset.entries[0]
        self.assertEqual(entry.name, 'file')
        self.assertEqual(entry.new_revision, '1.1')
        self.assertEqual(entry.action_kind, entry.ADDED)

        cset = csets[1]
        entry = cset.entries[0]
        self.assertEqual(entry.name, 'file')
        self.assertEqual(entry.new_revision, '1.2')
        self.assertEqual(entry.action_kind, entry.DELETED)

        cset = csets[2]
        entry = cset.entries[0]
        self.assertEqual(entry.name, 'file')
        self.assertEqual(entry.new_revision, '1.3')
        self.assertEqual(entry.action_kind, entry.ADDED)

    def testModules(self):
        """Verify the parser correctly handle multimodules"""

        log = self.getCvsLog('cvs-multi_module_test')
        csets = changesets_from_cvslog(log, 'apache-1.3')

    def testEntryNames(self):
        """Verify the parser removes module name from entries"""

        log = self.getCvsLog('cvs-entry_names_test')
        csets = changesets_from_cvslog(log, 'Products/PluggableAuthService')

        cset = csets.next()
        entry = cset.entries[0]
        self.assertEqual(entry.name, 'COPYRIGHT.txt')

    def testUnicode(self):
        """Verify cvs parser returns unicode strings"""

        log = self.getCvsLog('cvs-encoding_test')
        csets = changesets_from_cvslog(log, 'pxlib')

        log = csets.next().log
        self.assertEqual(type(log), type(u'€'))
        self.assertEqual(len(log), 42)
        self.assertRaises(UnicodeEncodeError, log.encode, 'ascii')
        self.assertEqual(len(log.encode('ascii', 'ignore')), 41)

    def testDoubleDead(self):
        """Verify the parser collapse multiple deletions on a single entry"""

        log = self.getCvsLog('cvs-double_dead_test')
        csets = changesets_from_cvslog(log,
                                       'composestar/temp/ComposestarVSAddin')

        cset = csets.next()
        self.assertEqual(len(cset.entries), 2)
        entry = cset.entries[0]
        self.assertEqual(entry.name, 'ComposestarVSAddin/Ini.cs')
        self.assertEqual(entry.new_revision, '1.1')
        self.assertEqual(entry.action_kind, entry.ADDED)
        entry = cset.entries[1]
        self.assertEqual(entry.name, 'ComposestarVSAddin/ConfigManager.cs')
        self.assertEqual(entry.new_revision, '1.1')
        self.assertEqual(entry.action_kind, entry.ADDED)

        cset = csets.next()
        self.assertEqual(len(cset.entries), 2)
        entry = cset.entries[0]
        self.assertEqual(entry.name, 'ComposestarVSAddin/Ini.cs')
        self.assertEqual(entry.new_revision, '1.3')
        self.assertEqual(entry.action_kind, entry.DELETED)
        entry = cset.entries[1]
        self.assertEqual(entry.name, 'ComposestarVSAddin/ConfigManager.cs')
        self.assertEqual(entry.new_revision, '1.3')
        self.assertEqual(entry.action_kind, entry.DELETED)

    def testHumanTouched(self):
        """Verify how the parser behaves with manually tweaked logs"""

        log = self.getCvsLog('cvs-human_touched')
        csets = list(changesets_from_cvslog(log, 'src'))

        cset = csets[0]
        self.assertEqual(cset.date, datetime(1994, 5, 17, 13, 03, 36, 0, UTC))

        cset = csets[-1]
        self.assertEqual(cset.date, datetime(1995, 12, 30, 18, 32, 46, 0, UTC))

class CvsRevisions(TestCase):
    """Tests the basic CVS revisions handling"""

    def testComparison(self):
        """Verify CVS revision comparison is done right"""

        self.assertEqual(0, compare_cvs_revs('1.1', '1.1'))
        self.assertEqual(-1, compare_cvs_revs('1.1', '1.3'))
        self.assertEqual(-1, compare_cvs_revs('1.5', '1.51'))
        self.assertEqual(-1, compare_cvs_revs('1.1', '1.1.2.2'))

    def testBranches(self):
        """Verify how the backend recognizes branches"""

        n = normalize_cvs_rev
        self.assertEqual(True, cvs_revs_same_branch(n('1.2'), n('1.2')))
        self.assertEqual(True, cvs_revs_same_branch(n('1.2.2'), n('1.2.2')))
        self.assertEqual(False, cvs_revs_same_branch(n('1.2.2'), n('1.2.2.3.3')))
        self.assertEqual(True, cvs_revs_same_branch(n('1.2.3.4'), n('1.2.3.4')))
        self.assertEqual(True, cvs_revs_same_branch(n('1.2'), n('1.2.3')))
        self.assertEqual(True, cvs_revs_same_branch(n('1.2.3'), n('1.2')))
