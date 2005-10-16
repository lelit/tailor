# -*- mode: python; coding: utf-8 -*-
# :Progetto: vcpx -- Tests for the state file
# :Creato:   mer 17 ago 2005 18:51:46 CEST
# :Autore:   Lele Gaifax <lele@nautilus.homeip.net>
# :Licenza:  GNU General Public License
#

from unittest import TestCase
from cStringIO import StringIO
from vcpx.statefile import StateFile
from vcpx.shwrap import ReopenableNamedTemporaryFile

class Statefile(TestCase):
    "Exercise the state file machinery"

    def testStateFile(self):
        """Verify the state file behaviour"""

        rontf = ReopenableNamedTemporaryFile('sf', 'tailor')

        sf = StateFile(rontf.name, None)
        sf.setPendingChangesets([1,2,3,4,5])
        self.assertEqual(len(sf), 5)

        sf = StateFile(rontf.name, None)
        self.assertEqual(sf.lastAppliedChangeset(), None)
        i = 1
        for cs in sf:
            self.assertEqual(cs, i)
            i += 1

        sf = StateFile(rontf.name, None)
        self.assertEqual(sf.lastAppliedChangeset(), None)
        cs = sf.next()
        sf.applied()
        self.assertEqual(sf.lastAppliedChangeset(), 1)
        cs = sf.next()
        sf.applied()
        self.assertEqual(sf.lastAppliedChangeset(), 2)
        self.assertEqual(len(sf), 3)
        sf.finalize()

        sf = StateFile(rontf.name, None)
        self.assertEqual(sf.lastAppliedChangeset(), 2)
        self.assertEqual(len(sf), 3)
        i = 3
        for cs in sf:
            self.assertEqual(cs, i)
            i += 1

    def testJournal(self):
        """Verify the state file journal"""

        from os.path import exists

        rontf = ReopenableNamedTemporaryFile('sf', 'tailor')

        sf = StateFile(rontf.name, None)
        sf.setPendingChangesets([1,2,3,4,5])
        self.assertEqual(len(sf), 5)

        sf = StateFile(rontf.name, None)
        self.assertEqual(sf.lastAppliedChangeset(), None)
        cs = sf.next()
        sf.applied()
        self.assertEqual(sf.lastAppliedChangeset(), 1)
        cs = sf.next()
        sf.applied()
        self.assertEqual(sf.lastAppliedChangeset(), 2)
        self.assertEqual(len(sf), 3)
        self.assert_(exists(rontf.name + '.journal'))

        sf = StateFile(rontf.name, None)
        self.assertEqual(sf.lastAppliedChangeset(), 2)
        self.assertEqual(len(sf), 3)
        i = 3
        for cs in sf:
            self.assertEqual(cs, i)
            i += 1

    def testReverse(self):
        """Verify the reverse iteration over changesets"""

        rontf = ReopenableNamedTemporaryFile('sf', 'tailor')

        sf = StateFile(rontf.name, None)
        sf.setPendingChangesets([1,2,3,4,5])
        self.assertEqual(len(sf), 5)

        reversed = list(sf.reversed())
        self.assertEqual(reversed, [5,4,3,2,1])
