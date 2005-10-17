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
subdir = .
debug = False
remove-first-log-line = False
patch-name-format = None
verbose = True
state-file = tailor.state
start-revision = Version 0.9.17

[darcs2bzr]
target = bzr:tailor
root-directory = /tmp/tailor-tests/darcs2bzr
source = darcs:tailor
patch-name-format = %(revision)s

[bzr2darcs]
source = bzr:tailor
root-directory = /tmp/tailor-tests/bzr2darcs
target = darcs:bzrtailor
patch-name-format = %(revision)s

[darcs:tailor]

[bzr:tailor]
python-path = /opt/src/bzr.dev


[darcs2cdv]
target = cdv:tailor
root-directory = /tmp/tailor-tests/darcs2cdv
source = darcs:tailor

[cdv:tailor]


[darcs2hg]
target = hg:tailor
root-directory = /tmp/tailor-tests/darcs2hg
source = darcs:tailor

[hg:tailor]


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

[svn:tailor]
repository = file:///tmp/tailor-tests/svnrepo
module = tailor
subdir = svnside
use-propset = True

[darcs:svntailor]
subdir = darcside


[darcs2monotone]
target = monotone:tailor
root-directory = /tmp/tailor-tests/darcs2monotone
source = darcs:tailor

[monotone2darcs]
source = monotone:tailor
root-directory = /tmp/tailor-tests/darcs2monotone
target = darcs:mtntailor
start-revision = INITIAL

[monotone:tailor]
keyid = tailor
passphrase = fin che la barca va
repository = /tmp/tailor-tests/tailor-mtn.db
module = tailor.test

[darcs:mtntailor]
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
encoding = iso-8859-1


[cvs2hglib]
root-directory = /tmp/tailor-tests/cvs2hglib
source = cvs:cmsmini
target = hglib:cmsmini
start-revision = INITIAL
subdir = cmsmini
before-commit = remap_authors

[cvs:cmsmini]
repository = :ext:anoncvs@savannah.nongnu.org:/cvsroot/cmsmini
module = cmsmini

[hglib:cmsmini]


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
python-path = /opt/src/bzr.dev


[svndump2darcs]
source = svndump:simple
target = darcs:simple
root-directory = /tmp/tailor-tests/svndump2darcs
subdir = simple
start-revision = INITIAL

[svndump:simple]
repository = %(tailor_repo)s/vcpx/tests/data/simple.svndump
subdir = plain

[darcs:simple]
subdir = .


[svndump2hg]
source = svndump:pyobjc
target = hg:pyobjc
root-directory = /tmp/tailor-tests/svndump2hg
start-revision = INITIAL

[svndump:pyobjc]
repository = %(tailor_repo)s/pyobjc.svndump
subdir = plain

[hg:pyobjc]
subdir = hg


[svndump2hg-partial]
source = svndump:simple-partial
target = hg:simple-partial
root-directory = /tmp/tailor-tests/svndump2hg-partial
start-revision = INITIAL

[svndump:simple-partial]
repository = %(tailor_repo)s/vcpx/tests/data/simple.svndump
#repository = /usr/local/tmp/docit.svndump
module = subdir
subdir = plain

[hg:simple-partial]
subdir = hg


[cvs2svn]
source = cvs:cmfeditions-houston-sprint
target = svn:cmfeditions
start-revision = houston-sprint-branch INITIAL
root-directory = /tmp/tailor-tests/cvs2svn

[cvs:cmfeditions-houston-sprint]
repository = :pserver:anonymous@cvs.sourceforge.net:/cvsroot/collective
module = CMFEditions
subdir = cvside

[svn:cmfeditions]
repository = file:///tmp/tailor-tests/cmfeditions.svnrepo
module = cmfeditions
subdir = svnside
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
            #register(rmtree, '/tmp/tailor-tests')

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
        self.assert_(not tailorizer.exists())
        tailorizer()
        self.assertEqual(self.diffWhenPossible(tailorizer), "")

class Darcs(OperationalTest):
    "Test darcs backend"

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


class Cvs(OperationalTest):
    "Test the CVS source backend"

    def testCvsToDarcs(self):
        "Test CVS to darcs"

        self.tailorize('cvs2darcs')

    def testCvsToMercurial(self):
        "Test CVS to mercurial"

        self.tailorize('cvs2hglib')

    def testCvsToBazaarng(self):
        "Test CVS to bazaar-ng"

        self.tailorize('cvs2bzr')

    def testCvsToSubversion(self):
        "Test CVS branch to Subversion"

        self.tailorize('cvs2svn')


class Svndump(OperationalTest):
    "Test the svndump source backend (deprecated)"

    def testSvndumpToDarcs(self):
        "Test subversion dump to darcs"

        self.tailorize('svndump2darcs')

    def testSvndumpToMercurial(self):
        "Test subversion dump to mercurial"

        self.tailorize('svndump2hg')

    def testPartialSvndumpToMercurial(self):
        "Test partial subversion dump to mercurial"

        self.tailorize('svndump2hg-partial')
