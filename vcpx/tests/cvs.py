#! /usr/bin/python
# -*- mode: python; coding: utf-8 -*-
# :Progetto: vcpx -- cvs specific tests
# :Creato:   dom 11 lug 2004 18:21:11 CEST
# :Autore:   Lele Gaifax <lele@nautilus.homeip.net>
# 

"""
"""

__docformat__ = 'reStructuredText'

from unittest import TestCase, TestSuite
from datetime import datetime
from StringIO import StringIO
from vcpx.cvs import changesets_from_cvslog

class CvsLogParserTest(TestCase):
    """Ensure the cvs log parser does its job."""

    SIMPLE_TEST = """\
RCS file: /cvsroot/docutils/docutils/THANKS.txt,v
Working file: THANKS.txt
head: 1.2
branch:
locks: strict
access list:
symbolic names:
keyword substitution: kv
total revisions: 2;      selected revisions: 2
description:
----------------------------
revision 1.2
date: 2004/06/10 02:17:20;  author: goodger;  state: Exp;  lines: +3 -2
updated
----------------------------
revision 1.1
date: 2004/06/03 13:50:58;  author: goodger;  state: Exp;
Added to project (exctracted from HISTORY.txt)
=============================================================================
"""

    DOUBLE_TEST = """\
RCS file: /cvsroot/docutils/docutils/docutils/statemachine.py,v
Working file: docutils/statemachine.py
head: 1.16
branch:
locks: strict
access list:
symbolic names:
        nesting: 1.15.0.2
        start: 1.1.1.1
        goodger: 1.1.1
keyword substitution: kv
total revisions: 17;    selected revisions: 1
description:
----------------------------
revision 1.16
date: 2004/06/17 21:46:50;  author: goodger;  state: Exp;  lines: +6 -2
support for CSV directive implementation
=============================================================================

RCS file: /cvsroot/docutils/docutils/docutils/utils.py,v
Working file: docutils/utils.py
head: 1.35
branch:
locks: strict
access list:
symbolic names:
        nesting: 1.29.0.2
        start: 1.1.1.1
        goodger: 1.1.1
keyword substitution: kv
total revisions: 36;    selected revisions: 5
description:
----------------------------
revision 1.35
date: 2004/06/20 16:03:17;  author: felixwiemann;  state: Exp;  lines: +12 -6
make warning_stream work
----------------------------
revision 1.34
date: 2004/06/17 21:46:50;  author: goodger;  state: Exp;  lines: +5 -2
support for CSV directive implementation
----------------------------
revision 1.33
date: 2004/06/17 02:51:31;  author: goodger;  state: Exp;  lines: +4 -2
docstrings
----------------------------
revision 1.32
date: 2004/06/17 02:08:48;  author: goodger;  state: Exp;  lines: +4 -2
docstrings
----------------------------
revision 1.31
date: 2004/04/27 19:51:07;  author: goodger;  state: Exp;  lines: +5 -3
updated
=============================================================================
"""
    
    def testBasicBehaviour(self):
        """Verify basic cvs log parser behaviour"""

        log = StringIO(self.SIMPLE_TEST)
        csets = changesets_from_cvslog(log)

        cset = csets.next()
        self.assertEqual(cset.author, "goodger")
        self.assertEqual(cset.date, datetime(2004, 6, 3, 13, 50, 58))
        self.assertEqual(cset.log, "Added to project (exctracted from "
                                   "HISTORY.txt)\n")
        entry = cset.entries[0]
        self.assertEqual(entry.name, 'THANKS.txt')
        self.assertEqual(entry.new_revision, '1.1')
        self.assertEqual(entry.action_kind, entry.ADDED)
        
        cset = csets.next()
        self.assertEqual(cset.author, "goodger")
        self.assertEqual(cset.date, datetime(2004, 6, 10, 2, 17, 20))
        self.assertEqual(cset.log, "updated\n") 
        entry = cset.entries[0]
        self.assertEqual(entry.name, 'THANKS.txt')
        self.assertEqual(entry.new_revision, '1.2')
        self.assertEqual(entry.action_kind, entry.UPDATED)
       
    def testDoubleBehaviour(self):
        """Verify cvs log parser behaviour"""

        log = StringIO(self.DOUBLE_TEST)
        csets = changesets_from_cvslog(log)

        cset = csets.next()
        self.assertEqual(cset.author, "goodger")
        self.assertEqual(cset.date, datetime(2004, 4, 27, 19, 51, 07))

        cset = csets.next()
        self.assertEqual(cset.author, "goodger")
        self.assertEqual(cset.date, datetime(2004, 6, 17, 2, 8, 48))

        cset = csets.next()
        self.assertEqual(cset.author, "goodger")
        self.assertEqual(cset.date, datetime(2004, 6, 17, 2, 51, 31))

        cset = csets.next()
        self.assertEqual(cset.author, "goodger")
        self.assertEqual(cset.date, datetime(2004, 6, 17, 21, 46, 50))
        self.assertEqual(cset.log,"support for CSV directive implementation\n")
        self.assertEqual(len(cset.entries), 2)

        entry = cset.entries[0]
        self.assertEqual(entry.name, 'docutils/statemachine.py')
        self.assertEqual(entry.new_revision, '1.16')
        
        entry = cset.entries[1]
        self.assertEqual(entry.name, 'docutils/utils.py')
        self.assertEqual(entry.new_revision, '1.34')
        
        cset = csets.next()
        self.assertEqual(cset.author, "felixwiemann")
        self.assertEqual(cset.date, datetime(2004, 6, 20, 16, 3, 17))
