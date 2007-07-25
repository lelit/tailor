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

    TESTDIR = None

    ALL_TARGET_VCS = [ 'arx', 'bzr', 'cdv', 'cg', 'cvs', 'cvsps', 'darcs', 'git', 'hg', 'monotone', 'svn' ]

    CONFIG = """\
[%(test_name)s]
# verbose = Yes
source = mock:source
target = %(vcs)s:target
root-directory = %(test_dir)s/rootdir
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
        from tempfile import gettempdir
        from shutil import rmtree
        from atexit import register

        self.TESTDIR = join(gettempdir(), 'tailor-tests', 'fixed-bugs')

        self.test_name = self.id().split('.')[-1]
        self.test_dir  = join(self.TESTDIR, self.test_name)

        if exists(self.test_dir):
            rmtree(self.test_dir)
        makedirs(self.test_dir)
        register(rmtree, self.test_dir)

        # defaults
        self.target_vcs = []
        self.source_changesets = []
        self.shared_basedirs = False

    def run_tailor(self, assert_function=None):
        test_name = self.test_name

        for vcs in self.target_vcs:
            subdir   = self.shared_basedirs and '#' or 'subdir = %s' % vcs
            test_dir = join(self.test_dir, vcs)
            config   = Config(StringIO(self.CONFIG % vars()), {})
            project  = Tailorizer(test_name, config)
            project.workingDir().source.changesets = self.source_changesets
            project()

            if assert_function is not None:
                assert_function(project, vcs)

    def testTicket64(self):
        """#64: support add('foo/bar/baz') even if 'foo' was not previously added"""
        self.target_vcs = [ 'bzr', 'darcs', 'hg' ]
        self.source_changesets = [
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
        self.target_vcs = [ 'bzr', 'darcs', 'hg' ] # XXX bzr 0.8 fails :-?
        self.source_changesets = [
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

    def testTicket74(self):
        """Files must be physically removed on dir removal, so they don't get readded"""
        self.target_vcs = [ 'svn' ] # FAIL: bzr for sure, probably others
        self.source_changesets = [
            Changeset("Add dir/a{1,2,3}",
                [ Entry(Entry.ADDED, 'dir/'),
                  Entry(Entry.ADDED, 'dir/a1'),
                  Entry(Entry.ADDED, 'dir/a2'),
                  Entry(Entry.ADDED, 'dir/a3'),
                ]),
            Changeset("rm dir",
                [ Entry(Entry.DELETED, 'dir/'), ]),
            Changeset("Add dir/z{1,2,3}",
                [ Entry(Entry.ADDED, 'dir/'),
                  Entry(Entry.ADDED, 'dir/z1'),
                  Entry(Entry.ADDED, 'dir/z2'),
                  Entry(Entry.ADDED, 'dir/z3'),
                ]),
        ]
        def assert_function(project, vcs):
            repository = project.workingDir().target.repository
            tree = join(repository.rootdir, repository.subdir)
            for file in ('a1', 'a2', 'a3'):
                self.failIf(exists(join(tree, 'dir', file)))

        self.run_tailor(assert_function)

    def testTicket75(self, shared_basedirs=False):
        """Reorganization of upstream sources with multiple renames (disjunct basedirs)"""

        self.target_vcs = [ 'svn', 'bzr', 'darcs' ]
        self.source_changesets = [
            Changeset("Add dir/a{1,2,3}",
                [ Entry(Entry.ADDED, 'dir/'),
                  Entry(Entry.ADDED, 'dir/a1'),
                  Entry(Entry.ADDED, 'dir/a2'),
                  Entry(Entry.ADDED, 'dir/a3'),
                ]),
            Changeset("Spread around",
                [ Entry(Entry.RENAMED, 'a.root', 'dir/a1'),
                  Entry(Entry.RENAMED, 'b.root', 'dir/a2'),
                  Entry(Entry.RENAMED, 'newdir/', 'dir/'),
                  Entry(Entry.UPDATED, 'newdir/a3', contents="ciao"),
                ]),
        ]

        def assert_function(project, vcs):
            repository = project.workingDir().target.repository
            tree = join(repository.rootdir, repository.subdir)
            for file in ('a1', 'a2', 'a3'):
                self.failIf(exists(join(tree, 'dir', file)))
            self.failIf(not exists(join(tree, 'newdir/a3')))
            self.failIf(open(join(tree, 'newdir/a3')).read() <> 'ciao')

        self.shared_basedirs = shared_basedirs
        self.run_tailor(assert_function)

    def testTicket75_2(self):
        """Reorganization of upstream sources with multiple renames (shared basedirs)"""

        self.testTicket75(shared_basedirs=True)
