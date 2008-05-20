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

    DEBUG = False
    """Print the output of the command, when not PIPEd to the caller."""

    DRY_RUN = False
    """Don't really execute the command."""

    MAX_CMDLINE_LENGTH = 8000
    """Don't execute commands longer than this number of characters."""

    def __init__(self, command=None, cwd=None, nolog=False, ok_status=None):
        """
        Initialize a ExternalCommand instance, specifying the command
        to be executed and eventually the working directory.

        The instance will use the logger ``tailor.shell``.
        """

        from logging import getLogger

        self.command = command
        """The command to be executed."""

        self.cwd = cwd
        """The working directory, go there before execution."""

        self.exit_status = None
        """Once the command has been executed, this is its exit status."""

        self.ok_status = ok_status is None and (0,) or ok_status
        """Used to determine which exit_status should not trigger warnings."""

        self._last_command = None
        """Last executed command."""

        self.capture_stderr = False

        if nolog:
            self.log = False
        else:
            self.log = getLogger('tailor.shell')

    def __str__(self):
        """
        Return a string representation of the command prefixed by working dir.
        """

        r = '$'+repr(self)
        if self.cwd:
            r = self.cwd + ' ' + r
        if self.capture_stderr:
            r = r + ' 2>&1'
        return r

    def __repr__(self):
        """
        Compute a reasonable shell-like representation of the external command.
        """

        result = []
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
        """Execute the command, avoiding too long command line."""

        from cStringIO import StringIO

        if kwargs.get('stderr'):
            self.capture_stderr = True
        else:
            self.capture_stderr = False

        if len(args) == 1 and type(args[0]) == type([]):
            allargs = list(args[0])
        else:
            allargs = list(args)

        maxlen = self.MAX_CMDLINE_LENGTH
        if maxlen is None or len(allargs) < 2:
            return self._execute(allargs, **kwargs)

        startlen = len(' '.join(self.command))
        allout = None
        allerr = None
        while allargs:
            thisrun = []
            clen = startlen
            pop = allargs.pop
            append = thisrun.append
            while allargs and clen<maxlen:
                thisarg = pop(0)
                clen += len(thisarg)+1
                append(thisarg)
            thisout, thiserr = self._execute(*thisrun, **kwargs)
            if thisout is not None:
                if allout is None:
                    allout = StringIO()
                allout.write(thisout.read())
            if thiserr is not None:
                if allerr is None:
                    allerr = StringIO()
                allerr.write(thiserr.read())
            if self.exit_status:
                break
        if allout is not None:
            allout.seek(0)
        if allerr is not None:
            allerr.seek(0)
        return allout, allerr

    def _execute(self, *args, **kwargs):
        """Execute the command."""

        from sys import stderr
        from locale import getpreferredencoding
        from os import environ, getcwd
        from os.path import isdir
        from cStringIO import StringIO
        from errno import ENOENT

        self.exit_status = None

        self._last_command = [chunk % kwargs for chunk in self.command]
        if len(args) == 1 and type(args[0]) == type([]):
            self._last_command.extend(args[0])
        else:
            self._last_command.extend(args)

        if self.log: self.log.info(self)

        if self.DRY_RUN:
            return

        cwd = kwargs.setdefault('cwd', self.cwd or getcwd())
        if not isdir(cwd):
            raise OSError(ENOENT, "Working directory does not exist", cwd)

        if self.log: self.log.debug("Executing %r (%r)", self, cwd)

        if not kwargs.has_key('env'):
            env = kwargs['env'] = {}
            env.update(environ)

            for v in ['LANG', 'TZ', 'PATH']:
                if kwargs.has_key(v):
                    env[v] = kwargs[v]
            # Override also LC_ALL that has a higher priority over LANG,
            # and LC_MESSAGES as well.
            if kwargs.has_key('LANG'):
                env['LC_ALL'] = kwargs['LANG']
                env['LC_MESSAGES'] = kwargs['LANG']

        input = kwargs.get('input')
        output = kwargs.get('stdout')
        error = kwargs.get('stderr')

        # When not in debug, redirect stderr and stdout to /dev/null
        # when the caller didn't ask for them.
        if not self.DEBUG:
            try:
                from os import devnull
            except ImportError:
                devnull = '/dev/null'
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
                            cwd=cwd,
                            universal_newlines=True)
        except OSError, e:
            if e.errno == ENOENT:
                raise OSError("%r does not exist!" % self._last_command[0])
            else:
                raise

        if input and isinstance(input, unicode):
            encoding = getpreferredencoding()
            if self.log:
                self.log.warning("Using default %s encoding, ignoring errors; "
                                 "caller should use repository's encoding and "
                                 "pass an already encoded input" % encoding)
            input = input.encode(encoding, 'ignore')

        out, err = process.communicate(input=input)

        self.exit_status = process.returncode
        if self.exit_status in self.ok_status:
            if self.log: self.log.info("[Ok]")
        else:
            if self.log: self.log.warning("[Status %s]", self.exit_status)

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
