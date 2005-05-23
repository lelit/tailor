#! /usr/bin/python
# -*- mode: python; coding: utf-8 -*-
# :Progetto: vcpx -- Interactive session
# :Creato:   ven 13 mag 2005 02:00:57 CEST
# :Autore:   Lele Gaifax <lele@nautilus.homeip.net>
# :Licenza:  GNU General Public License
# 

"""
Tailor interactive session.

This module implements an alternative approach at driving the various
steps tipically performed by tailor, using an interaction with the user
instead of pushing options madness on him.
"""

__docformat__ = 'reStructuredText'

from cmd import Cmd
from os import chdir, getcwd       


INTRO = """\
Welcome to the Tailor interactive session: you can issue several commands
with the usual `readline` facilities. With "help" you'll get a list of
available commands.
"""


class Session(Cmd):
    """Tailor interactive session."""
    
    prompt = "tailor $ "
    
    def __init__(self, options, args):
        """
        Initialize a new interactive session.

        Set the default values, and override them with option settings,
        then slurp in each command line argument that should contain
        a list of commands to be executed.
        """
        
        Cmd.__init__(self)
        self.options = options        
        self.args = args
        
        self.source_repository = options.repository
        self.source_kind = options.source_kind
        self.source_module = options.module
        self.target_repository = None
        self.target_kind = options.target_kind
        self.target_module = None
        self.current_directory = getcwd()
        self.sub_directory = None
        
        self.state_file = 'tailor.state'
        
        self.changesets = None
        self.logfile = None
        self.logger = None
        
        self.__processArgs()

    def __processArgs(self):
        """
        Process optional command line arguments.

        Each argument is assumed to contain a list of tailor commands
        to execute in order.
        """

        for arg in self.args:
            self.cmdqueue.extend(file(arg).readlines())

    def __log(self, what):
        if self.logger:
            self.logger.info(what)
            
        if self.options.verbose:
            self.stdout.write(what)

    def __err(self, what):
        if self.logger:
            self.logger.error(what)
            
        self.stdout.write('Error: ')
        self.stdout.write(what)
        

    ## Interactive commands

    def emptyline(self):
        """Override the default impl of reexecuting last command."""
        pass
        
    def do_exit(self, arg):
        """Exit the interactive session."""

        self.__log('Exiting...\n')
        return True

    def do_EOF(self, arg):
        """Exit the interactive session."""
        
        return self.do_exit(arg)

    def do_save(self, arg):
        """Save the commands history on the specified file."""

        import readline

        if not arg:
            return
            
        readline.write_history_file(arg)
        self.__log('History saved in: %s\n' % arg)
        
    def do_cd(self, arg):
        """Print or set current active directory."""

        if arg and self.current_directory <> arg:
            try:
                chdir(arg)
                self.current_directory = getcwd()
            except:
                self.__log('Cannot change current directory to %s\n' %
                           arg)
        self.__log('Current directory: %s\n' % self.current_directory)

    do_current_directory = do_cd

    def do_sub_directory(self, arg):
        """
        Print or set the subdirectory that actually contains the working copy.

        This is desumed automatically to be the last component of
        the upstream module or repository.
        """
        
        if arg and self.sub_directory <> arg:
            self.sub_directory = arg

        self.__log('Sub directory: %s\n' % self.sub_directory)

    def do_logfile(self, arg):
        """Print or set the logfile of operations."""

        import logging
        
        if arg:
            self.logfile = arg
            self.logger = logging.getLogger('tailor')
            hdlr = logging.FileHandler(self.logfile)
            formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(message)s')
            hdlr.setFormatter(formatter)
            self.logger.addHandler(hdlr) 
            self.logger.setLevel(logging.INFO)
            
        self.__log('Logging to: %s\n' % self.logfile)

    def do_source_kind(self, arg):
        """Print or set the source repository kind."""

        if arg and self.source_kind <> arg:
            self.source_kind = arg

        self.__log('Current source kind: %s\n' % self.source_kind)
        
    def do_target_kind(self, arg):
        """Print or set the target repository kind."""

        if arg and self.target_kind <> arg:
            self.target_kind = arg

        self.__log('Current target kind: %s\n' % self.target_kind)

    def do_source_repository(self, arg):
        """Print or set the source repository."""

        from os.path import sep
        
        if arg and self.source_repository <> arg:
            if arg.endswith(sep):
                arg = arg[:-1]
            self.source_repository = arg

        self.__log('Current source repository: %s\n' % self.source_repository)

    def do_target_repository(self, arg):
        """Print or set the target repository."""

        from os.path import sep
        
        if arg and self.target_repository <> arg:
            if arg.endswith(sep):
                arg = arg[:-1]
            self.target_repository = arg

        self.__log('Current target repository: %s\n' % self.target_repository)

    def do_source_module(self, arg):
        """Print or set the source module."""

        from os.path import sep
        
        if arg and self.source_module <> arg:
            if arg.endswith(sep):
                arg = arg[:-1]
            self.source_module = arg

        self.__log('Current target kind: %s\n' % self.source_module)

    def do_target_module(self, arg):
        """Print or set the target module."""

        from os.path import sep
        
        if arg and self.target_module <> arg:
            if arg.endswith(sep):
                arg = arg[:-1]
            self.target_module = arg

        self.__log('Current target kind: %s\n' % self.target_module)

    def readSourceRevision(self):
        """Read the source revision from the state file."""

        try:
            sf = open(self.state_file)
            revision = sf.read()
            sf.close()
        except IOError:
            revision = None

        return revision
            
    def saveSourceRevision(self, revision):
        """Write current source revision in the state file."""

        sf = open(self.state_file, 'w')
        sf.write(revision)
        sf.close()
        
    def do_state_file(self, arg):
        """
        Print or set the current state_file.

        The argument must be a file name, possibly with the usual
        "~user/file" convention.        
        """

        from os.path import isabs, abspath, expanduser

        if arg:
            arg = expanduser(arg)
            if not isabs(arg):
                arg = abspath(arg)
        
        if arg and self.state_file <> arg:
            self.state_file = arg
                
        self.__log('Current state file: %s\n' % self.state_file)

    def do_get_changes(self, arg):
        """Fetch information on upstream changes."""

        source_revision = self.readSourceRevision()
        if self.source_kind and \
           self.source_repository and \
           self.source_module and \
           source_revision:

            dwd = DualWorkingDir(self.source_kind, self.target_kind)
            self.changesets = dwd.getUpstreamChangesets(self.current_directory,
                                                        self.source_repository,
                                                        self.source_module,
                                                        source_revision)
            self.__log('Collected %d upstream changesets\n' %
                       len(self.changesets))
        else:
            self.__err("needs 'source_kind', 'source_repository' and "
                       "'source_module' to proceed.\n")

    def do_show_changes(self, arg):
        """Show the upstream changes not yet applied."""

        if self.changesets:
            self.__log(`self.changesets`)
            self.__log('\n')
        else:
            self.__err("needs `get_changes` to proceed.\n")

    def do_bootstrap(self, arg):
        """
        Checkout the initial upstream revision, by default HEAD (or
        specified by argument), then import the subtree into the
        target repository.
        """
        
        from os.path import join, split, sep
        from dualwd import DualWorkingDir

        if self.sub_directory:
            subdir = self.sub_directory
        else:
            subdir = split(self.source_module or self.source_repository)[1] or ''
            self.do_sub_directory(subdir)

        revision = arg or self.options.revision or 'HEAD'
        
        dwd = DualWorkingDir(self.source_kind, self.target_kind)
        self.__log("Getting %s revision '%s' of '%s' from '%s'\n" % (
            self.source_kind, revision,
            self.source_module, self.source_repository))

        try:
            actual = dwd.checkoutUpstreamRevision(self.current_directory,
                                                  self.source_repository,
                                                  self.source_module,
                                                  revision,
                                                  subdir=subdir,
                                                  logger=self.logger)
            self.saveSourceRevision(actual)
        except Exception, exc:
            self.__err('Checkout failed: %s, %s' % (exc.__doc__, exc))
            if self.logger:
                self.logger.exception('Checkout failed')

        try:
            dwd.initializeNewWorkingDir(self.current_directory,
                                        self.target_repository,
                                        self.target_module,
                                        self.sub_directory,
                                        actual)
        except:
            self.__err('Working copy initialization failed: %s, %s' % (exc.__doc__, exc))
            if self.logger:
                self.logger.exception('Working copy initialization failed')

        
def interactive(options, args):
    session = Session(options, args)
    session.cmdloop(options.verbose and INTRO or "")
