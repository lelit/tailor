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

    SIMPLE_TEST = """\
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

    def testBasicBehaviour(self):
        """Verify basic svn log parser behaviour"""

        log = StringIO(self.SIMPLE_TEST)
        csets = changesets_from_svnlog(log, 'http://server/svn/Shtoom/trunk')
        self.assertEqual(len(csets), 1)

        cset = csets[0]
        self.assertEqual(cset.author, 'anthony')
        self.assertEqual(cset.date, datetime(2004,11,9,6,54,20,709243))
        self.assertEqual(cset.log, 'Moving to a /sandbox')
        self.assertEqual(len(cset.entries), 2)

        entry = cset.entries[0]
        self.assertEqual(entry.name, 'shtoom/tmp')
        self.assertEqual(entry.action_kind, entry.DELETED)

        entry = cset.entries[1]
        self.assertEqual(entry.name, 'sandbox')
        self.assertEqual(entry.action_kind, entry.RENAMED)
        self.assertEqual(entry.old_name, 'shtoom/tmp')

        print cset
