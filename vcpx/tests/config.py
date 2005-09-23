# -*- mode: python; coding: utf-8 -*-
# :Progetto: vcpx -- Tests for the configuration stuff
# :Creato:   mer 03 ago 2005 02:17:18 CEST
# :Autore:   Lele Gaifax <lele@nautilus.homeip.net>
# :Licenza:  GNU General Public License
#

from unittest import TestCase, TestSuite
from cStringIO import StringIO
from vcpx.config import Config, ConfigurationError
from vcpx.project import Project

class ConfigTest(TestCase):

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
        if not exists('/tmp/tailor-tests'):
            mkdir('/tmp/tailor-tests')
            register(rmtree, '/tmp/tailor-tests')

    BASIC_TEST = """\
#!tailor
'''
[DEFAULT]
verbose = False
target-module = None
projects = project2

[project1]
root-directory = /tmp/tailor-tests
source = svn:project1repo
target = darcs:project1repo
refill-changelogs = Yes
state-file = project1.state
before-commit = (maybe_skip, refill, p1_remap_authors)
after-commit = checkpoint

[svn:project1repo]
repository = svn://some.server/svn
module = project1
use-propset = Yes

[darcs:project1repo]
repository = ~/darcs/project1

[monotone:project1repo]
repository = /tmp/db
passphrase = simba

[project2]
root-directory = /tmp/tailor-tests
source = darcs:project1repo
target = svn:project2repo
refill-changelogs = Yes
state-file = project2.state
before-commit = refill

[svn:project2repo]

[project3]
root-directory = /tmp/tailor-tests
source = svndump:project3repo
target = darcs:project3repo

[svndump:project3repo]
repository = %(tailor_repo)s/vcpx/tests/data/simple.svndump
subdir = plain

[darcs:project3repo]
subdir = .

[project4]
source = svndump:project3repo
target = darcs:project4repo

[darcs:project4repo]
subdir = darcs
'''

def maybe_skip(context, changeset):
    for e in changeset.entries:
        if not context.darcs.isBoringFile(e):
            return True
    # What a bunch of boring entries! Skip the patch
    return False

def refill(context, changeset):
    changeset.refillChangelog()
    return True

p1_authors_map = {
    'lele': 'Lele Gaifax <lele@example.com>',
    'x123': 'A man ... with a name to come',
}

def p1_remap_authors(context, changeset):
    if p1_authors_map.has_key(changeset.author):
        changeset.author = p1_authors_map[changeset.author]
    return True

def checkpoint(context, changeset):
    if changeset.log.startswith('Release '):
        context.target.tagWithCheckpoint(changeset.log)
    return True
"""

    def testBasicConfig(self):
        """Verify the configuration mechanism"""

        config = Config(StringIO(self.BASIC_TEST),
                        {'tailor_repo': self.tailor_repo})
        self.assertEqual(config.projects(), ['project2'])

    def testValidation(self):
        """Verify Repository validation mechanism"""

        config = Config(StringIO(self.BASIC_TEST),
                         {'tailor_repo': self.tailor_repo})
        self.assertRaises(ConfigurationError, Project, 'project2', config)

    def testSharedDirs(self):
        """Verify the shared-dir switch"""

        config = Config(StringIO(self.BASIC_TEST),
                        {'tailor_repo': self.tailor_repo})

        project1 = Project('project1', config)
        wd = project1.workingDir()
        self.assert_(wd.shared_basedirs)

        project3 = Project('project3', config)
        wd = project3.workingDir()
        self.assert_(wd.shared_basedirs)

        project4 = Project('project4', config)
        wd = project4.workingDir()
        self.assert_(not wd.shared_basedirs)

    def testRootDirectory(self):
        """Verify the root-directory expansion"""

        from os import getcwd

        config = Config(StringIO(self.BASIC_TEST),
                        {'tailor_repo': self.tailor_repo})

        project1 = Project('project1', config)
        self.assertEqual(project1.rootdir, '/tmp/tailor-tests')

        project4 = Project('project4', config)
        self.assertEqual(project4.rootdir, getcwd())
