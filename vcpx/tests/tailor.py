# -*- mode: python; coding: utf-8 -*-
# :Progetto: vcpx -- Operational tests
# :Creato:   lun 08 ago 2005 22:17:10 CEST
# :Autore:   Lele Gaifax <lele@nautilus.homeip.net>
# :Licenza:  GNU General Public License
#

"""
[DEFAULT]
dont-refill-changelogs = False
target-kind = hg
target-module = None
source-repository = /home/lele/WiP/cvsync
encoding = None
target-repository = None
use-svn-propset = False
source-module = None
update = True
source-kind = darcs
subdir = .
debug = True
remove-first-log-line = False
patch-name-format = None
verbose = True
state-file = tailor.state
start-revision = Almost arbitrarily tagging this as version 0.8

[darcs2hg]
target = hg:tailor
root-directory = /tmp/tailor-tests/darcs2hg
source = darcs:tailor

[darcs2svn]
target = svn:tailor
root-directory = /tmp/tailor-tests/darcs2svn
source = darcs:tailor

[darcs:tailor]
repository = ~/WiP/cvsync

[hg:tailor]

[svn:tailor]
repository = file:///tmp/tailor-tests/svnrepo
module = tailor
"""

from unittest import TestCase, TestSuite
from cStringIO import StringIO
from vcpx.config import Config
from vcpx.tailor import Tailorizer

class BootstrapOptions:
    bootstrap = True

class UpdateOptions:
    bootstrap = False

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

    def testDarcsToSubversionBootstrap(self):
        "Test darcs to subversion bootstrap"

        project = self.config['darcs2svn']
        tailorizer = Tailorizer(project)
        tailorizer(BootstrapOptions())

    def testDarcsToSubversionUpdate(self):
        "Test darcs to subversion update"

        project = self.config['darcs2svn']
        tailorizer = Tailorizer(project)
        tailorizer(UpdateOptions())

    def testDarcsToMercurialBootstrap(self):
        "Test darcs to mercurial bootstrap"

        project = self.config['darcs2hg']
        tailorizer = Tailorizer(project)
        tailorizer(BootstrapOptions())

    def testDarcsToMercurialUpdate(self):
        "Test darcs to mercurial update"

        project = self.config['darcs2hg']
        tailorizer = Tailorizer(project)
        tailorizer(UpdateOptions())
