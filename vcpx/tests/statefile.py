# -*- mode: python; coding: utf-8 -*-
# :Progetto: vcpx -- Tests for the state file
# :Creato:   mer 17 ago 2005 18:51:46 CEST
# :Autore:   Lele Gaifax <lele@nautilus.homeip.net>
# :Licenza:  GNU General Public License
#

from unittest import TestCase
from vcpx.statefile import StateFile
from vcpx.shwrap import ReopenableNamedTemporaryFile
from vcpx.repository.mock import MockChangeset as Changeset, MockChangesetEntry as Entry


class Statefile(TestCase):
    "Exercise the state file machinery"

    def testStateFile(self):
        """Verify the state file behaviour"""

        rontf = ReopenableNamedTemporaryFile('sf', 'tailor')

        sf = StateFile(rontf.name, None)
        sf.setPendingChangesets([1,2,3,4,5])

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
        sf.finalize()
        self.assertEqual(sf.pending(), True)

        sf = StateFile(rontf.name, None)
        self.assertEqual(sf.lastAppliedChangeset(), 2)
        i = 3
        for cs in sf:
            self.assertEqual(cs, i)
            sf.applied()
            i += 1
        sf.finalize()
        self.assertEqual(sf.pending(), False)

    def testJournal(self):
        """Verify the state file journal"""

        from os.path import exists

        rontf = ReopenableNamedTemporaryFile('sf', 'tailor')

        sf = StateFile(rontf.name, None)
        sf.setPendingChangesets([1,2,3,4,5])

        sf = StateFile(rontf.name, None)
        self.assertEqual(sf.lastAppliedChangeset(), None)
        cs = sf.next()
        sf.applied()
        self.assertEqual(sf.lastAppliedChangeset(), 1)
        cs = sf.next()
        sf.applied()
        self.assertEqual(sf.lastAppliedChangeset(), 2)
        self.assert_(exists(rontf.name + '.journal'))

        sf = StateFile(rontf.name, None)
        self.assertEqual(sf.lastAppliedChangeset(), 2)
        i = 3
        for cs in sf:
            self.assertEqual(cs, i)
            i += 1

    def testChangesets(self):
        """Verify the behaviour with "real" changesets"""

        from os.path import exists

        changesets = [
            Changeset("Add dir/a{1,2,3}",
                [ Entry(Entry.ADDED, 'dir/'),
                  Entry(Entry.ADDED, 'dir/a1'),
                  Entry(Entry.ADDED, 'dir/a2'),
                  Entry(Entry.ADDED, 'dir/a3'),
                ]),
            Changeset("Spread around",
                [ Entry(Entry.RENAMED, 'a.root', 'dir/a1'),
                  Entry(Entry.RENAMED, 'b.root', 'dir/a2'),
                  Entry(Entry.RENAMED, 'newdir/', 'dir/'),
                  Entry(Entry.UPDATED, 'newdir/a3', contents="ciao"),
                ]),
        ]

        rontf = ReopenableNamedTemporaryFile('sf', 'tailor')

        sf = StateFile(rontf.name, None)
        sf.setPendingChangesets(changesets)

        sf = StateFile(rontf.name, None)
        self.assertEqual(sf.lastAppliedChangeset(), None)
        cs = sf.next()
        sf.applied()
        sf.finalize()

        sf = StateFile(rontf.name, None)
        self.assertEqual(sf.lastAppliedChangeset(), changesets[0])
        cs = sf.next()
        self.assertEqual(cs, changesets[1])
        self.assertEqual(sf.lastAppliedChangeset(), changesets[0])
        sf.finalize()

        sf = StateFile(rontf.name, None)
        self.assertEqual(sf.lastAppliedChangeset(), changesets[0])
        cs = sf.next()
        self.assertEqual(cs, changesets[1])
        sf.applied()
        self.assertEqual(sf.lastAppliedChangeset(), changesets[1])

        self.assertRaises(StopIteration, sf.next)
