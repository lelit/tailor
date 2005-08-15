# -*- mode: python; coding: iso-8859-1 -*-
# :Progetto: vcpx -- Test shell wrappers
# :Creato:   mar 20 apr 2004 16:49:23 CEST
# :Autore:   Lele Gaifax <lele@nautilus.homeip.net>
# :Licenza:  GNU General Public License
#

from unittest import TestCase, TestSuite
from vcpx.shwrap import ExternalCommand, PIPE

class SystemCommandTest(TestCase):
    """Perform some basic tests of the wrapper.
    """

    def testExitStatusForTrue(self):
        """Verify ExternalCommand exit_status of ``true``.
        """

        c = ExternalCommand(['true'])
        c.execute()
        self.assertEqual(c.exit_status, 0)

    def testExitStatusForFalse(self):
        """Verify ExternalCommand exit_status of ``false``.
        """

        c = ExternalCommand(['false'])
        c.execute()
        self.assertNotEqual(c.exit_status, 0)

    def testExitStatusUnknownCommand(self):
        """Verify ExternalCommand raise OSError for non existing command.
        """

        c = ExternalCommand(['/does/not/exist'])
        self.assertRaises(OSError, c.execute)

    def testStandardOutput(self):
        """Verify that ExternalCommand redirects stdout."""

        c = ExternalCommand(['echo'])
        out = c.execute("ciao", stdout=PIPE)
        self.assertEqual(out.read(), "ciao\n")

    def testWorkingDir(self):
        """Verify that the given command is executed in the specified
        working directory.
        """

        c = ExternalCommand(['pwd'], '/tmp')
        out = c.execute(stdout=PIPE)
        self.assertEqual(out.read(), "/tmp\n")

    def testStringification(self):
        """Verify the conversion from sequence of args to string"""

        c = ExternalCommand(['some spaces here'])
        self.assertEqual(str(c), '$ "some spaces here"')

        c = ExternalCommand(['a "double quoted" arg'])
        self.assertEqual(str(c), r'$ "a \"double quoted\" arg"')

        c = ExternalCommand([r'a \" backslashed quote mark\\'])
        self.assertEqual(str(c), r'$ "a \\\" backslashed quote mark\\\\"')
