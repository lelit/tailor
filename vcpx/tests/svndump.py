# -*- mode: python; coding: utf-8 -*-
# :Progetto: vcpx -- Tests for svndump source backend
# :Creato:   gio 01 set 2005 10:47:17 CEST
# :Autore:   Lele Gaifax <lele@nautilus.homeip.net>
# :Licenza:  GNU General Public License
#

from unittest import TestCase, TestSuite
from datetime import datetime
from StringIO import StringIO
from vcpx.svndump import changesets_from_svndump

class SvndumpParserTest(TestCase):
    """Ensure the svndump parser does its job."""

    def setUp(self):
        from os.path import join, split

        datadir = join(split(__file__)[0], 'data')
        self.log = open(join(datadir, 'simple.svndump'), 'rU')

    def testBasicBehaviour(self):
        "Verify basic svndump parser behaviour"

        csets = changesets_from_svndump(self.log)

        self.assertEqual(len(csets), 5)

        cset = csets[0]
        self.assertEqual(cset.author, "lele")
        self.assertEqual(cset.date, datetime(2005, 9, 1, 8, 38, 41, 788715))
        self.assertEqual(cset.log, "Initial import")

        entry = cset.entries[0]
        self.assertEqual(entry.name, 'bash.bashrc')
        self.assertEqual(entry.action_kind, entry.ADDED)
        self.assertEqual(entry.text_length, 980)

        cset = csets[1]
        self.assertEqual(cset.log, "Rename the file")

        entry = cset.entries[0]
        self.assertEqual(entry.name, 'bashrc')
        self.assertEqual(entry.old_name, 'bash.bashrc')
        self.assertEqual(entry.action_kind, entry.RENAMED)
        self.assertEqual(entry.text_length, None)

        cset = csets[2]
        self.assertEqual(cset.log, "Add subdir")

        entry = cset.entries[0]
        self.assertEqual(entry.name, 'subdir')
        self.assertEqual(entry.action_kind, entry.ADDED)
        self.assertEqual(entry.text_length, None)

    def testFilterOnModule(self):
        "Verify how svndump parser filters entries"

        csets = changesets_from_svndump(self.log, module="subdir/")

        self.assertEqual(len(csets), 1)

        cset = csets[0]
        entry = cset.entries[0]
        self.assertEqual(entry.name, 'other.version')
        self.assertEqual(entry.action_kind, entry.ADDED)
