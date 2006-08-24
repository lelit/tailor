# -*- mode: python; coding: utf-8 -*-
# :Progetto: vcpx -- Prevents reintroduced bugs
# :Creato:   Sun Jul 16 02:50:04 CEST 2006
# :Autore:   Adeodato Simó <dato@net.com.org.es>
# :Licenza:  GNU General Public License
#

from os.path import exists, join
from unittest import TestCase
from cStringIO import StringIO

from vcpx.config import Config
from vcpx.tailor import Tailorizer
from vcpx.repository.mock import MockChangeset as Changeset, \
                                 MockChangesetEntry as Entry


class FixedBugs(TestCase):
    """Ensure already fixed bugs don't get reintroduced"""

    TESTDIR = '/tmp/tailor-tests/fixed-bugs'

    ALL_TARGET_VCS = [ 'arx', 'bzr', 'cdv', 'cg', 'cvs', 'cvsps', 'darcs', 'git', 'hg', 'monotone', 'svn' ]

    CONFIG = """\
[%(test_name)s]
# verbose = Yes
source = mock:source
target = %(vcs)s:target
root-directory = %(test_dir)s
state-file = state

[mock:source]
%(subdir)s.source

[%(vcs)s:target]
%(subdir)s
module = /
repository = file://%(test_dir)s/repo
"""

    def setUp(self):
        from os import makedirs
        from shutil import rmtree
        from atexit import register

        self.test_name = self.id().split('.')[-1]
        self.test_dir  = join(self.TESTDIR, self.test_name)

        if exists(self.test_dir):
            rmtree(self.test_dir)
        makedirs(self.test_dir)
        register(rmtree, self.test_dir)

        # defaults
        self.TARGET_VCS = []
        self.CHANGESETS = []
        self.SHARED_BASEDIRS = False

    def run_tailor(self, assert_function=None):
        test_name = self.test_name

        for vcs in self.TARGET_VCS:
            subdir   = self.SHARED_BASEDIRS and '#' or 'subdir = %s' % vcs
            test_dir = join(self.test_dir, vcs)
            config   = Config(StringIO(self.CONFIG % vars()), {})
            project  = Tailorizer(test_name, config)
            project.workingDir().source.changesets = self.CHANGESETS
            project()

            if assert_function is not None:
                assert_function(project, vcs)

    def testTicket64(self):
        """#64: support add('foo/bar/baz') even if 'foo' was not previously added"""
        self.TARGET_VCS = [ 'bzr', 'darcs', 'hg' ]
        self.CHANGESETS = [
            Changeset("Dummy first commit",
                [ Entry(Entry.ADDED, 'dummy.txt'), ]),
            Changeset("Add a/b/c",
                [ Entry(Entry.ADDED, 'a/b/'),
                  Entry(Entry.ADDED, 'a/b/c'),
            ]),
        ]
        self.run_tailor()

    def testTicket64_2(self):
        """#64 (2): support update('foo2/bar') even if 'foo2' is added in the same changeset"""
        self.TARGET_VCS = [ 'bzr', 'darcs', 'hg' ] # XXX bzr 0.8 fails :-?
        self.CHANGESETS = [
            Changeset("Dummy first commit",
                [ Entry(Entry.ADDED, 'dummy.txt'), ]),
            Changeset("Add a/b/c",
                [ Entry(Entry.ADDED, 'a/b/c'),
            ]),
            Changeset("Add (cp) a2 and modify a2/b/c",
                [ Entry(Entry.ADDED, 'a2/b/c'),
                  Entry(Entry.UPDATED, 'a2/b/c', contents='foo')
            ]),
        ]
        self.run_tailor()
