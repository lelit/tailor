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

    SIMPLE_TEST = """\
cvs rlog: Logging docutils

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

    def testBasicBehaviour(self):
        """Verify basic cvs log parser behaviour"""

        log = StringIO(self.SIMPLE_TEST)
        csets = changesets_from_cvslog(log, 'docutils')

        self.assertEqual(len(csets), 2)
        
        cset = csets[0]
        self.assertEqual(cset.author, "goodger")
        self.assertEqual(cset.date, datetime(2004, 6, 3, 13, 50, 58))
        self.assertEqual(cset.log, "Added to project (exctracted from "
                                   "HISTORY.txt)")
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
       
    DOUBLE_TEST = """\
cvs rlog: Logging docutils/docutils

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

    def testGroupingCapability(self):
        """Verify cvs log parser grouping capability"""

        log = StringIO(self.DOUBLE_TEST)
        csets = changesets_from_cvslog(log, 'docutils')

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
        self.assertEqual(cset.log,"support for CSV directive implementation")
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

    DELETED_TEST = """\
cvs rlog: Logging docutils

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

    def testDeletedEntry(self):
        """Verify recognition of deleted entries in the cvs log"""

        log = StringIO(self.DELETED_TEST)
        csets = changesets_from_cvslog(log, 'docutils')

        self.assertEqual(len(csets), 2)

        cset = csets[0]
        entry = cset.entries[0]
        self.assertEqual(entry.action_kind, entry.ADDED)
        
        cset = csets[1]
        entry = cset.entries[0]
        self.assertEqual(entry.name, 'THANKS.txt')
        self.assertEqual(entry.action_kind, entry.DELETED)

    COLLAPSE_TEST = """\
cvs rlog: Logging PyObjC/Doc
    
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

    def testCollapsedChangeset(self):
        """Verify the mechanism used to collapse related changesets"""

        log = StringIO(self.COLLAPSE_TEST)
        csets = changesets_from_cvslog(log, 'PyObjC')

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
        
    BRANCHES_TEST = """\
cvs rlog: Logging Archetypes/tests

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
    
    def testBranchesInLog(self):
        """Verify the parser groks with the branches info on revision"""

        log = StringIO(self.BRANCHES_TEST)
        csets = changesets_from_cvslog(log, 'Archetypes')

        self.assertEqual(len(csets), 3)

        cset = csets[0]
        self.assertEqual(cset.log,"Fixed deepcopy problem in validations")
        
    REPOSPATH_TEST = """\
cvs rlog: Logging Zope/spurious/dummy/dir
cvs rlog: Logging Zope/lib/python/DateTime
cvs rlog: warning: no revision `Zope-2_7-branch' in `/cvs-repository/Packages/DateTime/Attic/DateTime.html,v'

RCS file: /cvs-repository/Packages/DateTime/Attic/DateTime.py,v
head: 1.100
branch:
locks: strict
access list:
keyword substitution: kv
total revisions: 170;   selected revisions: 1
description:
----------------------------
revision 1.85.12.11
date: 2004/08/02 09:49:18;  author: andreasjung;  state: Exp;  lines: +22 -2
backported copy constructor from trunk
=============================================================================
"""

    def testReposPath(self):
        """Verify the parser is right in determine working copy file paths"""

        log = StringIO(self.REPOSPATH_TEST)
        csets = changesets_from_cvslog(log, 'Zope')

        self.assertEqual(len(csets), 1)

        cset = csets[0]
        self.assertEqual(cset.log,"backported copy constructor from trunk")
        self.assertEqual(len(cset.entries), 1)
        entry = cset.entries[0]
        self.assertEqual(entry.name, 'lib/python/DateTime/DateTime.py')

    LONGLOG_TEST = """\
cvs rlog: Logging ATContentTypes

RCS file: /cvsroot/collective/ATContentTypes/Attic/ConstrainTypesMixin.py,v
head: 1.1
branch:
locks: strict
access list:
keyword substitution: kv
total revisions: 5;	selected revisions: 1
description:
----------------------------
revision 1.1
date: 2004/08/11 01:09:46;  author: rochael;  state: dead;
branches:  1.1.2;
file ConstrainTypesMixin.py was initially added on branch jensens-restrain_mixin-branch.
=============================================================================

RCS file: /cvsroot/collective/ATContentTypes/customconfig.py.example,v
head: 1.7
branch:
locks: strict
access list:
keyword substitution: kv
total revisions: 9;	selected revisions: 1
description:
----------------------------
revision 1.7
date: 2004/08/13 13:59:55;  author: rochael;  state: Exp;  lines: +1 -5
removed duplicated ENABLE_TEMPLATE_MIXIN
=============================================================================
cvs rlog: Logging ATContentTypes/Extensions

RCS file: /cvsroot/collective/ATContentTypes/Extensions/batchCreate.py,v
head: 1.2
branch:
locks: strict
access list:
keyword substitution: kv
total revisions: 3;	selected revisions: 1
description:
----------------------------
revision 1.2
date: 2004/08/09 07:44:05;  author: tiran;  state: Exp;  lines: +4 -1
branches:  1.2.2;
Recoded migration walkers to use a generator instead returning a list to make them much more memory efficient.

Rewritten folder migration to use the depth inside the folder structur instead of recursing into the full side.

Added a findStaledObjects external method to ATCT to find staled objects. It is very useful to clean up a site before running the migration.
=============================================================================

RCS file: /cvsroot/collective/ATContentTypes/Extensions/findStaledObjects.py,v
head: 1.1
branch:
locks: strict
access list:
keyword substitution: kv
total revisions: 2;	selected revisions: 1
description:
----------------------------
revision 1.1
date: 2004/08/09 07:44:05;  author: tiran;  state: Exp;
branches:  1.1.2;
Recoded migration walkers to use a generator instead returning a list to make them much more memory efficient.

Rewritten folder migration to use the depth inside the folder structur instead of recursing into the full side.

Added a findStaledObjects external method to ATCT to find staled objects. It is very useful to clean up a site before running the migration.
=============================================================================
cvs rlog: Logging ATContentTypes/debian
cvs rlog: Logging ATContentTypes/docs

RCS file: /cvsroot/collective/ATContentTypes/docs/ExtendingType.txt,v
head: 1.1
branch:
locks: strict
access list:
keyword substitution: kv
total revisions: 2;	selected revisions: 1
description:
----------------------------
revision 1.1
date: 2004/08/06 20:13:30;  author: tiran;  state: Exp;
branches:  1.1.2;
Added ExtendingType
=============================================================================

RCS file: /cvsroot/collective/ATContentTypes/docs/HISTORY.txt,v
head: 1.42
branch:
locks: strict
access list:
keyword substitution: kv
total revisions: 44;	selected revisions: 1
description:
----------------------------
revision 1.42
date: 2004/08/09 07:44:07;  author: tiran;  state: Exp;  lines: +12 -0
Recoded migration walkers to use a generator instead returning a list to make them much more memory efficient.

Rewritten folder migration to use the depth inside the folder structur instead of recursing into the full side.

Added a findStaledObjects external method to ATCT to find staled objects. It is very useful to clean up a site before running the migration.
=============================================================================
cvs rlog: Logging ATContentTypes/i18n
cvs rlog: Logging ATContentTypes/interfaces

RCS file: /cvsroot/collective/ATContentTypes/interfaces/Attic/IConstrainTypes.py,v
head: 1.1
branch:
locks: strict
access list:
keyword substitution: kv
total revisions: 2;	selected revisions: 1
description:
----------------------------
revision 1.1
date: 2004/08/11 01:09:47;  author: rochael;  state: dead;
branches:  1.1.2;
file IConstrainTypes.py was initially added on branch jensens-restrain_mixin-branch.
=============================================================================
cvs rlog: Logging ATContentTypes/migration

RCS file: /cvsroot/collective/ATContentTypes/migration/ATCTMigrator.py,v
head: 1.12
branch:
locks: strict
access list:
keyword substitution: kv
total revisions: 14;	selected revisions: 1
description:
----------------------------
revision 1.12
date: 2004/08/09 07:44:09;  author: tiran;  state: Exp;  lines: +42 -32
Recoded migration walkers to use a generator instead returning a list to make them much more memory efficient.

Rewritten folder migration to use the depth inside the folder structur instead of recursing into the full side.

Added a findStaledObjects external method to ATCT to find staled objects. It is very useful to clean up a site before running the migration.
=============================================================================

RCS file: /cvsroot/collective/ATContentTypes/migration/CPTMigrator.py,v
head: 1.8
branch:
locks: strict
access list:
keyword substitution: kv
total revisions: 9;	selected revisions: 1
description:
----------------------------
revision 1.8
date: 2004/08/09 07:44:09;  author: tiran;  state: Exp;  lines: +38 -31
Recoded migration walkers to use a generator instead returning a list to make them much more memory efficient.

Rewritten folder migration to use the depth inside the folder structur instead of recursing into the full side.

Added a findStaledObjects external method to ATCT to find staled objects. It is very useful to clean up a site before running the migration.
=============================================================================

RCS file: /cvsroot/collective/ATContentTypes/migration/Walker.py,v
head: 1.15
branch:
locks: strict
access list:
keyword substitution: kv
total revisions: 17;	selected revisions: 1
description:
----------------------------
revision 1.15
date: 2004/08/09 07:44:09;  author: tiran;  state: Exp;  lines: +76 -30
Recoded migration walkers to use a generator instead returning a list to make them much more memory efficient.

Rewritten folder migration to use the depth inside the folder structur instead of recursing into the full side.

Added a findStaledObjects external method to ATCT to find staled objects. It is very useful to clean up a site before running the migration.
=============================================================================
cvs rlog: Logging ATContentTypes/skins
cvs rlog: Logging ATContentTypes/skins/ATContentTypes

RCS file: /cvsroot/collective/ATContentTypes/skins/ATContentTypes/atct_history.pt,v
head: 1.5
branch:
locks: strict
access list:
keyword substitution: kv
total revisions: 7;	selected revisions: 1
description:
----------------------------
revision 1.5
date: 2004/08/13 13:21:53;  author: tiran;  state: Exp;  lines: +1 -2
Somehow I mixed up two sentences
=============================================================================
cvs rlog: Logging ATContentTypes/tests

RCS file: /cvsroot/collective/ATContentTypes/tests/Attic/testContrainTypes.py,v
head: 1.1
branch:
locks: strict
access list:
keyword substitution: kv
total revisions: 4;	selected revisions: 1
description:
----------------------------
revision 1.1
date: 2004/08/11 01:13:43;  author: rochael;  state: dead;
branches:  1.1.2;
file testContrainTypes.py was initially added on branch jensens-restrain_mixin-branch.
=============================================================================
cvs rlog: Logging ATContentTypes/types

RCS file: /cvsroot/collective/ATContentTypes/types/ATContentType.py,v
head: 1.36
branch:
locks: strict
access list:
keyword substitution: kv
total revisions: 38;	selected revisions: 1
description:
----------------------------
revision 1.36
date: 2004/08/13 13:15:46;  author: tiran;  state: Exp;  lines: +2 -2
Fixed typo
=============================================================================

RCS file: /cvsroot/collective/ATContentTypes/types/schemata.py,v
head: 1.45
branch:
locks: strict
access list:
keyword substitution: kv
total revisions: 49;	selected revisions: 1
description:
----------------------------
revision 1.45
date: 2004/08/13 13:21:24;  author: tiran;  state: Exp;  lines: +24 -24
Something went wrong ...
=============================================================================
cvs rlog: Logging ATContentTypes/types/criteria
"""
    
    def testLongLog(self):
        """Stress the parser with a very long changelog"""

        log = StringIO(self.LONGLOG_TEST)
        csets = changesets_from_cvslog(log, 'ATContentTypes')

        self.assertEqual(len(csets), 9)
        
        cset = csets[0]
        self.assertEqual(cset.author, "tiran")
        self.assertEqual(cset.date, datetime(2004, 8, 6, 20, 13, 30))
        self.assertEqual(cset.log, "Added ExtendingType")
        entry = cset.entries[0]
        self.assertEqual(entry.name, 'docs/ExtendingType.txt')
        self.assertEqual(entry.new_revision, '1.1')
        self.assertEqual(entry.action_kind, entry.ADDED)
        
        cset = csets[1]
        self.assertEqual(cset.author, "tiran")
        self.assertEqual(cset.date, datetime(2004, 8, 9, 7, 44, 5))
        self.assertEqual(cset.log, """\
Recoded migration walkers to use a generator instead returning a list
to make them much more memory efficient. Rewritten folder migration to
use the depth inside the folder structur instead of recursing into the
full side. Added a findStaledObjects external method to ATCT to find
staled objects. It is very useful to clean up a site before running
the migration.""") 
        entry = cset.entries[0]
        self.assertEqual(entry.name, 'Extensions/batchCreate.py')
        self.assertEqual(entry.new_revision, '1.2')
        self.assertEqual(entry.action_kind, entry.UPDATED)

        cset = csets[2]
        self.assertEqual(cset.author, "rochael")
        self.assertEqual(cset.date, datetime(2004, 8, 11, 1, 9, 46))
        self.assertEqual(cset.log, """\
file ConstrainTypesMixin.py was initially added on branch jensens-
restrain_mixin-branch.""")
        entry = cset.entries[0]
        self.assertEqual(entry.name, 'ConstrainTypesMixin.py')
        self.assertEqual(entry.new_revision, '1.1')
        self.assertEqual(entry.action_kind, entry.DELETED)

        cset = csets[3]
        self.assertEqual(cset.author, "rochael")
        self.assertEqual(cset.date, datetime(2004, 8, 11, 1, 9, 47))
        self.assertEqual(cset.log, """\
file IConstrainTypes.py was initially added on branch jensens-
restrain_mixin-branch.""")
        entry = cset.entries[0]
        self.assertEqual(entry.name, 'interfaces/IConstrainTypes.py')
        self.assertEqual(entry.new_revision, '1.1')
        self.assertEqual(entry.action_kind, entry.DELETED)

        cset = csets[4]
        self.assertEqual(cset.author, "rochael")
        self.assertEqual(cset.date, datetime(2004, 8, 11, 1, 13, 43))
        self.assertEqual(cset.log, """\
file testContrainTypes.py was initially added on branch jensens-
restrain_mixin-branch.""")
        entry = cset.entries[0]
        self.assertEqual(entry.name, 'tests/testContrainTypes.py')
        self.assertEqual(entry.new_revision, '1.1')
        self.assertEqual(entry.action_kind, entry.DELETED)

        cset = csets[5]
        self.assertEqual(cset.author, "tiran")
        self.assertEqual(cset.date, datetime(2004, 8, 13, 13, 15, 46))
        self.assertEqual(cset.log, "Fixed typo")

        cset = csets[6]
        self.assertEqual(cset.author, "tiran")
        self.assertEqual(cset.date, datetime(2004, 8, 13, 13, 21, 24))
        self.assertEqual(cset.log, "Something went wrong ...")

        cset = csets[7]
        self.assertEqual(cset.author, "tiran")
        self.assertEqual(cset.date, datetime(2004, 8, 13, 13, 21, 53))
        self.assertEqual(cset.log, "Somehow I mixed up two sentences")

        cset = csets[8]
        self.assertEqual(cset.author, "rochael")
        self.assertEqual(cset.date, datetime(2004, 8, 13, 13, 59, 55))
        self.assertEqual(cset.log, "removed duplicated ENABLE_TEMPLATE_MIXIN")
        entry = cset.entries[0]
        self.assertEqual(entry.name, 'customconfig.py.example')
        self.assertEqual(entry.new_revision, '1.7')
        self.assertEqual(entry.action_kind, entry.UPDATED)
        
    SILLY_TEST = """\
RCS file: /cvsroot/docutils/docutils/THANKS.txt,v
head: 1.2
"""
    
    def testDirectoryMissing(self):
        """Verify how parser reacts on bad input"""

        log = StringIO(self.SILLY_TEST)
        self.assertRaises(AssertionError,
                          changesets_from_cvslog, log, 'docutils')

