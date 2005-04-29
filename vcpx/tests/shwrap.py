#  -*- Python -*- -*- coding: iso-8859-1 -*-
# :Progetto: vcpx -- Test shell wrappers
# :Creato:   mar 20 apr 2004 16:49:23 CEST
# :Autore:   Lele Gaifax <lele@nautilus.homeip.net>
# 

from unittest import TestCase, TestSuite
from vcpx.shwrap import SystemCommand, shrepr

class SystemCommandTest(TestCase):
    """Perform some basic tests of the wrapper.
    """

    def testExitStatusForTrue(self):
        """Verify SystemCommand exit_status of ``true``.
        """

        c = SystemCommand('true')
        c()
        self.assertEqual(c.exit_status, 0)

    def testExitStatusForTrueWithOutput(self):
        """Verify SystemCommand exit_status of ``true`` asking output.
        """

        c = SystemCommand('true')
        c(output=True)
        self.assertEqual(c.exit_status, 0)

    def testExitStatusForTrueWithInput(self):
        """Verify SystemCommand exit_status of ``true`` feeding input.
        """

        c = SystemCommand('cat > /dev/null && true')
        c(input="Ciao")
        self.assertEqual(c.exit_status, 0)

    def testExitStatusForTrueWithInputAndOutput(self):
        """Verify SystemCommand exit_status of ``true`` input/output.
        """

        c = SystemCommand('cat > /dev/null && true')
        c(output=True, input="Ciao")
        self.assertEqual(c.exit_status, 0)

    def testExitStatusForFalse(self):
        """Verify SystemCommand exit_status of ``false``.
        """

        c = SystemCommand('false')
        c()
        self.assertNotEqual(c.exit_status, 0)

    def testExitStatusForFalseWithOutput(self):
        """Verify SystemCommand exit_status of ``false`` asking output.
        """

        c = SystemCommand('false')
        c(output=True)
        self.assertNotEqual(c.exit_status, 0)

    def testExitStatusForFalseWithInput(self):
        """Verify SystemCommand exit_status of ``false`` feeding input.
        """

        c = SystemCommand('cat > /dev/null && false')
        c(input="Ciao")
        self.assertNotEqual(c.exit_status, 0)

    def testExitStatusForFalseWithInputAndOutput(self):
        """Verify SystemCommand exit_status of ``false`` input/output.
        """

        c = SystemCommand('cat > /dev/null && false')
        c(output=True, input="Ciao")
        self.assertNotEqual(c.exit_status, 0)

    def testExitStatusUnknownCommand(self):
        """Verify SystemCommand exit_status for non existing command.
        """

        c = SystemCommand('/does/not/exist 2>/dev/null')
        c()
        self.assertNotEqual(c.exit_status, 0)

    def testStandardOutput(self):
        """Verify that SystemCommand redirects stdout."""

        c = SystemCommand('echo "ciao"')
        out = c(output=True)
        self.assertEqual(out.read(), "ciao\n")

    def testWorkingDir(self):
        """Verify that the given command is executed in the specified
        working directory.
        """

        c = SystemCommand('pwd', '/tmp')
        out = c(output=True)
        self.assertEqual(out.read(), "/tmp\n")

    def testQuoting(self):
        """Verifify the quoting mechanism."""

        self.assertEqual(shrepr(r'''doublequote "'''), r'''"doublequote \""''')
        self.assertEqual(shrepr(r'''quote ' backslash \ doublequote "'''),
                         r'''"quote ' backslash \\ doublequote \""''')
