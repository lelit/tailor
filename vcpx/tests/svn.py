#! /usr/bin/python
# -*- mode: python; coding: utf-8 -*-
# :Progetto: vcpx -- svn specific tests
# :Creato:   gio 11 nov 2004 19:09:06 CET
# :Autore:   Lele Gaifax <lele@nautilus.homeip.net>
# 

from unittest import TestCase, TestSuite
from datetime import datetime
from StringIO import StringIO
from vcpx.svn import changesets_from_svnlog

class SvnLogParserTest(TestCase):
    """Ensure the svn log parser does its job."""

    SIMPLE_RENAME_TEST = """\
<?xml version="1.0" encoding="utf-8"?>
<log>
<logentry
   revision="2">
<author>lele</author>
<date>2004-11-12T15:05:37.134366Z</date>
<paths>
<path
   action="A">/trunk/dir</path>
<path
   action="A">/trunk/dir/a.txt</path>
</paths>
<msg>create tree</msg>
</logentry>
<logentry
   revision="3">
<author>lele</author>
<date>2004-11-12T15:06:04.193650Z</date>
<paths>
<path
   action="D">/trunk/dir</path>
<path
   copyfrom-path="/trunk/dir"
   copyfrom-rev="1"
   action="A">/trunk/new</path>
</paths>
<msg>rename dir</msg>
</logentry>
</log>
"""
   
    def testRenameBehaviour(self):
        """Verify svn log parser behaves correctly on renames"""

        log = StringIO(self.SIMPLE_RENAME_TEST)
        csets = changesets_from_svnlog(log, 'file:///tmp/t/repo/trunk')
        self.assertEqual(len(csets), 2)

        cset = csets[0]
        self.assertEqual(cset.author, 'lele')
        self.assertEqual(cset.date, datetime(2004,11,12,15,05,37,134366))
        self.assertEqual(cset.log, 'create tree')
        self.assertEqual(len(cset.entries), 2)

        entry = cset.entries[0]
        self.assertEqual(entry.name, 'dir')
        self.assertEqual(entry.action_kind, entry.ADDED)
        
        entry = cset.entries[1]
        self.assertEqual(entry.name, 'dir/a.txt')
        self.assertEqual(entry.action_kind, entry.ADDED)
        
        cset = csets[1]
        self.assertEqual(cset.author, 'lele')
        self.assertEqual(cset.date, datetime(2004,11,12,15,06,04,193650))
        self.assertEqual(cset.log, 'rename dir')
        self.assertEqual(len(cset.entries), 1)

        entry = cset.entries[0]
        self.assertEqual(entry.name, 'new')
        self.assertEqual(entry.action_kind, entry.RENAMED)
        self.assertEqual(entry.old_name, 'dir')
        
    RENAME_OUT_TEST = """\
<?xml version="1.0" encoding="utf-8"?>
<log>
<logentry
   revision="894">
<author>anthony</author>
<date>2004-11-09T06:54:20.709243Z</date>
<paths>
<path
   action="D">/trunk/shtoom/tmp</path>
<path
   copyfrom-path="/trunk/shtoom/tmp"
   copyfrom-rev="893"
   action="A">/sandbox</path>
</paths>
<msg>Moving to a /sandbox
</msg>
</logentry>
</log>
"""

    def testRenameOutBehaviour(self):
        """Verify svn log parser behaves correctly on renames outside tracked tree"""

        log = StringIO(self.RENAME_OUT_TEST)
        csets = changesets_from_svnlog(log, 'http://server/svn/Shtoom/trunk')
        self.assertEqual(len(csets), 1)

        cset = csets[0]
        self.assertEqual(cset.author, 'anthony')
        self.assertEqual(cset.date, datetime(2004,11,9,6,54,20,709243))
        self.assertEqual(cset.log, 'Moving to a /sandbox')
        self.assertEqual(len(cset.entries), 1)

        entry = cset.entries[0]
        self.assertEqual(entry.name, 'shtoom/tmp')
        self.assertEqual(entry.action_kind, entry.DELETED)

    COPY_AND_RENAME_TEST = """\
<?xml version="1.0" encoding="utf-8"?>
<log>
<logentry
   revision="1">
<author>lele</author>
<date>2005-01-08T17:36:39.131126Z</date>
<paths>
<path
   action="A">/test/file1.txt</path>
</paths>
<msg>First commit</msg>
</logentry>
<logentry
   revision="2">
<author>lele</author>
<date>2005-01-08T17:36:55.174757Z</date>
<paths>
<path
   copyfrom-path="/test/file1.txt"
   copyfrom-rev="1"
   action="A">/test/file2.txt</path>
</paths>
<msg>Copy</msg>
</logentry>
<logentry
   revision="3">
<author>lele</author>
<date>2005-01-08T17:42:41.347315Z</date>
<paths>
<path
   action="D">/test/file1.txt</path>
</paths>
<msg>Remove</msg>
</logentry>
<logentry
   revision="4">
<author>lele</author>
<date>2005-01-08T17:43:09.909127Z</date>
<paths>
<path
   copyfrom-path="/test/file2.txt"
   copyfrom-rev="2"
   action="A">/test/file1.txt</path>
<path
   action="D">/test/file2.txt</path>
</paths>
<msg>Move</msg>
</logentry>
</log>
"""

    def testCopyAndRename(self):
        """Verify svn log parser behaves correctly on copies"""

        log = StringIO(self.COPY_AND_RENAME_TEST)
        csets = changesets_from_svnlog(log, 'file:///tmp/rep/test')
        self.assertEqual(len(csets), 4)

        cset = csets[1]
        self.assertEqual(cset.author, 'lele')
        self.assertEqual(cset.date, datetime(2005,1,8, 17,36,55,174757))
        self.assertEqual(cset.log, 'Copy')
        self.assertEqual(len(cset.entries), 1)

        entry = cset.entries[0]
        self.assertEqual(entry.name, 'file2.txt')
        self.assertEqual(entry.action_kind, entry.ADDED)
        self.assertEqual(entry.old_name, 'file1.txt')
        
        cset = csets[2]
        self.assertEqual(cset.date, datetime(2005,1,8, 17,42,41,347315))
        self.assertEqual(cset.log, 'Remove')
        self.assertEqual(len(cset.entries), 1)

        entry = cset.entries[0]
        self.assertEqual(entry.name, 'file1.txt')
        self.assertEqual(entry.action_kind, entry.DELETED)

        cset = csets[3]
        self.assertEqual(cset.date, datetime(2005,1,8, 17,43,9,909127))
        self.assertEqual(cset.log, 'Move')
        self.assertEqual(len(cset.entries), 1)

        entry = cset.entries[0]
        self.assertEqual(entry.name, 'file1.txt')
        self.assertEqual(entry.action_kind, entry.RENAMED)
        self.assertEqual(entry.old_name, 'file2.txt')
