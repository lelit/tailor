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
use-propset = False
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
keygenid = tailor
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
repository = :pserver:anonymous@pxlib.cvs.sourceforce.net:/cvsroot/pxlib
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
repository = :pserver:anonymous@collective.cvs.sourceforge.net:/cvsroot/collective
module = ATSchemaEditorNG

[bzr:atse]


[cvs2svn]
source = cvs:cmfeditions-houston-sprint
target = svn:cmfeditions
start-revision = houston-sprint-branch INITIAL
root-directory = %(testdir)s/cvs2svn

[cvs:cmfeditions-houston-sprint]
repository = :pserver:anonymous@collective.cvs.sourceforge.net:/cvsroot/collective
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


[bazaar2darcs]
source = bzr:oodoctest
target = darcs:oodoctest
root-directory = %(testdir)s/bazaar2darcs
start-revision = INITIAL

[bzr:oodoctest]
repository = http://download.gna.org/oodoctest/oodoctest.og.main/

[darcs:oodoctest]


[darcs_rename_delete]
source = darcs:darcs_rename_delete
target = svn:darcs_rename_delete
root-directory = %(testdir)s/darcs_rename_delete
start-revision = INITIAL

[darcs:darcs_rename_delete]
repository = %(testdir)s/rename_delete
subdir = darcs

[svn:darcs_rename_delete]
repository = file://%(testdir)s/darcs_rename_delete.svnrepo
module = /
subdir = svn


[darcs_rename_delete_dir]
source = darcs:darcs_rename_delete_dir
target = svn:darcs_rename_delete_dir
root-directory = %(testdir)s/darcs_rename_delete_dir
start-revision = INITIAL

[darcs:darcs_rename_delete_dir]
repository = %(testdir)s/rename_delete_dir
subdir = darcs

[svn:darcs_rename_delete_dir]
repository = file://%(testdir)s/darcs_rename_delete_dir.svnrepo
module = /
subdir = svn


[cvsdirtest]
target = bzr:cvsdirtest
start-revision = INITIAL
root-directory = %(testdir)s/cvsdirtest/cvs2bzr
source = cvs:cvsdirtest
subdir = test-work

[cvspsdirtest]
target = bzr:cvsdirtest
start-revision = INITIAL
root-directory = %(testdir)s/cvsdirtest/cvsps2bzr
source = cvsps:cvsdirtest
subdir = test-work

[darcsdirtest]
target = darcs:cvsdirtest
start-revision = INITIAL
root-directory = %(testdir)s/cvsdirtest/cvs2darcs
source = cvs:cvsdirtest
subdir = test-work

[svndirtest]
target = svn:cvsdirtest
start-revision = INITIAL
root-directory = %(testdir)s/cvsdirtest/cvs2svn
source = cvs:cvsdirtest
subdir = test-work

[bzr:cvsdirtest]

[darcs:cvsdirtest]

[cvs:cvsdirtest]
module = test
repository = %(testdir)s/cvsdirtest.cvsrepo

[cvsps:cvsdirtest]
module = test
repository = %(testdir)s/cvsdirtest.cvsrepo

[svn:cvsdirtest]
module = test
repository = file://%(testdir)s/cvsdirtest.svnrepo

[svnresurdirtest]
target = svn:cvsresurdirtest
start-revision = INITIAL
root-directory = %(testdir)s/cvsresurdirtest/cvs2svn
source = cvs:cvsresurdirtest
subdir = test-work

[cvs:cvsresurdirtest]
module = test
repository = %(testdir)s/cvsresurdirtest.cvsrepo

[svn:cvsresurdirtest]
module = test
repository = file://%(testdir)s/cvsresurdirtest.svnrepo

'''

def remap_authors(context, changeset):
    if changeset.author == 'tizziano':
        changeset.author = 'tiziano'
    return True
"""

from unittest import TestCase
from cStringIO import StringIO
from vcpx import TailorException
from vcpx.config import Config
from vcpx.tailor import Tailorizer
from vcpx.shwrap import ExternalCommand, PIPE


class OperationalTest(TestCase):

    TESTDIR = None

    def setUp(self):
        from os import mkdir, getcwd
        from os.path import exists, split, join
        from tempfile import gettempdir
        from atexit import register
        from shutil import rmtree
        from vcpx.tests import DEBUG

        self.TESTDIR = join(gettempdir(), 'tailor-tests')

        tailor_repo = getcwd()
        while tailor_repo != split(tailor_repo)[0] and not exists(join(tailor_repo, '_darcs')):
            tailor_repo = split(tailor_repo)[0]
        assert exists(join(tailor_repo, '_darcs')), "Tailor Darcs repository not found!"
        self.tailor_repo = tailor_repo
        self.config = Config(StringIO(__doc__), {'tailor_repo': tailor_repo,
                                                 'testdir': self.TESTDIR,
                                                 'verbose': DEBUG})

        if not exists(self.TESTDIR):
            mkdir(self.TESTDIR)
            register(rmtree, self.TESTDIR)

    def diffWhenPossible(self, tailorizer):
        "Diff the resulting sides"

        from vcpx.tests import DEBUG

        dwd = tailorizer.workingDir()
        if not dwd.shared_basedirs:
            cmd = ["diff", "-r", "-u"]
            if tailorizer.source.METADIR:
                cmd.extend(["-x", tailorizer.source.METADIR])
            if tailorizer.target.METADIR:
                cmd.extend(["-x", tailorizer.target.METADIR])
            d = ExternalCommand(command=cmd, nolog=not DEBUG)
            out = d.execute(dwd.source.repository.basedir,
                            dwd.target.repository.basedir,
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

    def testDarcsAndBazaar(self):
        "Test darcs to Bazaar and the other way around"

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


class Bazaar(OperationalTest):
    "Test the Bazaar source backend"

    def testBazaarAndPython23(self):
        "Bazaar test we detect early when running under Python < 2.4"

        from sys import version_info

        if version_info < (2,4):
            try:
                self.tailorize('bazaar2darcs')
            except TailorException, e:
                self.assert_("Bazaar backend requires Python 2.4"
                             in str(e))
            else:
                self.fail("Expected a specific TailorException")

    def testBazaarToDarcs(self):
        "Test bazaar to darcs"

        try:
            self.tailorize('bazaar2darcs')
        except TailorException, e:
            from sys import version_info

            if version_info < (2,4):
                # Under python 2.3 we expect an exception here, but
                # different from the above: since we are still in a
                # single python session importing the bzr stuff does
                # not raise the same error, because from the python
                # runtime pov the module is already loaded and thus
                # the second import does not fail. The repository
                # class will then instantiate the raw Repository
                # class, not the specific bzr one. Still, when asked
                # for a working dir, it will fail again
                self.assert_("object has no attribute 'BzrWorkingDir'"
                             in str(e))
            else:
                raise



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

    def testCvsToBazaar(self):
        "Test CVS to Bazaar"

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

    def testDarcsRenameDelete(self):
        "Try to migrate a darcs patch that renames and removes the same file"

        from os import mkdir
        from os.path import join
        from vcpx.tests import DEBUG

        drepo = join(self.TESTDIR, 'rename_delete')
        mkdir(drepo)

        darcs = ExternalCommand(command=['darcs'], cwd=drepo, nolog=not DEBUG)

        darcs.execute('init')

        fileA = join(drepo, 'fileA')
        open(fileA, 'w')
        darcs.execute('add', fileA)
        darcs.execute('record', '-a', '-m', 'Add A')

        fileB = join(drepo, 'fileB')
        darcs.execute('mv', fileA, fileB)

        darcs.execute('remove', fileB)

        darcs.execute('record', '-a', '-m', 'Move A to B and delete B')

        self.tailorize('darcs_rename_delete')

    def testDarcsRenameDeleteDir(self):
        "Test if darcs to svn fails on moves combined with directory deletes"

        from os import mkdir
        from os.path import join
        from vcpx.tests import DEBUG

        drepo = join(self.TESTDIR, 'rename_delete_dir')
        mkdir(drepo)

        darcs = ExternalCommand(command=['darcs'], cwd=drepo, nolog=not DEBUG)

        darcs.execute('init')

        dir = join(drepo, 'dir')
        mkdir(dir)
        darcs.execute('add', dir)
        fileA = join(dir, 'fileA')
        open(fileA, 'w')
        darcs.execute('add', fileA)

        darcs.execute('record', '-a', '-m', 'Add dir and dir/A')

        fileB = join(drepo, 'fileA')
        darcs.execute('rename', fileA, fileB)

        darcs.execute('remove', dir)

        darcs.execute('record', '-a', '-m', 'Move dir/A to A and delete dir')

        self.tailorize('darcs_rename_delete_dir')


class CvsOrderTest(OperationalTest):
    """Test problems with improper ordering of adds with new directories."""

    def setUp(self):
        """Create a CVS repository that has the difficult history."""

        from os import mkdir, getcwd
        from os.path import join, exists
        from vcpx.tests import DEBUG

        super(CvsOrderTest, self).setUp()

        repodir = join(self.TESTDIR, 'cvsdirtest.cvsrepo')
        basedir = join(self.TESTDIR, 'cvsdirtest')

        if not exists(repodir):
            cvscmd = ['cvs', '-d', repodir]
            mkdir(basedir)
            mkdir(repodir)
            startdir = join(basedir, 'start')
            mkdir(startdir)

            cvs = ExternalCommand(cwd=startdir, nolog=not DEBUG, command=cvscmd)
            cvs.execute('init')
            self.failIf(cvs.exit_status, "%r failed" % cvs._last_command)

            open(join(startdir, 'foo'), "w").close()

            cvs.execute('import', '-m', 'one', 'test', 'test', 'test1')
            self.failIf(cvs.exit_status, "%r failed" % cvs._last_command)

            workdir = join(basedir, 'work')
            cvs.execute('checkout', '-d', workdir, 'test')
            self.failIf(cvs.exit_status, "%r failed" % cvs._last_command)

            bardir = join(workdir, 'bar')
            mkdir(bardir)
            baz = join(bardir, 'baz')
            open(baz, "w").close()

            cvs.execute('add', bardir, baz)
            self.failIf(cvs.exit_status, "%r failed" % cvs._last_command)
            cvs.execute('commit', '-m', 'two')
            self.failIf(cvs.exit_status, "%r failed" % cvs._last_command)

    def testCvsConvertDirectoryAddToBazaar(self):
        """Test that we can handle directory adds in the cvs module to bzr."""

        t = Tailorizer("cvsdirtest", self.config)
        t()

    def testCvspsConvertDirectoryAddToBazaar(self):
        """Test that we can handle directory adds in the cvsps module to bzr."""

        t = Tailorizer("cvspsdirtest", self.config)
        t()

    def testCvsConvertDirectoryAddToDarcs(self):
        """Test that we can handle directory adds in the cvs module to darcs."""

        t = Tailorizer("darcsdirtest", self.config)
        t()

    def testCvsConvertDirectoryAddToSubversion(self):
        """Test that we can handle directory adds in the cvs module to svn."""

        t = Tailorizer("svndirtest", self.config)
        t()


class CvsReappearedDirectory(OperationalTest):
    """Test problems with resurrected directories."""

    def setUp(self):
        """Create a CVS repository that has the difficult history."""

        from os import mkdir, getcwd
        from os.path import join, exists
        from time import sleep
        from shutil import rmtree
        from vcpx.tests import DEBUG

        super(CvsReappearedDirectory, self).setUp()

        repodir = join(self.TESTDIR, 'cvsresurdirtest.cvsrepo')
        basedir = join(self.TESTDIR, 'cvsresurdirtest')

        if not exists(repodir):
            mkdir(basedir)
            mkdir(repodir)
            startdir = join(basedir, 'start')
            mkdir(startdir)

            cvs = ExternalCommand(cwd=startdir, nolog=not DEBUG, command=['cvs', '-d', repodir])
            cvs.execute('init')
            self.failIf(cvs.exit_status, "%r failed" % cvs._last_command)

            open(join(startdir, 'foo'), "w").close()

            cvs.execute('import', '-m', 'one', 'test', 'test', 'test1')
            self.failIf(cvs.exit_status, "%r failed" % cvs._last_command)

            workdir = join(basedir, 'work')
            cvs.execute('checkout', '-d', workdir, 'test')
            self.failIf(cvs.exit_status, "%r failed" % cvs._last_command)

            cvs = ExternalCommand(cwd=workdir, nolog=not DEBUG, command=['cvs'])
            bardir = join(workdir, 'bar')
            mkdir(bardir)
            baz = join(bardir, 'baz')
            open(baz, "w").close()

            cvs.execute('add', bardir, baz)
            self.failIf(cvs.exit_status, "%r failed" % cvs._last_command)
            cvs.execute('commit', '-m', 'two', baz)
            self.failIf(cvs.exit_status, "%r failed" % cvs._last_command)
            sleep(1)

            cvs.execute('rm', '-f', baz)
            self.failIf(cvs.exit_status, "%r failed" % cvs._last_command)
            cvs.execute('commit', '-m', 'three', baz)
            self.failIf(cvs.exit_status, "%r failed" % cvs._last_command)
            cvs.execute('update', '-dP')
            self.failIf(cvs.exit_status, "%r failed" % cvs._last_command)
            sleep(1)

            mkdir(bardir)
            again = join(bardir, 'again')
            open(again, "w").close()

            cvs.execute('add', bardir, again)
            self.failIf(cvs.exit_status, "%r failed" % cvs._last_command)
            cvs.execute('commit', '-m', 'four', again)
            self.failIf(cvs.exit_status, "%r failed" % cvs._last_command)

    def testCvsReappearedDirectoryToSubversion(self):
        """Test that we can handle resurrected cvs directory to svn."""

        from vcpx.tests import DEBUG

        t = Tailorizer("svnresurdirtest", self.config)
        t()

        svnls = ExternalCommand(nolog=not DEBUG, command=['svn', 'ls'])
        manifest = svnls.execute('file://%s/cvsresurdirtest.svnrepo/test/bar' % self.TESTDIR,
                                 stdout=PIPE)[0]
        self.assertEqual(manifest.read(), "again\n")
