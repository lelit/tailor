#! /usr/bin/python
# -*- mode: python; coding: utf-8 -*-
# :Progetto: vcpx -- Darcs specific tests
# :Creato:   sab 17 lug 2004 02:33:41 CEST
# :Autore:   Lele Gaifax <lele@nautilus.homeip.net>
# 

from unittest import TestCase, TestSuite
from datetime import datetime
from StringIO import StringIO
from vcpx.darcs import changesets_from_darcschanges

class DarcsChangesParserTest(TestCase):
    """Tests for the parser of darcs changes"""

    SIMPLE_TEST = """\
<changelog>
<patch author='lele@nautilus.homeip.net' date='20040716123737' local_date='Fri Jul 16 14:37:37 CEST 2004' inverted='False' hash='20040716123737-97f81-9db0d923d2ba6f4c3808cb04a4ae4cf99fed185b.gz'>
        <name>Fix the CVS parser to omit already seen changesets</name>
        <comment>For some unknown reasons....</comment>

    <summary>
    <modify_file>vcpx/cvs.py<removed_lines num='4'/><added_lines num='11'/></modify_file>
    <modify_file>vcpx/tests/cvs.py<removed_lines num='14'/><added_lines num='32'/></modify_file>
    </summary>
    
</patch>

<patch author='lele@nautilus.homeip.net' date='20040601140559' local_date='Tue Jun  1 16:05:59 CEST 2004' inverted='False' hash='20040601140559-97f81-b669594864cb35290fbe4848e6645e73057a8caf.gz'>
        <name>Svn log parser with test</name>

    <summary>
    <modify_file>cvsync/svn.py<removed_lines num='1'/><added_lines num='93'/></modify_file>
    <modify_file>cvsync/tests/__init__.py<added_lines num='1'/></modify_file>
    <add_file>cvsync/tests/svn.py</add_file>
    <add_file>cvsync/tests/testrepo.dump</add_file>
    </summary>
    
</patch>

</changelog>
"""

    def testBasicBehaviour(self):
        """Verify basic darcs changes parser behaviour"""

        log = StringIO(self.SIMPLE_TEST)

        csets = changesets_from_darcschanges(log)

        self.assertEqual(len(csets), 2)

        cset = csets[0]
        self.assertEqual(cset.revision,
                         "Svn log parser with test")
        self.assertEqual(cset.date, datetime(2004, 6, 1, 14, 5, 59))
        self.assertEqual(cset.revision, "Svn log parser with test")
        self.assertEqual(len(cset.entries), 4)
        
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
        
        cset = csets[1]
        self.assertEqual(cset.revision,
                         "Fix the CVS parser to omit already seen changesets")
        self.assertEqual(cset.author, "lele@nautilus.homeip.net")
        self.assertEqual(cset.date, datetime(2004, 7, 16, 12, 37, 37))
        self.assertEqual(cset.log, "For some unknown reasons....\n")
        entry = cset.entries[0]
        self.assertEqual(entry.name, 'vcpx/cvs.py')
        self.assertEqual(entry.action_kind, entry.UPDATED)
        
