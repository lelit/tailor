#! /usr/bin/python
# -*- mode: python; coding: utf-8 -*-
# :Progetto: vcpx -- basic cvs tests
# :Creato:   ven 09 lug 2004 01:43:52 CEST
# :Autore:   Lele Gaifax <lele@nautilus.homeip.net>
# 

from unittest import TestCase, TestSuite
from datetime import datetime
from StringIO import StringIO
from vcpx.cvs import changesets_from_cvsps

SIMPLE_TEST = """\
---------------------
PatchSet 1500
Date: 2004/05/09 17:54:22
Author: grubert
Branch: HEAD
Tag: (none)
Log:
Tell the reason for using mbox (not wrapping long lines).

Members: 
\tdocutils/writers/latex2e.py:1.78->1.79

"""

DOUBLE_TEST = """\
---------------------
PatchSet 819
Date: 2004/06/26 12:05:44
Author: ajung
Branch: HEAD
Tag: (none)
Log:
cleanup

Members: 
\tNormalizer.py:1.12->1.13
\tRegistry.py:1.22->1.23
\tRegistry.py:1.21->1.22
\tStopwords.py:1.9->1.10

"""

class CvspsParserTest(TestCase):
    """Ensure the cvsps parser does its job."""

    def testBasicBehaviour(self):
        """Verify basic cvsps parser behaviour"""

        log = StringIO(SIMPLE_TEST)
        csets = changesets_from_cvsps(log)

        cset = csets.next()
        self.assertEqual(cset.revision, '1500')
        self.assertEqual(cset.author, "grubert")
        self.assertEqual(cset.date, datetime(2004, 5, 9, 17, 54, 22))
        self.assertEqual(cset.log, "Tell the reason for using mbox "
                                   "(not wrapping long lines).\n")
        
    def testDoubleEntry(self):
        """Verify the parser recognizes double entries"""

        log = StringIO(DOUBLE_TEST)
        csets = changesets_from_cvsps(log)

        cset = csets.next()
        self.assertEqual(len(cset.entries), 3)

        e = cset.entries[0]
        self.assertEqual(e.name, "Normalizer.py")
        self.assertEqual(e.old_revision, '1.12')
        self.assertEqual(e.new_revision, '1.13')

        e = cset.entries[1]
        self.assertEqual(e.name, "Registry.py")
        self.assertEqual(e.old_revision, '1.21')
        self.assertEqual(e.new_revision, '1.23')

        e = cset.entries[2]
        self.assertEqual(e.name, "Stopwords.py")
        self.assertEqual(e.old_revision, '1.9')
        self.assertEqual(e.new_revision, '1.10')
