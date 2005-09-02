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

    BASIC_TEST = """\
#!tailor
'''
[DEFAULT]
verbose = Yes
target-module = None
projects = project2

[project1]
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
root-directory = /tmp/test
source = darcs:project1repo
target = svn:project2repo
refill-changelogs = Yes
state-file = project2.state
before-commit = refill

[svn:project2repo]
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

        config = Config(StringIO(self.BASIC_TEST), {})
        self.assertEqual(config.projects(), ['project2'])

    def testValidation(self):
        """Verify Repository validation mechanism"""

        config = Config(StringIO(self.BASIC_TEST), {})
        self.assertRaises(ConfigurationError, Project, 'project2', config)
