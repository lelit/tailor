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

