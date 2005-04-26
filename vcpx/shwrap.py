#  -*- Python -*- -*- coding: iso-8859-1 -*-
# :Progetto: vcpx -- Tiny wrapper around external command
# :Creato:   sab 10 apr 2004 16:43:48 CEST
# :Autore:   Lele Gaifax <lele@nautilus.homeip.net>
# 

__docformat__ = 'reStructuredText'

from StringIO import StringIO
from sys import stderr
import threading

def shrepr(str):
    str = str.replace("'", "\\'")
    return "'" + str + "'"


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
        
        self.name = mkstemp(suffix, prefix, dir, text)[1]
      
    def __del__(self):
        self.shutdown()
       
    def shutdown(self):
        from os import remove
        
        remove(self.name)


class VerboseStringIO(StringIO):

    def write(self, data):        
        """Give a feedback to the user."""
        
        StringIO.write(self, data)
        stderr.write('.'*data.count('\n'))

def joinall(threadlist):
    for t in threadlist:
        t.join()

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
        threadlist = []
        
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
                def handleinp():
                    inp.write(input)
                    inp.close()
                inpthread = threading.Thread(target = handleinp)
                inpthread.start()
                threadlist.append(inpthread)
            else:
                out = popen(command)

            def handleout():
                copyfileobj(out, output, length=128)
                output.seek(0)
            outthread = threading.Thread(target = handleout)
            outthread.start()
            threadlist.append(outthread)

            joinall(threadlist)

            if input:
                self.exit_status = wait()[1]
                out.close()
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

