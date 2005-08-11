# -*- mode: python; coding: utf-8 -*-
# :Progetto: vcpx -- Darcs specific tests
# :Creato:   sab 17 lug 2004 02:33:41 CEST
# :Autore:   Lele Gaifax <lele@nautilus.homeip.net>
# :Licenza:  GNU General Public License
#

from unittest import TestCase, TestSuite
from datetime import datetime
from StringIO import StringIO
from vcpx.darcs import changesets_from_darcschanges
from shwrap import ExternalCommand, PIPE

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
        self.assertEqual(cset.log,
                         "Fix the CVS parser to omit already seen changesets\n"
                         "For some unknown reasons....")
        entry = cset.entries[0]
        self.assertEqual(entry.name, 'vcpx/cvs.py')
        self.assertEqual(entry.action_kind, entry.UPDATED)

    def testOnTailorOwnRepo(self):
        """Verify fetching unidiff of a darcs patch"""

        from os import getcwd

        patchname = 'more detailed diags on SAXException'
        changes = ExternalCommand(command=["darcs", "changes", "--xml", "--summary",
                                           "--patches", patchname])
        csets = changesets_from_darcschanges(changes.execute(stdout=PIPE),
                                             unidiff=True,
                                             repodir=getcwd())
        unidiff = csets[0].unidiff
        head = unidiff.split('\n')[0]
        self.assertEqual(head, 'Thu Jun  9 22:17:11 CEST 2005  zooko@zooko.com')

    ALL_ACTIONS_TEST = """\
<changelog>
<patch author='' date='20050811140203' local_date='Thu Aug 11 16:02:03 CEST 2005' inverted='False' hash='20050811140203-da39a-0a36c886b2479b20ab9188781fe2e51f9a50a175.gz'>
        <name>first</name>
    <summary>
    <add_file>
    a.txt
    </add_file>
    <add_directory>
    dir
    </add_directory>
    </summary>
</patch>
<patch author='' date='20050811140254' local_date='Thu Aug 11 16:02:54 CEST 2005' inverted='False' hash='20050811140254-da39a-b2ad279f1d7edae8e07b7b1ea8f3e63dbb242bf0.gz'>
        <name>removed</name>
    <summary>
    <remove_directory>
    dir
    </remove_directory>
    </summary>
</patch>
<patch author='' date='20050811140314' local_date='Thu Aug 11 16:03:14 CEST 2005' inverted='False' hash='20050811140314-da39a-de701bff466827b91e51658e411c768f43abc1b0.gz'>
        <name>moved</name>
    <summary>
    <move from="bdir" to="dir"/>
    <add_directory>
    bdir
    </add_directory>
    </summary>
</patch>
<patch author='lele@metapensiero.it' date='20050811143245' local_date='Thu Aug 11 16:32:45 CEST 2005' inverted='False' hash='20050811143245-7a6fb-663bb3085e9b7996f554e4bd9d2f0b13208d65e0.gz'>
        <name>modified</name>
    <summary>
    <modify_file>
    a.txt<added_lines num='3'/>
    </modify_file>
    </summary>
</patch>
</changelog>
"""

    def testAllActions(self):
        """Verify darcs changes parser understand all actions"""

        log = StringIO(self.ALL_ACTIONS_TEST)

        csets = changesets_from_darcschanges(log)

        self.assertEqual(len(csets), 4)

        cset = csets[0]
        self.assertEqual(cset.revision, 'first')
        self.assertEqual(len(cset.entries), 2)

        entry = cset.entries[0]
        self.assertEqual(entry.name, 'a.txt')
        self.assertEqual(entry.action_kind, entry.ADDED)
        entry = cset.entries[1]
        self.assertEqual(entry.name, 'dir')
        self.assertEqual(entry.action_kind, entry.ADDED)

        cset = csets[1]
        self.assertEqual(cset.revision, 'removed')
        self.assertEqual(len(cset.entries), 1)

        entry = cset.entries[0]
        self.assertEqual(entry.name, 'dir')
        self.assertEqual(entry.action_kind, entry.DELETED)

        cset = csets[2]
        self.assertEqual(cset.revision, 'moved')
        self.assertEqual(len(cset.entries), 2)

        entry = cset.entries[0]
        self.assertEqual(entry.name, 'bdir')
        self.assertEqual(entry.action_kind, entry.ADDED)

        entry = cset.entries[1]
        self.assertEqual(entry.name, 'dir')
        self.assertEqual(entry.action_kind, entry.RENAMED)

        cset = csets[3]
        self.assertEqual(cset.revision, 'modified')
        self.assertEqual(len(cset.entries), 1)

        entry = cset.entries[0]
        self.assertEqual(entry.name, 'a.txt')
        self.assertEqual(entry.action_kind, entry.UPDATED)
