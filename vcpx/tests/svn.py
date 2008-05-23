# -*- mode: python; coding: utf-8 -*-
# :Progetto: vcpx -- svn specific tests
# :Creato:   gio 11 nov 2004 19:09:06 CET
# :Autore:   Lele Gaifax <lele@nautilus.homeip.net>
# :Licenza:  GNU General Public License
#

from unittest import TestCase
from datetime import datetime
from vcpx.repository.svn import changesets_from_svnlog
from vcpx.tzinfo import UTC


class FakeLogger:
    def warning(self, *args):
        pass


class FakeRepository:
    def __init__(self, repo, module):
        self.repository = repo
        self.module = module
        self.log = FakeLogger()
FR = FakeRepository


class SvnLogParser(TestCase):
    """Ensure the svn log parser does its job"""

    def getSvnLog(self, testname):
        from os.path import join, split

        logname = join(split(__file__)[0], 'data', testname)+'.log'
        return file(logname)

    def testRenameBehaviour(self):
        """Verify svn log parser behaves correctly on renames"""

        log = self.getSvnLog('svn-simple_rename_test')
        csets = changesets_from_svnlog(log, FR('file:///tmp/t/repo', '/trunk'))

        cset = csets.next()
        self.assertEqual(cset.author, 'lele')
        self.assertEqual(cset.date, datetime(2004,11,12,15,05,37,134366,UTC))
        self.assertEqual(cset.log, 'create tree')
        self.assertEqual(len(cset.entries), 2)

        entry = cset.entries[0]
        self.assertEqual(entry.name, 'dir')
        self.assertEqual(entry.action_kind, entry.ADDED)

        entry = cset.entries[1]
        self.assertEqual(entry.name, 'dir/a.txt')
        self.assertEqual(entry.action_kind, entry.ADDED)

        cset = csets.next()
        self.assertEqual(cset.author, 'lele')
        self.assertEqual(cset.date, datetime(2004,11,12,15,06,04,193650,UTC))
        self.assertEqual(cset.log, 'rename dir')
        self.assertEqual(len(cset.entries), 1)

        entry = cset.entries[0]
        self.assertEqual(entry.name, 'new')
        self.assertEqual(entry.action_kind, entry.RENAMED)
        self.assertEqual(entry.old_name, 'dir')

        self.assertRaises(StopIteration, csets.next)

    def testRenameOutBehaviour(self):
        """Verify svn log parser behaves correctly on renames out of scope"""

        log = self.getSvnLog('svn-rename_out_test')
        csets = changesets_from_svnlog(log,
                                       FR('http://srv/svn/Shtoom', '/trunk'))

        cset = csets.next()
        self.assertEqual(cset.author, 'anthony')
        self.assertEqual(cset.date, datetime(2004,11,9,6,54,20,709243,UTC))
        self.assertEqual(cset.log, 'Moving to a /sandbox\n')
        self.assertEqual(len(cset.entries), 1)

        entry = cset.entries[0]
        self.assertEqual(entry.name, 'shtoom/tmp')
        self.assertEqual(entry.action_kind, entry.DELETED)

        self.assertRaises(StopIteration, csets.next)

    def testCopyAndRename(self):
        """Verify svn log parser behaves correctly on copies"""

        log = self.getSvnLog('svn-copy_and_rename_test')
        csets = list(changesets_from_svnlog(log,
                                            FR('file:///tmp/rep', '/test')))
        self.assertEqual(len(csets), 4)

        cset = csets[1]
        self.assertEqual(cset.author, 'lele')
        self.assertEqual(cset.date, datetime(2005,1,8, 17,36,55,174757,UTC))
        self.assertEqual(cset.log, 'Copy')
        self.assertEqual(len(cset.entries), 1)

        entry = cset.entries[0]
        self.assertEqual(entry.name, 'file2.txt')
        self.assertEqual(entry.action_kind, entry.ADDED)
        self.assertEqual(entry.old_name, 'file1.txt')

        cset = csets[2]
        self.assertEqual(cset.date, datetime(2005,1,8, 17,42,41,347315,UTC))
        self.assertEqual(cset.log, 'Remove')
        self.assertEqual(len(cset.entries), 1)

        entry = cset.entries[0]
        self.assertEqual(entry.name, 'file1.txt')
        self.assertEqual(entry.action_kind, entry.DELETED)

        cset = csets[3]
        self.assertEqual(cset.date, datetime(2005,1,8, 17,43,9,909127,UTC))
        self.assertEqual(cset.log, 'Move')
        self.assertEqual(len(cset.entries), 1)

        entry = cset.entries[0]
        self.assertEqual(entry.name, 'file1.txt')
        self.assertEqual(entry.action_kind, entry.RENAMED)
        self.assertEqual(entry.old_name, 'file2.txt')

    def testREvent(self):
        """Verify how tailor handle svn "R" event"""

        log = self.getSvnLog('svn-svn_r_event_test')
        csets = changesets_from_svnlog(log, FR('file:///tmp/rep', '/trunk'))

        cset = csets.next()

        cset = csets.next()
        self.assertEqual(cset.author, 'cmlenz')
        self.assertEqual(cset.date, datetime(2005,3,21, 8,34, 2,522947,UTC))
        self.assertEqual(len(cset.entries), 7)

        entry = cset.entries[0]
        self.assertEqual(entry.name, 'setup.py')
        self.assertEqual(entry.action_kind, entry.UPDATED)

        entry = cset.entries[1]
        self.assertEqual(entry.name, 'trac/scripts')
        self.assertEqual(entry.action_kind, entry.ADDED)

        entry = cset.entries[2]
        self.assertEqual(entry.name, 'trac/scripts/__init__.py')
        self.assertEqual(entry.action_kind, entry.ADDED)

        entry = cset.entries[3]
        self.assertEqual(entry.name, 'trac/scripts/admin.py')
        self.assertEqual(entry.action_kind, entry.RENAMED)
        self.assertEqual(entry.old_name, 'scripts/trac-admin')

        entry = cset.entries[4]
        self.assertEqual(entry.name, 'trac/tests/environment.py')
        self.assertEqual(entry.action_kind, entry.UPDATED)

        entry = cset.entries[6]
        self.assertEqual(entry.name, 'scripts/trac-admin')
        self.assertEqual(entry.action_kind, entry.ADDED)

        self.assertRaises(StopIteration, csets.next)

    def testTrackingRoot(self):
        """Verify we are able to track the root of the repository"""

        log = self.getSvnLog('svn-svn_repos_root_test')
        csets = list(changesets_from_svnlog(log,
                                            FR('svn+ssh://caia/tmp/svn', '/')))
        self.assertEqual(len(csets), 4)

        cset = csets[1]
        self.assertEqual(len(cset.entries), 3)

        entry = cset.entries[0]
        self.assertEqual(entry.name, 'branches/branch-a')
        self.assertEqual(entry.action_kind, entry.ADDED)

        entry = cset.entries[1]
        self.assertEqual(entry.name, 'branches/branch-a/a.txt')
        self.assertEqual(entry.action_kind, entry.ADDED)

        entry = cset.entries[2]
        self.assertEqual(entry.name, 'branches/branch-a/b.txt')
        self.assertEqual(entry.action_kind, entry.ADDED)

    def testPydistStrangeCase(self):
        """Verify we are able to groke with svn 'R' strangeness"""

        log = self.getSvnLog('svn-pydist_strange_case')
        csets = changesets_from_svnlog(log, FR('http://srv/svn', '/py/dist'))

        cset = csets.next()
        self.assertEqual(len(cset.entries), 3)

        entry = cset.entries[0]
        self.assertEqual(entry.name, 'py/documentation/example')
        self.assertEqual(entry.action_kind, entry.RENAMED)
        self.assertEqual(entry.old_name, 'example')

        entry = cset.entries[1]
        self.assertEqual(entry.name, 'py/documentation/test.txt')
        self.assertEqual(entry.action_kind, entry.UPDATED)

        entry = cset.entries[2]
        self.assertEqual(entry.name, 'py/documentation/example/test')
        self.assertEqual(entry.action_kind, entry.ADDED)

        self.assertRaises(StopIteration, csets.next)

    def testUnicode(self):
        """Verify svn parser returns unicode strings"""

        log = self.getSvnLog('svn-encoding_test')
        csets = changesets_from_svnlog(log, FR('http://srv/plone/CMFPlone',
                                               '/branches/2.1'))

        log = csets.next().log
        self.assertEqual(type(log), type(u'€'))
        self.assertEqual(len(log), 91)
        self.assertRaises(UnicodeEncodeError, log.encode, 'iso-8859-1')
        self.assertEqual(len(log.encode('ascii', 'ignore')), 90)

        self.assertRaises(StopIteration, csets.next)

    def testCopyAndReplace(self):
        """Verify the svn parser handle copy+replace"""

        log = self.getSvnLog('svn-copy_and_replace_test')
        csets = changesets_from_svnlog(log,
                                       FR('http://srv/repos/trac', '/trunk'))

        cset = csets.next()
        self.assertEqual(len(cset.entries), 7)

        entry = cset.entries[0]
        self.assertEqual(entry.name, 'setup.py')
        self.assertEqual(entry.action_kind, entry.UPDATED)

        entry = cset.entries[1]
        self.assertEqual(entry.name, 'trac/scripts')
        self.assertEqual(entry.action_kind, entry.ADDED)

        entry = cset.entries[2]
        self.assertEqual(entry.name, 'trac/scripts/__init__.py')
        self.assertEqual(entry.action_kind, entry.ADDED)

        entry = cset.entries[3]
        self.assertEqual(entry.name, 'trac/scripts/admin.py')
        self.assertEqual(entry.action_kind, entry.RENAMED)
        self.assertEqual(entry.old_name, 'scripts/trac-admin')

        entry = cset.entries[4]
        self.assertEqual(entry.name, 'trac/tests/environment.py')
        self.assertEqual(entry.action_kind, entry.UPDATED)

        entry = cset.entries[5]
        self.assertEqual(entry.name, 'trac/tests/tracadmin.py')
        self.assertEqual(entry.action_kind, entry.UPDATED)

        entry = cset.entries[6]
        self.assertEqual(entry.name, 'scripts/trac-admin')
        self.assertEqual(entry.action_kind, entry.ADDED)

    def testCopyFromAndRemove(self):
        """Verify the svn parser handle copyfrom+remove"""

        log = self.getSvnLog('svn-copyfrom_and_remove_test')
        csets = changesets_from_svnlog(log, FR('http://srv/samba',
                                               '/branches/SAMBA_4_0'))

        cset = csets.next()
        self.assertEqual(len(cset.entries), 4)

        entry = cset.entries[0]
        self.assertEqual(entry.name, 'source/nsswitch')
        self.assertEqual(entry.action_kind, entry.ADDED)

        entry = cset.entries[1]
        self.assertEqual(entry.name, 'source/nsswitch/config.m4')
        self.assertEqual(entry.action_kind, entry.ADDED)

        entry = cset.entries[2]
        self.assertEqual(entry.name, 'source/nsswitch/wb_common.c')
        self.assertEqual(entry.action_kind, entry.ADDED)

        entry = cset.entries[3]
        self.assertEqual(entry.name, 'source/nsswitch/wins.c')
        self.assertEqual(entry.action_kind, entry.DELETED)

    def testIncrementalParser(self):
        """Verify that the svn log parser is effectively incremental"""

        log = self.getSvnLog('svn-svn_repos_root_test')
        csets = list(changesets_from_svnlog(log,
                                            FR('svn+ssh://caia/tmp/svn', '/'),
                                            chunksize=100))
        self.assertEqual(len(csets), 4)

    def testExternalCopies(self):
        """Verify that external copies+deletions are handled ok"""

        log = self.getSvnLog('svn-external_copies_test')
        csets = changesets_from_svnlog(log,
                                       FR('svn+ssh://caia/tmp/svn', '/trunk'))

        cset = csets.next()
        cset = csets.next()
        self.assertEqual(len(cset.entries), 5)

        entry = cset.removedEntries()[0]
        self.assertEqual(entry.name, 'README_LOGIN')

        cset = csets.next()
        self.assertEqual(len(cset.entries), 5)

    def testCollidingNames(self):
        """Verify svn log parser behaves correctly with colliding names"""

        # Sorry, couldn't find a better name

        log = self.getSvnLog('svn-colliding_names_test')
        csets = changesets_from_svnlog(log,
                                       FR('svn://ixion.tartarus.org/main', '/putty'))

        cset = csets.next()
        self.assertEqual(len(cset.entries), 1)
