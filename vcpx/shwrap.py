#  -*- Python -*- -*- coding: iso-8859-1 -*-
# :Progetto: vcpx -- Tiny wrapper around external command
# :Creato:   sab 10 apr 2004 16:43:48 CEST
# :Autore:   Lele Gaifax <lele@nautilus.homeip.net>
# 

__docformat__ = 'reStructuredText'

from StringIO import StringIO
from sys import stderr

class VerboseStringIO(StringIO):

    def write(self, data):        
        """Give a feedback to the user."""
        
        StringIO.write(self, data)
        stderr.write('.'*data.count('\n'))


class SystemCommand(object):
    """Wrap a single command to be executed by the shell."""

    COMMAND = None
    """The default command for this class.  Must be redefined by subclasses."""

    VERBOSE = True
    """Print the executed command on stderr, at each run."""
    
    def __init__(self, command=None, working_dir=None):
        """Initialize a SystemCommand instance, specifying the command
           to be executed and eventually the working directory."""
        
        self.command = command or self.COMMAND
        """The command to be executed."""
        
        self.working_dir = working_dir
        """The working directory, go there before execution."""
        
        self.exit_status = None
        """Once the command has been executed, this is its exit status."""
        
    def __call__(self, output=None, input=None, dry_run=False, **kwargs):
        """Execute the command."""
        
        from os import system, popen, popen2, wait, chdir
        from shutil import copyfileobj
        
        wdir = self.working_dir or kwargs.get('working_dir')
        if wdir:
            chdir(wdir)

        command = self.command % kwargs
        if self.VERBOSE:
            stderr.write("%s " % command)

        if dry_run:
            if self.VERBOSE:
                stderr.write(" [dry run]\n")
            return
        
        if output:
            if output is True:
                if self.VERBOSE:
                    output = VerboseStringIO()
                else:
                    output = StringIO()

            if input:
                inp, out = popen2(command)
                inp.write(input)
                inp.close()
            else:
                out = popen(command)

            copyfileobj(out, output, length=128)
            output.seek(0)

            if input:
                self.exit_status = wait()[1]
            else:
                self.exit_status = out.close() or 0
        else:
            if input:
                inp, out = popen2(command)
                inp.write(input)
                inp.close()
                out.close()
                self.exit_status = wait()[1]
            else:
                self.exit_status = system(command)            
                    
        if self.VERBOSE:
            if not self.exit_status:
                stderr.write(" [Ok]\n")
            else:
                stderr.write(" [Error %s]\n" % self.exit_status)
                
        return output

