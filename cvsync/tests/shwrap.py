#  -*- Python -*- -*- coding: iso-8859-1 -*-
# :Progetto: Bice -- Test shell wrappers
# :Sorgente: $HeadURL: http://svn.bice.dyndns.org/progetti/wip/tools/cvsync/tests/shwrap.py $
# :Creato:   mar 20 apr 2004 16:49:23 CEST
# :Autore:   Lele Gaifax <lele@nautilus.homeip.net>
# :Modifica: $LastChangedDate: 2004-04-23 15:24:11 +0200 (ven, 23 apr 2004) $
# :Fatta da: $LastChangedBy: lele $
# 

from unittest import TestCase, TestSuite
from cvsync.shwrap import SystemCommand

class SystemCommandTest(TestCase):
    """Perform some basic tests of the wrapper.
    """

    def testExitStatusForTrue(self):
        """Verify SystemCommand exit_status of ``true``.
        """

        c = SystemCommand('true')
        c()
        self.assertEqual(c.exit_status, 0)


    def testExitStatusForFalse(self):
        """Verify SystemCommand exit_status of ``false``.
        """

        c = SystemCommand('false')
        c()
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

