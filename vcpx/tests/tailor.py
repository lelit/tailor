# -*- mode: python; coding: utf-8 -*-
# :Progetto: vcpx -- Operational tests
# :Creato:   lun 08 ago 2005 22:17:10 CEST
# :Autore:   Lele Gaifax <lele@nautilus.homeip.net>
# :Licenza:  GNU General Public License
#

"""\
#!tailor
'''
[DEFAULT]
target-module = None
source-repository = %(tailor_repo)s
encoding = None
target-repository = None
use-svn-propset = False
source-module = None
update = True
subdir = test
debug = False
remove-first-log-line = False
patch-name-format = None
verbose = False
state-file = tailor.state
start-revision = Version 0.9.17

[darcs2bzr]
target = bzr:tailor
root-directory = %(testdir)s/darcs2bzr
source = darcs:tailor
patch-name-format = %(revision)s

[bzr2darcs]
source = bzr:tailor
root-directory = %(testdir)s/bzr2darcs
target = darcs:bzrtailor
patch-name-format = %(revision)s
start-revision = INITIAL

[darcs:tailor]

[bzr:tailor]
repository = %(testdir)s/darcs2bzr

[darcs:bzrtailor]


[darcs2cdv]
target = cdv:tailor
root-directory = %(testdir)s/darcs2cdv
source = darcs:tailor

[cdv:tailor]


[darcs2hg]
target = hg:tailor
root-directory = %(testdir)s/darcs2hg
source = darcs:tailor

[hg:tailor]


[darcs2svn]
target = svn:tailor
root-directory = %(testdir)s/darcs2svn
source = darcs:svntailor
start-revision = INITIAL

[svn2darcs]
target = darcs:svntailor
root-directory = %(testdir)s/svn2darcs
source = svn:tailor
start-revision = 1

[svn:tailor]
repository = file://%(testdir)s/svnrepo
module = tailor
subdir = svnside
use-propset = True

[darcs:svntailor]
repository = %(tailor_repo)s
subdir = darcside


[darcs2monotone]
target = monotone:tailor
root-directory = %(testdir)s/darcs2monotone
source = darcs:tailor

[monotone2darcs]
source = monotone:tailor
root-directory = %(testdir)s/monotone2darcs
target = darcs:mtntailor
start-revision = INITIAL

[monotone:tailor]
keyid = tailor
passphrase = fin che la barca va
repository = %(testdir)s/tailor-mtn.db
module = tailor.test
subdir = mntside

[darcs:mtntailor]
subdir = darcside


[cvs2darcs]
target = darcs:pxlib
root-directory = %(testdir)s/cvs2darcs
source = cvs:pxlib
start-revision = R-0-5-1
subdir = pxlib

[darcs:pxlib]

[cvs:pxlib]
repository = :pserver:anonymous@cvs.sf.net:/cvsroot/pxlib
module = pxlib
encoding = iso-8859-1


[darcs2cvs]
target = cvs:tailor
root-directory = %(testdir)s/darcs2cvs
source = darcs:tailor

[cvs:tailor]
repository = :local:%(testdir)s/cvsrepo
module = tailor


[cvs2hg]
root-directory = %(testdir)s/cvs2hg
source = cvs:cmsmini
target = hg:cmsmini
start-revision = INITIAL
subdir = cmsmini
before-commit = remap_authors

[cvs:cmsmini]
repository = :pserver:anonymous@cvs.savannah.nongnu.org:/sources/cmsmini
module = cmsmini

[hg:cmsmini]


[cvs2bzr]
root-directory = %(testdir)s/cvs2bzr
source = cvs:atse
target = bzr:atse
start-revision = spamies-improvement-branch INITIAL
subdir = atse

[cvs:atse]
repository = :pserver:anonymous@cvs.sourceforge.net:/cvsroot/collective
module = ATSchemaEditorNG

[bzr:atse]


[cvs2svn]
source = cvs:cmfeditions-houston-sprint
target = svn:cmfeditions
start-revision = houston-sprint-branch INITIAL
root-directory = %(testdir)s/cvs2svn

[cvs:cmfeditions-houston-sprint]
repository = :pserver:anonymous@cvs.sourceforge.net:/cvsroot/collective
module = CMFEditions
subdir = cvside

[svn:cmfeditions]
repository = file://%(testdir)s/cmfeditions.svnrepo
module = cmfeditions
subdir = svnside


[svn2hg]
source = svn:plonebook
target = hg:plonebook
start-revision = 1101
root-directory = %(testdir)s/svn2hg

[svn:plonebook]
repository = http://docit.bice.dyndns.org
module = /Plone/PloneBook2/it

[hg:plonebook]

[svn2hg_with_externals]
source = svn:plonebook_we
target = hg:plonebook
start-revision = HEAD
root-directory = %(testdir)s/svn2hg_we

[svn:plonebook_we]
repository = http://docit.bice.dyndns.org
module = /Plone/PloneBook2/it
ignore-externals = False


[bazaarng2darcs]
source = bzr:oodoctest
target = darcs:oodoctest
root-directory = %(testdir)s/bazaarng2darcs
start-revision = INITIAL

[bzr:oodoctest]
repository = http://download.gna.org/oodoctest/oodoctest.og.main/

[darcs:oodoctest]
'''

def remap_authors(context, changeset):
    if changeset.author == 'tizziano':
        changeset.author = 'tiziano'
    return True
"""

from unittest import TestCase
from cStringIO import StringIO
from vcpx.config import Config
from vcpx.tailor import Tailorizer
from vcpx.shwrap import ExternalCommand, PIPE

class OperationalTest(TestCase):

    TESTDIR = '/tmp/tailor-tests'

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
        self.config = Config(StringIO(__doc__), {'tailor_repo': tailor_repo,
                                                 'testdir': self.TESTDIR})
        if not exists(self.TESTDIR):
            mkdir(self.TESTDIR)
            register(rmtree, self.TESTDIR)

    def diffWhenPossible(self, tailorizer):
        "Diff the resulting sides"

        dwd = tailorizer.workingDir()
        if not dwd.shared_basedirs:
            cmd = ["diff", "-r", "-u"]
            if tailorizer.source.METADIR:
                cmd.extend(["-x", tailorizer.source.METADIR])
            if tailorizer.target.METADIR:
                cmd.extend(["-x", tailorizer.target.METADIR])
            d = ExternalCommand(command=cmd)
            out = d.execute(dwd.source.basedir, dwd.target.basedir,
                            stdout=PIPE)[0]
            return out.read()
        else:
            return ""

    def tailorize(self, project):
        "The actual test"

        tailorizer = Tailorizer(project, self.config)
        self.assert_(not tailorizer.exists(),
                     "For test purposes, better start from scratch!")
        tailorizer()
        self.assertEqual(self.diffWhenPossible(tailorizer), "")

class Darcs(OperationalTest):
    "Test darcs backend"

    def testConfiguration(self):
        "Test basic configuration"

        from os.path import expanduser

        p = Tailorizer('darcs2svn', self.config)
        self.assertEqual(p.source.subdir, 'darcside')
        self.assertEqual(p.rootdir, '%s/darcs2svn' % self.TESTDIR)
        self.assertEqual(p.source.repository, self.tailor_repo)
        self.assertEqual(p.target.repository,
                         'file://%s/svnrepo' % self.TESTDIR)
        self.assertEqual(p.state_file.filename,
                         '%s/darcs2svn/tailor.state' % self.TESTDIR)

        tailorizer = Tailorizer('cvs2darcs', self.config)
        self.assertEqual(tailorizer.subdir, 'pxlib')
        self.assertEqual(tailorizer.source.subdir, 'pxlib')

    def testDarcsAndBazaarng(self):
        "Test darcs to bazaar-ng and the other way around"

        self.tailorize('darcs2bzr')
        self.tailorize('bzr2darcs')

    def testDarcsToMercurial(self):
        "Test darcs to mercurial"

        self.tailorize('darcs2hg')

    def testDarcsToCodeville(self):
        "Test darcs to codeville"

        self.tailorize('darcs2cdv')

    def testDarcsAndSubversion(self):
        "Test darcs to subversion and the other way around"

        self.tailorize('darcs2svn')
        self.tailorize('svn2darcs')

    def testDarcsAndMonotone(self):
        "Test darcs to monotone and the other way around"

        self.tailorize('darcs2monotone')
        self.tailorize('monotone2darcs')


class Bazaarng(OperationalTest):
    "Test the BazaarNG source backend"

    def testBazaarngToDarcs(self):
        "Test bazaar-ng to darcs"

        self.tailorize('bazaarng2darcs')


class Cvs(OperationalTest):
    "Test the CVS source backend"

    def testCvsToDarcs(self):
        "Test CVS to darcs"

        self.tailorize('cvs2darcs')

    def testDarcsToCvs(self):
        "Test Darcs to CVS"

        self.tailorize('darcs2cvs')

    def testCvsToMercurial(self):
        "Test CVS to mercurial"

        self.tailorize('cvs2hg')

    def testCvsToBazaarng(self):
        "Test CVS to bazaar-ng"

        self.tailorize('cvs2bzr')

    def testCvsToSubversion(self):
        "Test CVS branch to Subversion"

        self.tailorize('cvs2svn')


class Svn(OperationalTest):
    "Test the subversion backend"

    def testExternals(self):
        "Exercise svn to mercurial with and without svn:externals"

        from os.path import exists

        external = self.TESTDIR + '/svn2hg%s/test/make/docutils.make'
        self.tailorize('svn2hg')
        self.failIf(exists(external % ''))

        self.tailorize('svn2hg_with_externals')
        self.failUnless(exists(external % '_we'))
