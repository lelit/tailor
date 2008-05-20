# -*- mode: python; coding: iso-8859-1 -*-
# :Progetto: vcpx -- Test shell wrappers
# :Creato:   mar 20 apr 2004 16:49:23 CEST
# :Autore:   Lele Gaifax <lele@nautilus.homeip.net>
# :Licenza:  GNU General Public License
#

from unittest import TestCase
from vcpx.shwrap import ExternalCommand, PIPE
from sys import platform
from tempfile import gettempdir


class SystemCommand(TestCase):
    """Perform some basic tests of the wrapper"""

    def testExitStatusForTrue(self):
        """Verify ExternalCommand exit_status of ``true``.
        """

        if platform != 'win32':
            c = ExternalCommand(['true'])
        else:
            c = ExternalCommand(['cmd','/c exit 0'])
        c.execute()
        self.assertEqual(c.exit_status, 0)

    def testExitStatusForFalse(self):
        """Verify ExternalCommand exit_status of ``false``.
        """

        if platform != 'win32':
            c = ExternalCommand(['false'])
        else:
            c = ExternalCommand(['cmd','/c exit 1'])
        c.execute()
        self.assertNotEqual(c.exit_status, 0)

    def testOkStatus(self):
        """Verify the log on exit_status"""

        class Logger:
            def warning(self, *args):
                raise Exception('should not happen: %s' % str(args))

            def info(self, *args):
                pass

            def debug(self, *args):
                pass

        if platform != 'win32':
            c = ExternalCommand(['false'], ok_status=(0,1))
        else:
            c = ExternalCommand(['cmd','/c exit 1'], ok_status=(0,1))
        c.execute()

        c.log = Logger()
        c.execute()

    def testExitStatusUnknownCommand(self):
        """Verify ExternalCommand raise OSError for non existing command.
        """

        c = ExternalCommand(['/does/not/exist'])
        self.assertRaises(OSError, c.execute)

    def testStandardOutput(self):
        """Verify that ExternalCommand redirects stdout."""

        if platform != 'win32':
            c = ExternalCommand(['echo'])
        else:
            c = ExternalCommand(['cmd','/c','echo'])
        out = c.execute("ciao", stdout=PIPE)[0]
        self.assertEqual(out.read(), "ciao\n")

        if platform != 'win32':
            out = c.execute('-n', stdout=PIPE)[0]
            self.assertEqual(out.read(), '')

        out = c.execute("ciao")[0]
        self.assertEqual(out, None)

    def testStandardError(self):
        """Verify that ExternalCommand redirects stderr."""

        c = ExternalCommand(['darcs', 'ciao'])
        out, err = c.execute("ciao", stdout=PIPE, stderr=PIPE)
        self.assert_("darcs failed" in err.read())

    def testWorkingDir(self):
        """Verify that the given command is executed in the specified
        working directory.
        """

        tempdir = gettempdir()
        if platform != 'win32':
            c = ExternalCommand(['pwd'], tempdir)
        else:
            c = ExternalCommand(['cmd','/c','cd'], tempdir)
        out = c.execute(stdout=PIPE)[0]
        self.assertEqual(out.read(), tempdir+"\n")

    def testStringification(self):
        """Verify the conversion from sequence of args to string"""

        c = ExternalCommand(['some spaces here'])
        self.assertEqual(str(c), '$ "some spaces here"')

        c = ExternalCommand(['a "double quoted" arg'])
        self.assertEqual(str(c), r'$ "a \"double quoted\" arg"')

        c = ExternalCommand([r'a \" backslashed quote mark\\'])
        self.assertEqual(str(c), r'$ "a \\\" backslashed quote mark\\\\"')

    def testSplittedExecution(self):
        """Verify the mechanism that avoids too long command lines"""

        args = [str(i) * 20 for i in range(10)]
        if platform != 'win32':
            c = ExternalCommand(['echo'])
        else:
            c = ExternalCommand(['cmd','/c','echo'])
        c.MAX_CMDLINE_LENGTH = 30
        out = c.execute(args, stdout=PIPE)[0]
        self.assertEqual(out.read(), '\n'.join([args[i]+' '+args[i+1]
                                                for i in range(0,10,2)])+'\n')

        c = ExternalCommand(['echo'])
        c.MAX_CMDLINE_LENGTH = None
        out = c.execute(args, stdout=PIPE)[0]
        self.assertEqual(out.read(), ' '.join(args)+'\n')
