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


INTRO = """\
Welcome to the Tailor interactive session: you can issue several commands
with the usual `readline` facilities. With "help" you'll get a list of
available commands.
"""

def yesno(arg):
    "Return True for '1', 'true' or 'yes', False otherwise."

    try:
        return bool(int(arg))
    except ValueError:
        return arg.lower() in ('true', 'yes')
    
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
        
        from os import getcwd       

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
        
        self.state_file = None
        self.logfile = None
        self.logger = None
        
        self.__processArgs()

        # Persistent
        
        self.changesets = None
        self.source_revision = None
        
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
            self.stdout.write('\n')

    def __err(self, what, exc=False):
        if self.logger:
            if exc:
                self.logger.exception(what)
            else:
                self.logger.error(what)
            
            
        self.stdout.write('Error: ')
        self.stdout.write(what)
        if exc:
            from sys import exc_info

            ei = exc_info()
            self.stdout.write(' -- Exception %s: %s' % ei[0:2])
        self.stdout.write('\n')

    def emptyline(self):
        """Override the default impl of reexecuting last command."""
        pass

    def precmd(self, line):
        """Strip anything after the first '#', to allow comments."""

        try:
            line = line[:line.index('#')]
        except ValueError:
            pass

        return line
        
    ## Interactive commands

    def do_exit(self, arg):
        """
        Usage: exit

        Terminate the interactive session. This is the same thing
        happening upon EOF (Ctrl-D).
        """

        self.__log('Exiting...')
        return True

    do_EOF = do_exit

    def do_save(self, arg):
        """
        Usage: save filename

        Save the commands history on the specified file.
        """

        import readline

        if not arg:
            return
            
        readline.write_history_file(arg)
        self.__log('History saved in: %s' % arg)
        
    def do_cd(self, arg):
        """
        Usage: cd [dirname]

        Print or set current active directory. If the directory does not
        exist it is created.
        """

        from os import chdir, makedirs, getcwd
        from os.path import isabs, abspath, expanduser
        
        if arg:
            arg = expanduser(arg)
            if not isabs(arg):
                arg = abspath(arg)

        if arg and self.current_directory <> arg:
            try:
                chdir(arg)
            except OSError:
                self.__log('Creating directory %s' % arg)
                try:
                    makedirs(arg)
                    chdir(arg)
                except:
                    self.__err("Cannot create directory '%s'" % arg, True)
                    return
                
            self.current_directory = getcwd()
            
        self.__log('Current directory: %s' % self.current_directory)

    do_current_directory = do_cd

    def do_sub_directory(self, arg):
        """
        Usage: sub_directory dirname
        
        Print or set the subdirectory that actually contains the
        working copy. When not explicitly set, this is desumed from
        the last component of the upstream module name or repository.
        """
        
        if arg and self.sub_directory <> arg:
            self.sub_directory = arg

        self.__log('Sub directory: %s' % self.sub_directory)

    def do_logfile(self, arg):
        """
        Usage: logfile [filename]
        
        Print or set the logfile of operations. By default there's no log.
        """

        import logging
        
        if arg:
            self.logfile = arg
            self.logger = logging.getLogger('tailor')
            hdlr = logging.FileHandler(self.logfile)
            formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(message)s')
            hdlr.setFormatter(formatter)
            self.logger.addHandler(hdlr) 
            self.logger.setLevel(logging.INFO)
            
        self.__log('Logging to: %s' % self.logfile)

    def do_print_executed_commands(self, arg):
        """
        Usage: print_executed_commands [0|1]

        Print or set the verbosity on external commands execution.
        """

        from shwrap import ExternalCommand
        
        if arg:
            ExternalCommand.VERBOSE = yesno(arg)

        self.__log('Print executed commands: %s' % ExternalCommand.VERBOSE)

    def do_force_output_encoding(self, arg):
        """
        Usage: force_output_encoding [charset]

        Print or set the current output encoding. When given, charset must
        be either the string "None" or a recognized Python charset name.
        In the former case (the default), tailor will use the current
        settings from the user environment.
        """

        from shwrap import ExternalCommand
        
        if arg:
            if arg == 'None':
                ExternalCommand.FORCE_ENCODING = None
            else:
                ExternalCommand.FORCE_ENCODING = arg

        self.__log('Forced output encoding: %s' % ExternalCommand.FORCE_ENCODING)

    def do_patch_name_format(self, arg):
        """
        Usage: patch_name_format [format]

        Print or set the patch name format, ie the prototype that will
        be used to compute the patch name.

        The prototype may contain %(keyword)s such as 'module',
        'author', 'date', 'revision', 'firstlogline', 'remaininglog'
        for normal updates, otherwise 'module', 'authors',
        'nchangesets', 'mindate' and 'maxdate'.
        """

        from target import SyncronizableTargetWorkingDir

        if arg:
            SyncronizableTargetWorkingDir.PATCH_NAME_FORMAT = arg

        self.__log('Patch name format: %s' %
                   SyncronizableTargetWorkingDir.PATCH_NAME_FORMAT)
        
    def do_remove_first_log_line(self, arg):
        """
        Usage: remove_first_log_line [0|1]
        
        Print or set if tailor should drop the first line of the
        upstream changelog.

        This is intended to go in pair with patch_name_format, when
        using it's 'firstlogline' variable to build the name of the
        patch.
        """

        from target import SyncronizableTargetWorkingDir

        if arg:
            SyncronizableTargetWorkingDir.REMOVE_FIRST_LOG_LINE = yesno(arg)

        self.__log('Remove first log line: %s' %
                   SyncronizableTargetWorkingDir.REMOVE_FIRST_LOG_LINE)

    def do_refill_changelogs(self, arg):
        """
        Usage: refill_changelogs [0|1]

        Print or set if tailor should refill the upstream changelogs,
        as it does by default.
        """

        from changes import Changeset
        
        if arg:
            Changeset.REFILL_MESSAGE = yesno(arg)

        self.__log('Refill changelogs: %s' % Changeset.REFILL_MESSAGE)
        
    def do_source_kind(self, arg):
        """
        Usage: source_kind [svn|darcs|cvs]

        Print or set the source repository kind.
        """

        if arg and self.source_kind <> arg:
            self.source_kind = arg

        self.__log('Current source kind: %s' % self.source_kind)
        
    def do_target_kind(self, arg):
        """
        Usage: target_kind [svn|darcs|cvs|monotone|cdv|bzr]

        Print or set the target repository kind.
        """

        if arg and self.target_kind <> arg:
            self.target_kind = arg

        self.__log('Current target kind: %s' % self.target_kind)

    def do_source_repository(self, arg):
        """
        Usage: source_repository [repos]

        Print or set the source repository.
        """

        from os.path import sep
        
        if arg and self.source_repository <> arg:
            if arg.endswith(sep):
                arg = arg[:-1]
            self.source_repository = arg

        self.__log('Current source repository: %s' % self.source_repository)

    def do_target_repository(self, arg):
        """
        Usage: target_repository [repos]

        Print or set the target repository. This is currently unused.
        """

        from os.path import sep
        
        if arg and self.target_repository <> arg:
            if arg.endswith(sep):
                arg = arg[:-1]
            self.target_repository = arg

        self.__log('Current target repository: %s' % self.target_repository)

    def do_source_module(self, arg):
        """
        Usage: source_module [module]
        
        Print or set the source module.
        """

        from os.path import sep
        
        if arg and self.source_module <> arg:
            if arg.endswith(sep):
                arg = arg[:-1]
            self.source_module = arg

        self.__log('Current source module: %s' % self.source_module)

    def do_target_module(self, arg):
        """
        Usage: target_module [module]

        Print or set the target module. This is currently not used.
        """

        from os.path import sep
        
        if arg and self.target_module <> arg:
            if arg.endswith(sep):
                arg = arg[:-1]
            self.target_module = arg

        self.__log('Current target module: %s' % self.target_module)

    def loadStateFile(self):
        """
        Read the source revision and pending changesets from the state file.
        """

        from cPickle import load

        try:
            sf = open(self.state_file)
            self.source_revision, self.changesets = load(sf)
            sf.close()

            self.__log('Source revision: %s' % self.source_revision)
            if self.changesets:
                self.__log('Pending changesets: %d' % len(self.changesets))
        except IOError:
            self.source_revision = None
            self.changesets = None

    def writeStateFile(self):
        """
        Write current source revision and pending changesets in the state file.
        """

        from cPickle import dump
        
        sf = open(self.state_file, 'w')
        dump((self.source_revision, self.changesets), sf)
        sf.close()

    def do_state_file(self, arg):
        """
        Usage: state_file [filename]
        
        Print or set the current state file, where tailor stores the
        source revision that has been applied last.
        
        The argument must be a file name, possibly with the usual
        "~user/file" convention.        
        """

        from os.path import isabs, abspath, expanduser
        from cPickle import load
        
        if arg:
            arg = expanduser(arg)
            if not isabs(arg):
                arg = abspath(arg)
        
        if arg and self.state_file <> arg:
            self.state_file = arg
            
        self.__log('Current state file: %s' % self.state_file)

        if not self.state_file:
            self.__err('Need a state_file to proceed to load state file!')
            return

        try:
            self.loadStateFile()
        except:
            self.__err("'%s' is not a valid state file" % self.state_file,
                       True)
            self.state_file = None
            return

    def do_bootstrap(self, arg):
        """
        Usage: bootstrap [revision]
        
        Checkout the initial upstream revision, by default HEAD (or
        specified by argument), then import the subtree into the
        target repository.
        """
        
        from os.path import join, split, sep
        from dualwd import DualWorkingDir

        if not self.state_file:
            self.__err('Need a state_file to proceed!')
            return

        if self.source_revision is not None:
            self.__err('Already bootstrapped!')
            
        if self.sub_directory:
            subdir = self.sub_directory
        else:
            subdir = split(self.source_module or
                           self.source_repository)[1] or ''
            self.do_sub_directory(subdir)

        revision = arg or self.options.revision or 'HEAD'

        dwd = DualWorkingDir(self.source_kind, self.target_kind)
        self.__log("Getting %s revision '%s' of '%s' from '%s'" % (
            self.source_kind, revision,
            self.source_module, self.source_repository))

        try:
            self.source_revision = dwd.checkoutUpstreamRevision(
                self.current_directory, self.source_repository,
                self.source_module, revision,
                subdir=subdir, logger=self.logger)
        except:
            self.__err('Checkout failed', True)
            return
        
        self.writeStateFile()
        
        try:
            dwd.initializeNewWorkingDir(self.current_directory,
                                        self.source_repository,
                                        self.source_module,
                                        self.sub_directory,
                                        self.source_revision)
        except:
            self.__err('Working copy initialization failed', True)
            return
        
    def willApply(self, root, changeset):
        """
        Print the changeset being applied.
        """

        try:
            self.__log("Changeset %s:\n%s" % (changeset.revision,
                                              changeset.log))
        except UnicodeEncodeError:
            self.__log("Changeset %s:\n%s" % (changeset.revision,
                                              ">>Non-printable changelog<<"))
        return True

    def shouldApply(self, root, changeset):
        """
        Ask weather a changeset should be applied.
        """

        self.stdout.write("\nChangeset %s:\n%s" % (changeset.revision,
                                                     changeset.log))

        while 1:
            self.stdout.write('\n')
            ans = raw_input("Apply [Y/n/v/h/q]? ")
            ans = ans=='' and 'y' or ans[0].lower()

            if ans == 'y':
                return True
            elif ans == 'n':
                return False
            elif ans == 'h':
                self.stdout.write('y: yes, apply it and keep going\n'
                                  'n: no, skip the current changeset\n'
                                  'v: view more detailed information\n'
                                  'q: do not apply the current changeset '
                                  'and stop iterating\n')
            elif ans == 'q':
                raise StopIteration()
            else:
                self.stdout.write(str(changeset) + '\n')

    def applied(self, root, changeset):
        """
        Save current status.
        """

        self.source_revision = changeset.revision
        self.changesets.remove(changeset)

    def do_update(self, arg):
        """
        Usage: update [arg]

        Fetch information on upstream changes and replay them with the
        target system.

        Argument may be either an integer value or the string 'ask'. The
        number specify the maximum number of changesets that will be
        applied. With 'ask' tailor will propose a "y/n" question for each
        changeset before applying it.
        """

        from dualwd import DualWorkingDir
        from os.path import join, split
        from source import GetUpstreamChangesetsFailure

        if not self.state_file:
            self.__err('Need a state_file to proceed!')
            return
                
        if self.source_revision is None:
            self.__log('Boostrapping, because source_revision is None!')
            return self.do_bootstrap(None)
        
        if self.sub_directory:
            subdir = self.sub_directory
        else:
            if not self.source_module:
                self.__err('Need a source_module to proceed!')
                return
            subdir = split(self.source_module or
                           self.source_repository)[1] or ''
            self.do_sub_directory(subdir)
            
        repodir = join(self.current_directory, subdir)
        dwd = DualWorkingDir(self.source_kind, self.target_kind)

        # If we have no pending changesets, ask the upstream server
        # about new changes
        
        if not self.changesets:
            try:
                self.changesets = dwd.getUpstreamChangesets(
                                           repodir,
                                           self.source_repository,
                                           self.source_module,
                                           self.source_revision)
            except GetUpstreamChangesetsFailure, exc:
                self.__err('Unable to collect upstream changes from %s: %s' %
                           (self.source_repository, exc))
                return
            except:
                self.__err('Unable to collect upstream changes', True)
                return
            
        nchanges = len(self.changesets)
        if nchanges:
            applyable = self.willApply
            if arg:
                try:
                    howmany = min(int(arg), nchanges)
                    changesets = self.changesets[:howmany]
                except ValueError:
                    changesets = self.changesets[:]
                    if arg.lower() == 'ask':
                        applyable = self.shouldApply
            else:
                changesets = self.changesets[:]
                
            self.__log('Applying %d changesets (out of %d)' %
                       (len(changesets), nchanges))

            last = None
            try:
                try:
                    last, conflicts = dwd.applyUpstreamChangesets(
                        repodir, self.source_module, changesets,
                        applyable=applyable, applied=self.applied,
                        logger=self.logger) # , delayed_commit=single_commit)
                except StopIteration, KeyboardInterrupt:
                    if self.logger:
                        self.logger.warning("Stopped by user")
                except:
                    self.__err('Stopping after upstream change application '
                               'failure', True)
            finally:
                self.writeStateFile()
                
                if self.changesets:
                    self.__log("There are still %d pending changesets, "
                               "now at revision '%s'" %
                               (len(self.changesets), self.source_revision))
                else:
                    self.__log("Update completed, now at revision '%s'" %
                               self.source_revision)
        else:
            self.__log("Update completed with no upstream changes")

    def do_dopplebanger(self, arg):
        """
        Usage: dopplebanger patchname

        Given two repositories (in the actual implementation, the source
        must be a local darcs repository), do something similar to update
        but using diff and patch instead.
        """

        from os.path import isdir
        from dualwd import DualWorkingDir
        from darcs import DARCS_CMD, changesets_from_darcschanges
        from shwrap import ExternalCommand, PIPE
        
        if not (self.source_repository and self.target_repository and
                isdir(self.source_repository) and
                isdir(self.target_repository) and
                self.source_kind == 'darcs' and
                self.target_kind):
            self.__err('Both source and target repository must be under '
                       'darcs and on the local filesystem!')
            return

        if not arg:
            self.__err('Needs a patchname to proceed')
            return
        
        c = ExternalCommand(cwd=self.source_repository,
                            command=[DARCS_CMD, "changes", "--patches",
                                     arg, "--xml-output", "--summ"])
        last = changesets_from_darcschanges(c.execute(output=PIPE),
                                            unidiff=True,
                                            repodir=self.source_repository)
        
        if not last:
            self.__err('Specified patchname does not exist!')
            return
        
        cset = last[0]
        cset.applyPatch(working_dir=self.target_repository,
                        patch_options=["-p1", "--force"])
        
        dwd = DualWorkingDir(self.source_kind, self.target_kind)
        dwd.replayChangeset(self.target_repository, self.target_module, cset,
                            logger=self.logger)
        
def interactive(options, args):
    session = Session(options, args)
    session.cmdloop(options.verbose and INTRO or "")
