#! /usr/bin/python
# -*- mode: python; coding: utf-8 -*-
# :Progetto: vcpx -- cvs specific tests
# :Creato:   dom 11 lug 2004 18:21:11 CEST
# :Autore:   Lele Gaifax <lele@nautilus.homeip.net>
# 

from unittest import TestCase, TestSuite
from datetime import datetime
from StringIO import StringIO
from vcpx.cvs import changesets_from_cvslog, CvsEntry

class CvsEntryTest(TestCase):
    """Tests for the CvsEntry class"""

    def testBasicCapabilities(self):
        """Verify CvsEntry parser"""

        from datetime import datetime
        
        tagline = "/version.txt/1.16.2.1/Tue Jul 13 12:49:02 2004//T1.16.2.1"
        e = CvsEntry(tagline)
        self.assertEqual(e.filename, 'version.txt')
        self.assertEqual(e.cvs_version, '1.16.2.1')
        self.assertEqual(e.timestamp, datetime(2004, 7, 13, 12, 49, 2))
        self.assertEqual(e.cvs_tag, 'T1.16.2.1')
        
        tagline = "/Validator.py/1.31.2.5/Result of merge+Tue Jul 13 13:43:06 2004//T1.31.2.5"
        e = CvsEntry(tagline)
        self.assertEqual(e.filename, 'Validator.py')
        self.assertEqual(e.cvs_version, '1.31.2.5')
        self.assertEqual(e.timestamp, datetime(2004, 7, 13, 13, 43, 6))
        self.assertEqual(e.cvs_tag, 'T1.31.2.5')
        

class CvsLogParserTest(TestCase):
    """Ensure the cvs log parser does its job."""

    SIMPLE_TEST_PREFIX = "/cvsroot/docutils/docutils/"
    SIMPLE_TEST = """\
RCS file: /cvsroot/docutils/docutils/THANKS.txt,v
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
*** empty log message ***
----------------------------
revision 1.1
date: 2004/06/03 13:50:58;  author: goodger;  state: Exp;
Added to project (exctracted from HISTORY.txt)
=============================================================================
"""

    DOUBLE_TEST_PREFIX = "/cvsroot/docutils/docutils/"
    DOUBLE_TEST = """\
RCS file: /cvsroot/docutils/docutils/docutils/statemachine.py,v
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
    
    DELETED_TEST_PREFIX = "/cvsroot/docutils/docutils/"
    DELETED_TEST = """\
RCS file: /cvsroot/docutils/docutils/Attic/THANKS.txt,v
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
date: 2004/06/10 02:17:20;  author: goodger;  state: dead;  lines: +3 -2
updated
----------------------------
revision 1.1
date: 2004/06/03 13:50:58;  author: goodger;  state: Exp;
Added to project (exctracted from HISTORY.txt)
=============================================================================
"""

    COLLAPSE_TEST_PREFIX = "/usr/local/CVSROOT/PyObjC/"
    COLLAPSE_TEST = """\
RCS file: /usr/local/CVSROOT/PyObjC/Doc/libObjCStreams.tex,v
head: 1.4
branch:
locks: strict
access list:
keyword substitution: kv
total revisions: 4;     selected revisions: 4
description:
----------------------------
revision 1.4
date: 1997-12-21 23:01:28;  author: lele;  state: Exp;  lines: +2 -8
Fake changelog 1
----------------------------
revision 1.3
date: 1996-10-18 13:48:36;  author: lele;  state: Exp;  lines: +10 -3
Fake changelog 2
----------------------------
revision 1.2
date: 1996-10-14 13:56:50;  author: lele;  state: Exp;  lines: +11 -19
Fake changelog 3
----------------------------
revision 1.1
date: 1996-10-07 18:32:11;  author: lele;  state: Exp;
Fake changelog 4
=============================================================================

RCS file: /usr/local/CVSROOT/PyObjC/Doc/libPyObjC.tex,v
head: 1.4
branch:
locks: strict
access list:
keyword substitution: kv
total revisions: 4;     selected revisions: 4
description:
----------------------------
revision 1.4
date: 1997-12-21 23:01:29;  author: lele;  state: Exp;  lines: +2 -8
Fake changelog 1
----------------------------
revision 1.3
date: 1996-10-18 13:48:45;  author: lele;  state: Exp;  lines: +7 -2
Fake changelog 2
----------------------------
revision 1.2
date: 1996-10-18 12:36:04;  author: lele;  state: Exp;  lines: +7 -3
Fake changelog 3
----------------------------
revision 1.1
date: 1996-10-07 18:32:12;  author: lele;  state: Exp;
Fake changelog 4
=============================================================================
"""

    BRANCHES_TEST_PREFIX = "/cvsroot/archetypes/Archetypes/"
    BRANCHES_TEST = """\
RCS file: /cvsroot/archetypes/Archetypes/tests/test_classgen.py,v
head: 1.18
branch:
locks: strict
access list:
keyword substitution: kv
total revisions: 34;    selected revisions: 3
description:
----------------------------
revision 1.18.14.5
date: 2004/06/17 19:08:43;  author: tiran;  state: Exp;  lines: +1 -0
new test for setFormat/setContentType, content_type as computed attribute
----------------------------
revision 1.18.14.4
date: 2004/05/24 11:20:57;  author: tiran;  state: Exp;  lines: +11 -1
Merge from tiran-seperate_mtr-branch
----------------------------
revision 1.18.14.3
date: 2004/05/21 18:08:46;  author: tiran;  state: Exp;  lines: +1 -3
branches:  1.18.14.3.2;
Fixed deepcopy problem in validations
=============================================================================
"""
    
    def testBasicBehaviour(self):
        """Verify basic cvs log parser behaviour"""

        log = StringIO(self.SIMPLE_TEST)
        csets = changesets_from_cvslog(log,
                                       reposprefix=self.SIMPLE_TEST_PREFIX)

        self.assertEqual(len(csets), 2)
        
        cset = csets[0]
        self.assertEqual(cset.author, "goodger")
        self.assertEqual(cset.date, datetime(2004, 6, 3, 13, 50, 58))
        self.assertEqual(cset.log, "Added to project (exctracted from "
                                   "HISTORY.txt)\n")
        entry = cset.entries[0]
        self.assertEqual(entry.name, 'THANKS.txt')
        self.assertEqual(entry.new_revision, '1.1')
        self.assertEqual(entry.action_kind, entry.ADDED)
        
        cset = csets[1]
        self.assertEqual(cset.author, "goodger")
        self.assertEqual(cset.date, datetime(2004, 6, 10, 2, 17, 20))
        self.assertEqual(cset.log, "") 
        entry = cset.entries[0]
        self.assertEqual(entry.name, 'THANKS.txt')
        self.assertEqual(entry.new_revision, '1.2')
        self.assertEqual(entry.action_kind, entry.UPDATED)
       
    def testGroupingCapability(self):
        """Verify cvs log parser grouping capability"""

        log = StringIO(self.DOUBLE_TEST)
        csets = changesets_from_cvslog(log,
                                       reposprefix=self.DOUBLE_TEST_PREFIX)

        self.assertEqual(len(csets), 5)

        cset = csets[0]
        self.assertEqual(cset.author, "goodger")
        self.assertEqual(cset.date, datetime(2004, 4, 27, 19, 51, 07))

        cset = csets[1]
        self.assertEqual(cset.author, "goodger")
        self.assertEqual(cset.date, datetime(2004, 6, 17, 2, 8, 48))

        cset = csets[2]
        self.assertEqual(cset.author, "goodger")
        self.assertEqual(cset.date, datetime(2004, 6, 17, 2, 51, 31))

        cset = csets[3]
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
        
        cset = csets[4]
        self.assertEqual(cset.author, "felixwiemann")
        self.assertEqual(cset.date, datetime(2004, 6, 20, 16, 3, 17))

    def testDeletedEntry(self):
        """Verify recognition of deleted entries in the cvs log"""

        log = StringIO(self.DELETED_TEST)
        csets = changesets_from_cvslog(log,
                                       reposprefix=self.DELETED_TEST_PREFIX)

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

        log = StringIO(self.COLLAPSE_TEST)
        csets = changesets_from_cvslog(log,
                                       reposprefix=self.COLLAPSE_TEST_PREFIX)

        self.assertEqual(len(csets), 5)

        cset = csets[0]
        self.assertEqual(len(cset.entries), 2)
        self.assertEqual(cset.date, datetime(1996, 10, 7, 18, 32, 11))
        
        cset = csets[1]
        self.assertEqual(len(cset.entries), 1)
        self.assertEqual(cset.date, datetime(1996, 10, 14, 13, 56, 50))
        entry = cset.entries[0]
        self.assertEqual(entry.name, 'Doc/libObjCStreams.tex')       
        
        cset = csets[2]
        self.assertEqual(len(cset.entries), 1)
        self.assertEqual(cset.date, datetime(1996, 10, 18, 12, 36, 4))
        entry = cset.entries[0]
        self.assertEqual(entry.name, 'Doc/libPyObjC.tex')       
        
        cset = csets[3]
        self.assertEqual(len(cset.entries), 2)
        self.assertEqual(cset.date, datetime(1996, 10, 18, 13, 48, 36))
        
    def testBranchesInLog(self):
        """Verify the parser groks with the branches info on revision"""

        log = StringIO(self.BRANCHES_TEST)
        csets = changesets_from_cvslog(log,
                                       reposprefix=self.BRANCHES_TEST_PREFIX)

        self.assertEqual(len(csets), 3)

        cset = csets[0]
        self.assertEqual(cset.log,"Fixed deepcopy problem in validations\n")
        
