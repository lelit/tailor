# -*- mode: python; coding: utf-8 -*-
# :Progetto: vcpx -- Tests for the state file
# :Creato:   mer 17 ago 2005 18:51:46 CEST
# :Autore:   Lele Gaifax <lele@nautilus.homeip.net>
# :Licenza:  GNU General Public License
#

from unittest import TestCase, TestSuite
from cStringIO import StringIO
from vcpx.project import StateFile

class StateFileTest(TestCase):

    def testStateFile(self):
        """Verify the state file behaviour"""

        from tempfile import mktemp

        sfname = mktemp('sf', 'tailor')
        sf = StateFile(sfname, None)
        sf.setPendingChangesets([1,2,3,4,5])
        self.assertEqual(len(sf), 5)

        sf = StateFile(sfname, None)
        self.assertEqual(sf.lastAppliedChangeset(), None)
        i = 1
        for cs in sf:
            self.assertEqual(cs, i)
            i += 1

        sf = StateFile(sfname, None)
        self.assertEqual(sf.lastAppliedChangeset(), None)
        cs = sf.next()
        sf.applied()
        self.assertEqual(sf.lastAppliedChangeset(), 1)
        cs = sf.next()
        sf.applied()
        self.assertEqual(sf.lastAppliedChangeset(), 2)
        self.assertEqual(len(sf), 3)
        sf.finalize()

        sf = StateFile(sfname, None)
        self.assertEqual(sf.lastAppliedChangeset(), 2)
        self.assertEqual(len(sf), 3)
        i = 3
        for cs in sf:
            self.assertEqual(cs, i)
            i += 1

    def testJournal(self):
        """Verify the state file journal"""

        from tempfile import mktemp
        from os.path import exists

        sfname = mktemp('sf', 'tailor')
        sf = StateFile(sfname, None)
        sf.setPendingChangesets([1,2,3,4,5])
        self.assertEqual(len(sf), 5)

        sf = StateFile(sfname, None)
        self.assertEqual(sf.lastAppliedChangeset(), None)
        cs = sf.next()
        sf.applied()
        self.assertEqual(sf.lastAppliedChangeset(), 1)
        cs = sf.next()
        sf.applied()
        self.assertEqual(sf.lastAppliedChangeset(), 2)
        self.assertEqual(len(sf), 3)
        self.assert_(exists(sfname + '.journal'))

        sf = StateFile(sfname, None)
        self.assertEqual(sf.lastAppliedChangeset(), 2)
        self.assertEqual(len(sf), 3)
        i = 3
        for cs in sf:
            self.assertEqual(cs, i)
            i += 1
