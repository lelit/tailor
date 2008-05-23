# -*- mode: python; coding: utf-8 -*-
# :Progetto: vcpx -- basic cvsps tests
# :Creato:   ven 09 lug 2004 01:43:52 CEST
# :Autore:   Lele Gaifax <lele@nautilus.homeip.net>
# :Licenza:  GNU General Public License
#

from unittest import TestCase
from datetime import datetime
from vcpx.repository.cvsps import changesets_from_cvsps
from vcpx.tzinfo import UTC


class CvspsParser(TestCase):
    """Ensure the cvsps parser does its job"""

    def getCvspsLog(self, testname):
        from codecs import open
        from os.path import join, split

        logname = join(split(__file__)[0], 'data', testname)+'.log'
        return open(logname, 'r', 'utf-8')

    def testBasicBehaviour(self):
        """Verify basic cvsps log parser behaviour"""

        log = self.getCvspsLog('cvsps-simple_test')
        csets = changesets_from_cvsps(log)

        cset = csets.next()
        self.assertEqual(cset.revision, '1500')
        self.assertEqual(cset.author, "grubert")
        self.assertEqual(cset.date, datetime(2004, 5, 9, 17, 54, 22, 0, UTC))
        self.assertEqual(cset.log, "Tell the reason for using mbox "
                                   "(not wrapping long lines).\n\n")

    def testDoubleEntry(self):
        """Verify the cvsps log parser recognizes double entries"""

        log = self.getCvspsLog('cvsps-double_test')
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

    def testColonInName(self):
        """Verify the parser handle ':' in names"""

        log = self.getCvspsLog('cvsps-colon_in_name')
        csets = changesets_from_cvsps(log)

        cset = csets.next()
        e = cset.entries[0]
        self.assertEqual(e.name, 'somedir/with/fancy:named_file.txt')
