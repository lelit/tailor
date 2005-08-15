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

        from sys import stderr, getdefaultencoding
        from os import environ
        from cStringIO import StringIO

        self.exit_status = None

        self._last_command = [chunk % kwargs for chunk in self.command]
        if len(args) == 1 and type(args[0]) == type([]):
            self._last_command.extend(args[0])
        else:
            self._last_command.extend(args)

        if self.VERBOSE:
            stderr.write(str(self))

        if self.DRY_RUN:
            return

        if not kwargs.has_key('cwd') and self.cwd:
            kwargs['cwd'] = self.cwd

        if not kwargs.has_key('env'):
            env = kwargs['env'] = {}
            env.update(environ)

            for v in ['LANG', 'TZ', 'PATH']:
                if kwargs.has_key(v):
                    env[v] = kwargs[v]

        input = kwargs.get('input')

        try:
            process = Popen(self._last_command,
                            stdin=input and PIPE or None,
                            stdout=kwargs.get('stdout'),
                            stderr=kwargs.get('stderr'),
                            env=kwargs.get('env'),
                            cwd=kwargs.get('cwd'),
                            universal_newlines=True)
        except OSError:
            stderr.write("'%s' does not exist!" % self._last_command[0])
            self.exit_status = -1
            return

        if input:
            input = input.encode(self.FORCE_ENCODING or getdefaultencoding())

        out = process.communicate(input=input)[0]
        if out:
            out = StringIO(out)
        self.exit_status = process.returncode

        if self.VERBOSE:
            if not self.exit_status:
                stderr.write(" [Ok]\n")
            else:
                stderr.write(" [Status %s]\n" % self.exit_status)

        return out
