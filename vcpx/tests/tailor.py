# -*- mode: python; coding: utf-8 -*-
# :Progetto: vcpx -- Operational tests
# :Creato:   lun 08 ago 2005 22:17:10 CEST
# :Autore:   Lele Gaifax <lele@nautilus.homeip.net>
# :Licenza:  GNU General Public License
#

"""
[DEFAULT]
dont-refill-changelogs = True
target-module = None
source-repository = ~/WiP/cvsync
encoding = None
target-repository = None
use-svn-propset = False
source-module = None
update = True
subdir = .
debug = True
remove-first-log-line = False
patch-name-format = None
verbose = True
state-file = tailor.state
start-revision = Almost arbitrarily tagging this as version 0.8

[darcs2bzr]
target = bzr:tailor
root-directory = /tmp/tailor-tests/darcs2bzr
source = darcs:tailor

[darcs2cdv]
target = cdv:tailor
root-directory = /tmp/tailor-tests/darcs2cdv
source = darcs:tailor

[darcs2hg]
target = hg:tailor
root-directory = /tmp/tailor-tests/darcs2hg
source = darcs:tailor

[darcs2svn]
target = svn:tailor
root-directory = /tmp/tailor-tests/darcs2svn
source = darcs:svntailor
start-revision = INITIAL

[svn2darcs]
target = darcs:svntailor
root-directory = /tmp/tailor-tests/svn2darcs
source = svn:tailor
start-revision = 1

[darcs:tailor]
repository = ~/WiP/cvsync

[bzr:tailor]
bzr-command = /opt/src/bzr.dev/bzr

[cdv:tailor]

[hg:tailor]

[svn:tailor]
repository = file:///tmp/tailor-tests/svnrepo
module = tailor
subdir = svnside

[darcs:svntailor]
subdir = darcside

[cvs2darcs]
target = darcs:pxlib
root-directory = /tmp/tailor-tests/cvs2darcs
source = cvs:pxlib
start-revision = INITIAL
subdir = pxlib

[darcs:pxlib]

[cvs:pxlib]
repository = :pserver:anonymous@cvs.sf.net:/cvsroot/pxlib
module = pxlib
"""

from unittest import TestCase, TestSuite
from cStringIO import StringIO
from vcpx.config import Config
from vcpx.tailor import Tailorizer

class TailorTest(TestCase):

    def setUp(self):
        from os import mkdir
        from os.path import exists
        from atexit import register
        from shutil import rmtree

        self.config = Config(StringIO(__doc__), {})
        if not exists('/tmp/tailor-tests'):
            mkdir('/tmp/tailor-tests')
            register(rmtree, '/tmp/tailor-tests')

    def testConfiguration(self):
        "Test basic configuration"

        from os.path import expanduser

        p = Tailorizer('darcs2svn', self.config)
        self.assertEqual(p.source.subdir, 'darcside')
        self.assertEqual(p.rootdir, '/tmp/tailor-tests/darcs2svn')
        self.assertEqual(p.source.repository, expanduser('~/WiP/cvsync'))
        self.assertEqual(p.target.repository,
                         'file:///tmp/tailor-tests/svnrepo')
        self.assertEqual(p.state_file.filename,
                         '/tmp/tailor-tests/darcs2svn/tailor.state')

        tailorizer = Tailorizer('cvs2darcs', self.config)
        self.assertEqual(tailorizer.subdir, 'pxlib')
        self.assertEqual(tailorizer.source.subdir, 'pxlib')

    def testDarcsToBazaarng(self):
        "Test darcs to BazaarNG"

        tailorizer = Tailorizer('darcs2bzr', self.config)
        tailorizer()
        self.assert_(tailorizer.exists())
        tailorizer()

    def testDarcsToMercurial(self):
        "Test darcs to mercurial"

        tailorizer = Tailorizer('darcs2hg', self.config)
        tailorizer()
        self.assert_(tailorizer.exists())
        tailorizer()

    def testDarcsToCodeville(self):
        "Test darcs to codeville"

        tailorizer = Tailorizer('darcs2cdv', self.config)
        tailorizer()
        self.assert_(tailorizer.exists())
        tailorizer()

    def testDarcsToSubversion(self):
        "Test darcs to subversion"

        tailorizer = Tailorizer('darcs2svn', self.config)
        tailorizer()
        self.assert_(tailorizer.exists())
        tailorizer()

    ## The other way

    def testSubversionToDarcs(self):
        "Test subversion to darcs"

        tailorizer = Tailorizer('svn2darcs', self.config)
        tailorizer()
        self.assert_(tailorizer.exists())
        tailorizer()

    def testCvsToDarcs(self):
        "Test CVS to darcs"

        tailorizer = Tailorizer('cvs2darcs', self.config)
        tailorizer()
        self.assert_(tailorizer.exists())
        tailorizer()
