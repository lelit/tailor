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

Each session's data may persist in *state file*, that may be specified
either thru the ``state_file`` command::

  bash $ tailor --verbose --interactive
  Welcome to the Tailor interactive session: you can issue several commands
  with the usual `readline` facilities. With "help" you'll get a list of
  available commands.

  tailor $ state_file ~/tailored/someproj.state
  
or directly as the only non-option argument on the tailor's command line::

  bash $ tailor -vi ~/tailored/someproj.state

with the same meaning. The content of the file overrides the options.
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
    
    PERSIST_ATTRS = ('source_repository', 'source_kind', 'source_module',
                     'source_revision', 'target_repository',
                     'target_kind', 'target_module', 'current_directory',
                     'sub_directory')
    
    def __init__(self, options, args):
        Cmd.__init__(self)
        self.options = options        
        self.args = args
        
        self.source_repository = options.repository
        self.source_kind = options.source_kind
        self.source_module = options.module
        self.source_revision = None
        self.target_repository = None
        self.target_kind = options.target_kind
        self.target_module = None
        self.state_file = args and args[0] or None
        self.current_directory = getcwd()
        self.sub_directory = None
        
        self.changesets = None
        self.changed = False

        if self.state_file:
            self.__loadState()
            
    def __del__(self):
        if self.state_file and self.changed:
            self.__saveState()

    def __saveState(self):
        self.__log('Saving state file...\n')
        state = file(self.state_file, 'w')
        for attr in self.PERSIST_ATTRS:
            value = getattr(self, attr)
            if not value is None:
                state.write('%s=%s\n' % (attr, value))
        state.close()

    def __loadState(self):
        state = file(self.state_file, 'r')
        for line in state:
            attr, value = line[:-1].split('=',1)
            meth = getattr(self, 'do_' + attr)
            meth(value)
        state.close()
        
    def __log(self, what):
        if self.options.verbose:
            self.stdout.write(what)

    def __err(self, what):
        self.stdout.write('Error: ')
        self.stdout.write(what)
        

    ## Interactive commands

    def emptyline(self):
        for attr in self.PERSIST_ATTRS:
            print '%s=%s' % (attr, getattr(self, attr))
        
    def do_exit(self, arg):
        """Exit the interactive session."""

        self.__log('Exiting...\n')
        return True

    def do_EOF(self, arg):
        """Exit the interactive session."""
        
        return self.do_exit(arg)

    def do_save(self, arg):
        """Save the commands history."""

        import readline

        if not arg:
            arg = '/tmp/tailor.cmds'
            
        readline.write_history_file(arg)
        self.__log('History saved in: %s\n' % arg)
        
    def do_cd(self, arg):
        """Print or set current active directory."""

        if arg and self.current_directory <> arg:
            try:
                chdir(arg)
                self.current_directory = getcwd()
                self.changed = True
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
            self.sub_directory = getcwd()
            self.changed = True

        self.__log('Sub directory: %s\n' % self.sub_directory)
        
    def do_source_kind(self, arg):
        """Print or set the source repository kind."""

        if arg and self.source_kind <> arg:
            self.source_kind = arg
            self.changed = True

        self.__log('Current source kind: %s\n' % self.source_kind)
        
    def do_target_kind(self, arg):
        """Print or set the target repository kind."""

        if arg and self.target_kind <> arg:
            self.target_kind = arg
            self.changed = True

        self.__log('Current target kind: %s\n' % self.target_kind)

    def do_source_repository(self, arg):
        """Print or set the source repository."""

        from os.path import sep
        
        if arg and self.source_repository <> arg:
            if arg.endswith(sep):
                arg = arg[:-1]
            self.source_repository = arg
            self.changed = True

        self.__log('Current source repository: %s\n' % self.source_repository)

    def do_target_repository(self, arg):
        """Print or set the target repository."""

        from os.path import sep
        
        if arg and self.target_repository <> arg:
            if arg.endswith(sep):
                arg = arg[:-1]
            self.target_repository = arg
            self.changed = True

        self.__log('Current target repository: %s\n' % self.target_repository)

    def do_source_module(self, arg):
        """Print or set the source module."""

        from os.path import sep
        
        if arg and self.source_module <> arg:
            if arg.endswith(sep):
                arg = arg[:-1]
            self.source_module = arg
            self.changed = True

        self.__log('Current target kind: %s\n' % self.source_module)

    def do_target_module(self, arg):
        """Print or set the target module."""

        from os.path import sep
        
        if arg and self.target_module <> arg:
            if arg.endswith(sep):
                arg = arg[:-1]
            self.target_module = arg
            self.changed = True

        self.__log('Current target kind: %s\n' % self.target_module)

    def do_source_revision(self, arg):
        """Print or set the current source revision."""
        
        if arg and self.source_revision <> arg:
            self.source_revision = arg
            self.changed = True

        self.__log('Current source revision: %s\n' % self.source_revision)
        
    def do_state_file(self, arg):
        """
        Print or set the current state_file.

        When specified, this is used as the persistent storage for this
        session, automatically saved upon clean exit.

        The argument must be a file name, possibly with the usual
        "~user/file" convention.        
        """

        from os.path import exists, isabs, abspath, expanduser

        if arg:
            arg = expanduser(arg)
            if not isabs(arg):
                arg = abspath(arg)
        
        if arg and self.state_file <> arg:
            self.state_file = arg
            self.changed = True

        self.__log('Current state file: %s\n' % self.state_file)

        if exists(self.state_file):
            self.__loadState()
            
    def do_get_changes(self, arg):
        """Fetch information on upstream changes."""
        
        if self.source_kind and \
           self.source_repository and \
           self.source_module and \
           self.source_revision:

            dwd = DualWorkingDir(self.source_kind, self.target_kind)
            self.changesets = dwd.getUpstreamChangesets(self.current_directory,
                                                        self.source_repository,
                                                        self.source_module,
                                                        self.source_revision)
            self.__log('Collected %d upstream changesets\n' %
                       len(self.changesets))
        else:
            self.__err("needs 'source_kind', 'source_repository', "
                       "'source_module' and 'source_revision' to proceed.\n")

    def do_show_changes(self, arg):
        """Show the upstream changes not yet applied."""

        if self.changesets:
            self.__log(`self.changesets`)
            self.__log('\n')
        else:
            self.__err("needs `get_changes` to proceed.\n")
            
    def do_bootstrap(self, arg):
        """Bootstrap a new tailorized module."""

        from os.path import join, split, sep
        from dualwd import DualWorkingDir

        if self.sub_directory:
            subdir = self.sub_directory
        else:
            subdir = split(self.source_module or self.source_repository)[1] or ''
            self.do_sub_directory(subdir)
            
        self.__log("Bootstrapping '%s'\n" % join(self.current_directory, subdir))

        dwd = DualWorkingDir(self.source_kind, self.target_kind)
        self.__log("Getting %s revision '%s' of '%s' from '%s'\n" % (
            self.source_kind, self.source_revision,
            self.source_module, self.source_repository))

        try:
            actual = dwd.checkoutUpstreamRevision(self.current_directory,
                                                  self.source_repository,
                                                  self.source_module,
                                                  self.source_revision,
                                                  subdir=subdir)
        except:
            self.__err('Checkout failed!\n')
            raise
        
        try:
            dwd.initializeNewWorkingDir(self.current_directory,
                                        self.target_repository,
                                        self.target_module,
                                        subdir, actual)
        except:
            self.__err('Working copy initialization failed!\n')
            raise

        self.do_source_revision(actual)
        self.__log("Bootstrap completed")

        
def interactive(options, args):
    session = Session(options, args)
    session.cmdloop(options.verbose and INTRO or "")
