# -*- mode: python; coding: iso-8859-1 -*-
# :Progetto: vcpx -- Tiny wrapper around external command
# :Creato:   sab 10 apr 2004 16:43:48 CEST
# :Autore:   Lele Gaifax <lele@nautilus.homeip.net>
# :Licenza:  GNU General Public License
#

__docformat__ = 'reStructuredText'

try:
    # Python 2.4
    from subprocess import Popen, PIPE, STDOUT
except ImportError:
    # Older snakes
    from _process import Popen, PIPE, STDOUT
import logging

class ReopenableNamedTemporaryFile:
    """
    This uses tempfile.mkstemp() to generate a secure temp file.  It
    then closes the file, leaving a zero-length file as a placeholder.
    You can get the filename with ReopenableNamedTemporaryFile.name.
    When the ReopenableNamedTemporaryFile instance is garbage
    collected or its shutdown() method is called, it deletes the file.

    Copied from Zooko's pyutil.fileutil, http://zooko.com/repos/pyutil
    """
    def __init__(self, suffix=None, prefix=None, dir=None, text=None):
        from tempfile import mkstemp
        from os import close

        fd, self.name = mkstemp(suffix, prefix, dir, text)
        close(fd)

    def __del__(self):
        self.shutdown()

    def shutdown(self):
        from os import remove

        remove(self.name)


class ExternalCommand:
    """Wrap a single command to be executed by the shell."""

    VERBOSE = True
    """Print the executed command on stderr, at each run."""

    DEBUG = False
    """Print the output of the command, when not PIPEd to the caller."""

    DRY_RUN = False
    """Don't really execute the command."""

    FORCE_ENCODING = None
    """Force the output encoding to some other charset instead of user prefs."""

    def __init__(self, command=None, cwd=None):
        """Initialize a ExternalCommand instance, specifying the command
           to be executed and eventually the working directory."""

        self.command = command
        """The command to be executed."""

        self.cwd = cwd
        """The working directory, go there before execution."""

        self.exit_status = None
        """Once the command has been executed, this is its exit status."""

        self._last_command = None
        """Last executed command."""

        self.log = logging.getLogger('tailor.shell')

    def __str__(self):
        result = []
        if self.cwd:
            result.append(self.cwd)
            result.append(' ')
        result.append('$')
        needquote = False
        for arg in self._last_command or self.command:
            bs_buf = []

            # Add a space to separate this argument from the others
            result.append(' ')

            needquote = (" " in arg) or ("\t" in arg)
            if needquote:
                result.append('"')

            for c in arg:
                if c == '\\':
                    # Don't know if we need to double yet.
                    bs_buf.append(c)
                elif c == '"':
                    # Double backspaces.
                    result.append('\\' * len(bs_buf)*2)
                    bs_buf = []
                    result.append('\\"')
                else:
                    # Normal char
                    if bs_buf:
                        result.extend(bs_buf)
                        bs_buf = []
                    result.append(c)

            # Add remaining backspaces, if any.
            if bs_buf:
                result.extend(bs_buf)

            if needquote:
                result.extend(bs_buf)
                result.append('"')

        return ''.join(result)

    def execute(self, *args, **kwargs):
        """Execute the command."""

        from sys import stderr
        from locale import getpreferredencoding
        import os
        from cStringIO import StringIO

        self.exit_status = None

        self._last_command = [chunk % kwargs for chunk in self.command]
        if len(args) == 1 and type(args[0]) == type([]):
            self._last_command.extend(args[0])
        else:
            self._last_command.extend(args)

        self.log.info(self)

        if self.DRY_RUN:
            return

        if not kwargs.has_key('cwd') and self.cwd:
            kwargs['cwd'] = self.cwd

        if not kwargs.has_key('env'):
            env = kwargs['env'] = {}
            env.update(os.environ)

            for v in ['LANG', 'TZ', 'PATH']:
                if kwargs.has_key(v):
                    env[v] = kwargs[v]

        input = kwargs.get('input')
        output = kwargs.get('stdout')
        error = kwargs.get('stderr')

        # When not in debug, redirect stderr and stdout to /dev/null
        # when the caller didn't ask for them.
        if not self.DEBUG:
            devnull = getattr(os, 'devnull', '/dev/null')
            if output is None:
                output = open(devnull, 'w')
            if error is None:
                error = open(devnull, 'w')
        try:
            process = Popen(self._last_command,
                            stdin=input and PIPE or None,
                            stdout=output,
                            stderr=error,
                            env=kwargs.get('env'),
                            cwd=kwargs.get('cwd'),
                            universal_newlines=True)
        except OSError, e:
            from errno import ENOENT

            if e.errno == ENOENT:
                raise OSError("'%s' does not exist!" % self._last_command[0])
            else:
                raise

        if input and isinstance(input, unicode):
            input = input.encode(self.FORCE_ENCODING or getpreferredencoding())

        out, err = process.communicate(input=input)

        self.exit_status = process.returncode
        if not self.exit_status:
            self.log.info("[Ok]")
        else:
            self.log.warning("[Status %s]", self.exit_status)

        # For debug purposes, copy the output to our stderr when hidden above
        if self.DEBUG:
            if out and output == PIPE:
                stderr.write('Output stream:\n')
                stderr.write(out)
            if err and error == PIPE:
                stderr.write('Error stream:\n')
                stderr.write(err)

        if out is not None:
            out = StringIO(out)
        if err is not None:
            err = StringIO(err)

        return out, err
