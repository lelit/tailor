# -*- mode: python; coding: utf-8 -*-
# :Progetto: vcpx -- Tests for the configuration stuff
# :Creato:   mer 03 ago 2005 02:17:18 CEST
# :Autore:   Lele Gaifax <lele@nautilus.homeip.net>
# :Licenza:  GNU General Public License
#

from unittest import TestCase
from vcpx.config import Config, ConfigurationError
from vcpx.project import Project

class Configuration(TestCase):
    "Test the configuration system"

    TESTDIR = None

    def setUp(self):
        from os import mkdir, getcwd
        from os.path import exists, split, join
        from tempfile import gettempdir
        from atexit import register
        from shutil import rmtree

        self.TESTDIR = join(gettempdir(), 'tailor-tests')

        tailor_repo = getcwd()
        while tailor_repo != split(tailor_repo)[0] and not exists(join(tailor_repo, '_darcs')):
            tailor_repo = split(tailor_repo)[0]
        assert exists(join(tailor_repo, '_darcs')), "Tailor Darcs repository not found!"
        self.tailor_repo = tailor_repo
        if not exists(self.TESTDIR):
            mkdir(self.TESTDIR)
            register(rmtree, self.TESTDIR)

    def getTestConfiguration(self, testname):
        from os.path import join, split

        logname = join(split(__file__)[0], 'data', testname)+'.py'
        return file(logname)

    def testBasicConfig(self):
        """Verify the basic configuration mechanism"""

        from os import getcwd
        from os.path import expanduser

        config = Config(self.getTestConfiguration("config-basic_test"),
                        {'tailor_repo': self.tailor_repo})

        self.assertEqual(config.projects(), ['project2'])
        self.assertRaises(ConfigurationError, Project, 'project2', config)

        project1 = Project('project1', config)
        self.assertEqual(project1.rootdir, self.TESTDIR)
        self.assertEqual(project1.source.name, 'svn:project1repo')
        self.assertEqual(project1.target.name, 'darcs:project1')
        self.assertEqual(project1.target.repository, expanduser('~/darcs/project1'))

        project4 = Project('project4', config)
        self.assertEqual(project4.rootdir, getcwd())

        self.assert_(config.namespace.has_key('maybe_skip'))
        self.assert_(config.namespace['refill'] in project1.before_commit)
        self.assertEqual(len(project1.after_commit), 1)

    def testSharedDirs(self):
        """Verify the shared-dir switch"""

        config = Config(self.getTestConfiguration("config-basic_test"),
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

    def testWithLogging(self):
        """Verify a configuration containing also a [[logging]] section"""

        from logging import getLogger

        config = Config(self.getTestConfiguration("config-with_logging"), {})

        logger = getLogger()
        self.assertEqual(logger.handlers[0].formatter._fmt, 'DUMMY')

    def testLookForAdds(self):
        """Verify the darcs Repository knows about --look-for-adds"""

        config = Config(self.getTestConfiguration("config-basic_test"),
                        {'tailor_repo': self.tailor_repo})

        project3 = Project('project3', config)
        self.assertEqual(project3.target.command('record', '-a'),
                         ['darcs', 'record', '-a'])
        project4 = Project('project4', config)
        self.assertEqual(project4.target.command('record', '-a'),
                         ['darcs', 'record', '-a', '--look-for-adds'])

    def testTagEntries(self):
        """Verify the darcs Repository knows when force CVS tag on entries"""

        config = Config(self.getTestConfiguration("config-basic_test"),
                        {'tailor_repo': self.tailor_repo})

        project5 = Project('project5', config)
        self.assertEqual(project5.source.tag_entries, True)
        self.assertEqual(project5.target.tag_entries, False)

    def testStateFileName(self):
        """Verify that the state file is computed the way it should"""

        from os.path import expanduser, join

        config = Config(self.getTestConfiguration("config-basic_test"),
                        {'tailor_repo': self.tailor_repo})

        project1 = Project('project1', config)
        self.assertEqual(project1.state_file.filename, join(self.TESTDIR, 'project1.state'))
        project3 = Project('project3', config)
        self.assertEqual(project3.state_file.filename, join(self.TESTDIR, '_darcs', 'tailor.state'))
        project4 = Project('project4', config)
        self.assertEqual(project4.state_file.filename, expanduser('~/tailorize/project4.state'))
        project6 = Project('project6', config)
        self.assertEqual(project6.state_file.filename, expanduser('~/tailorizedp/project6/.hg/tailor.state'))

        config = Config(self.getTestConfiguration("config-sf_test"), {})
        sbcl = Project('sbcl', config)
        self.assertEqual(sbcl.state_file.filename, expanduser('~/tmp/test-tailor/sbcl/.hg/tailor.state'))

    def testBadChars(self):
        """Test how the config parser loads the badchar mapping"""

        config = Config(self.getTestConfiguration("config-basic_test"),
                        {'tailor_repo': self.tailor_repo})
        project4 = Project('project4', config)
        self.assert_(project4.target.replace_badchars.has_key('\xc1'))
        project6 = Project('project6', config)
        self.assertEqual(project6.source.replace_badchars['a'], 'b')
