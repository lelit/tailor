# -*- mode: python; coding: utf-8 -*-
# :Progetto: vcpx -- Operational tests
# :Creato:   lun 08 ago 2005 22:17:10 CEST
# :Autore:   Lele Gaifax <lele@nautilus.homeip.net>
# :Licenza:  GNU General Public License
#

"""
[DEFAULT]
target-module = None
source-repository = %(tailor_repo)s
encoding = None
target-repository = None
use-svn-propset = False
source-module = None
update = True
subdir = .
debug = False
remove-first-log-line = False
patch-name-format = None
verbose = True
state-file = tailor.state
start-revision = Version 0.9.7

[darcs2bzr]
target = bzr:tailor
root-directory = /tmp/tailor-tests/darcs2bzr
source = darcs:tailor

[darcs2bzrng]
target = bzrng:tailor
root-directory = /tmp/tailor-tests/darcs2bzrng
source = darcs:tailor
patch-name-format = %(revision)s

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

[darcs2monotone]
target = monotone:tailor
root-directory = /tmp/tailor-tests/darcs2monotone
source = darcs:tailor

[svn2darcs]
target = darcs:svntailor
root-directory = /tmp/tailor-tests/svn2darcs
source = svn:tailor
start-revision = 1

[darcs:tailor]

[bzr:tailor]
bzr-command = /opt/src/bzr.dev/bzr

[bzrng:tailor]
python-path = /opt/src/bzr.dev

[cdv:tailor]

[hg:tailor]

[monotone:tailor]
keyid = tailor
passphrase = fin che la barca va
repository = /tmp/tailor-tests/tailor-mtn.db
module = tailor.test

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
start-revision = R-0-5-1
subdir = pxlib

[darcs:pxlib]

[cvs:pxlib]
repository = :pserver:anonymous@cvs.sf.net:/cvsroot/pxlib
module = pxlib

[cvs2hg]
root-directory = /tmp/tailor-tests/cvs2hg
source = cvs:cmsmini
target = hg:cmsmini
start-revision = INITIAL
subdir = cmsmini

[cvs:cmsmini]
repository = :ext:anoncvs@savannah.nongnu.org:/cvsroot/cmsmini
module = cmsmini

[hg:cmsmini]

[cvs2bzr]
root-directory = /tmp/tailor-tests/cvs2bzr
source = cvs:atse
target = bzr:atse
start-revision = spamies-improvement-branch INITIAL
subdir = atse

[cvs:atse]
repository = :pserver:anonymous@cvs.sourceforge.net:/cvsroot/collective
module = ATSchemaEditorNG

[bzr:atse]
bzr-command = /opt/src/bzr.dev/bzr

[svndump2darcs]
source = svndump:simple
target = darcs:simple
root-directory = /tmp/tailor-tests/svndump2darcs
subdir = simple
start-revision = INITIAL

[svndump:simple]
repository = /tmp/pyobjc.svndump

[darcs:simple]
"""

from unittest import TestCase, TestSuite
from cStringIO import StringIO
from vcpx.config import Config
from vcpx.tailor import Tailorizer
from vcpx.shwrap import ExternalCommand, PIPE

class TailorTest(TestCase):

    def setUp(self):
        from os import mkdir, getcwd
        from os.path import exists, split, join
        from atexit import register
        from shutil import rmtree

        tailor_repo = getcwd()
        while tailor_repo and not exists(join(tailor_repo, '_darcs')):
            tailor_repo = split(tailor_repo)[0]
        assert exists(join(tailor_repo, '_darcs')), "Tailor Darcs repository not found!"
        self.tailor_repo = tailor_repo
        self.config = Config(StringIO(__doc__), {'tailor_repo': tailor_repo})
        if not exists('/tmp/tailor-tests'):
            mkdir('/tmp/tailor-tests')
            register(rmtree, '/tmp/tailor-tests')

    def diffWhenPossible(self, tailorizer):
        "Diff the resulting sides"

        dwd = tailorizer.workingDir()
        if dwd.source.basedir <> dwd.target.basedir:
            cmd = ["diff", "-r", "-u",
                   "-x", tailorizer.source.METADIR,
                   "-x", tailorizer.target.METADIR]
            d = ExternalCommand(command=cmd)
            out = d.execute(dwd.source.basedir, dwd.target.basedir,
                            stdout=PIPE)[0]
            return out.read()
        else:
            return ""

    def testConfiguration(self):
        "Test basic configuration"

        from os.path import expanduser

        p = Tailorizer('darcs2svn', self.config)
        self.assertEqual(p.source.subdir, 'darcside')
        self.assertEqual(p.rootdir, '/tmp/tailor-tests/darcs2svn')
        self.assertEqual(p.source.repository, self.tailor_repo)
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
        self.assert_(not tailorizer.exists())
        tailorizer()
        self.assertEqual(self.diffWhenPossible(tailorizer), "")

    def testDarcsToBazaarngNative(self):
        "Test darcs to BazaarNG (native)"

        tailorizer = Tailorizer('darcs2bzrng', self.config)
        self.assert_(not tailorizer.exists())
        tailorizer()
        self.assertEqual(self.diffWhenPossible(tailorizer), "")

    def testDarcsToMercurial(self):
        "Test darcs to mercurial"

        tailorizer = Tailorizer('darcs2hg', self.config)
        self.assert_(not tailorizer.exists())
        tailorizer()
        self.assertEqual(self.diffWhenPossible(tailorizer), "")

    def testDarcsToCodeville(self):
        "Test darcs to codeville"

        tailorizer = Tailorizer('darcs2cdv', self.config)
        self.assert_(not tailorizer.exists())
        tailorizer()
        self.assertEqual(self.diffWhenPossible(tailorizer), "")

    def testDarcsToSubversion(self):
        "Test darcs to subversion"

        tailorizer = Tailorizer('darcs2svn', self.config)
        self.assert_(not tailorizer.exists())
        tailorizer()
        self.assertEqual(self.diffWhenPossible(tailorizer), "")

    def testDarcsToMonotone(self):
        "Test darcs to monotone"

        tailorizer = Tailorizer('darcs2monotone', self.config)
        self.assert_(not tailorizer.exists())
        tailorizer()
        self.assertEqual(self.diffWhenPossible(tailorizer), "")

    ## The other way

    def testSubversionToDarcs(self):
        "Test subversion to darcs"

        tailorizer = Tailorizer('svn2darcs', self.config)
        self.assert_(not tailorizer.exists())
        tailorizer()
        self.assertEqual(self.diffWhenPossible(tailorizer), "")

    def testCvsToDarcs(self):
        "Test CVS to darcs"

        tailorizer = Tailorizer('cvs2darcs', self.config)
        self.assert_(not tailorizer.exists())
        tailorizer()
        self.assertEqual(self.diffWhenPossible(tailorizer), "")

    def testCvsToMercurial(self):
        "Test CVS to Mercurial"

        tailorizer = Tailorizer('cvs2hg', self.config)
        self.assert_(not tailorizer.exists())
        tailorizer()
        self.assertEqual(self.diffWhenPossible(tailorizer), "")

    def testCvsToBazaarng(self):
        "Test CVS to Bazaar-NG"

        tailorizer = Tailorizer('cvs2bzr', self.config)
        self.assert_(not tailorizer.exists())
        tailorizer()
        self.assertEqual(self.diffWhenPossible(tailorizer), "")

    def testSvndumpToDarcs(self):
        "Test subversion dump to darcs"

        tailorizer = Tailorizer('svndump2darcs', self.config)
        self.assert_(not tailorizer.exists())
        tailorizer()
        self.assertEqual(self.diffWhenPossible(tailorizer), "")
