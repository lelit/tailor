# -*- mode: python; coding: utf-8 -*-
# :Progetto: vcpx -- Frontend capabilities
# :Creato:   dom 04 lug 2004 00:40:54 CEST
# :Autore:   Lele Gaifax <lele@nautilus.homeip.net>
# :Licenza:  GNU General Public License
#

"""
Implement the frontend functionalities.
"""

__docformat__ = 'reStructuredText'

__version__ = '0.9.35'

from logging import getLogger
from optparse import OptionParser, OptionGroup, Option
from vcpx import TailorBug, TailorException
from vcpx.config import Config, ConfigurationError
from vcpx.project import Project
from vcpx.source import GetUpstreamChangesetsFailure


class EmptySourceRepository(TailorException):
    "The source repository appears to be empty"


class Tailorizer(Project):
    """
    A Tailorizer has two main capabilities: its able to bootstrap a
    new Project, or brought it in sync with its current upstream
    revision.
    """

    def _applyable(self, changeset):
        """
        Print the changeset being applied.
        """

        if self.verbose:
            self.log.info('Changeset "%s"', changeset.revision)
            if changeset.log:
                self.log.info("Log message: %s", changeset.log)
        self.log.debug("Going to apply changeset:\n%s", str(changeset))
        return True

    def _applied(self, changeset):
        """
        Separate changesets with an empty line.
        """

        if self.verbose:
            self.log.info('-*'*30)

    def bootstrap(self):
        """
        Bootstrap a new tailorized module.

        First of all prepare the target system working directory such
        that it can host the upstream source tree. This is backend
        specific.

        Then extract a copy of the upstream repository and import its
        content into the target repository.
        """

        self.log.info('Bootstrapping "%s" in "%s"', self.name, self.rootdir)

        dwd = self.workingDir()
        try:
            dwd.prepareWorkingDirectory(self.source)
        except:
            self.log.critical('Cannot prepare working directory!', exc_info=True)
            raise

        revision = self.config.get(self.name, 'start-revision', 'INITIAL')
        try:
            actual = dwd.checkoutUpstreamRevision(revision)
        except:
            self.log.critical("Checkout of %s failed!", self.name)
            raise

        if actual is None:
            raise EmptySourceRepository("Cannot complete the bootstrap")

        try:
            dwd.importFirstRevision(self.source, actual, 'INITIAL'==revision)
        except:
            self.log.critical('Could not import checked out tree in "%s"!',
                              self.rootdir, exc_info=True)
            raise

        self.log.info("Bootstrap completed")

    def update(self):
        """
        Update an existing tailorized project.
        """

        self.log.info('Updating "%s" in "%s"', self.name, self.rootdir)

        dwd = self.workingDir()
        try:
            pendings = dwd.getPendingChangesets()
        except KeyboardInterrupt:
            self.log.warning('Leaving "%s" unchanged, stopped by user',
                             self.name)
            raise
        except:
            self.log.fatal('Unable to get changes for "%s"', self.name)
            raise

        if pendings.pending():
            self.log.info("Applying pending upstream changesets")

            try:
                last, conflicts = dwd.applyPendingChangesets(
                    applyable=self._applyable, applied=self._applied)
            except KeyboardInterrupt:
                self.log.warning('Leaving "%s" incomplete, stopped by user',
                                 self.name)
                raise
            except:
                self.log.fatal('Upstream change application failed')
                raise

            if last:
                self.log.info('Update completed, now at revision "%s"',
                              last.revision)
        else:
            self.log.info("Update completed with no upstream changes")

    def __call__(self):
        from shwrap import ExternalCommand
        from target import SynchronizableTargetWorkingDir
        from changes import Changeset

        def pconfig(option, raw=False):
            return self.config.get(self.name, option, raw=raw)

        ExternalCommand.DEBUG = pconfig('debug')

        pname_format = pconfig('patch-name-format', raw=True)
        if pname_format is not None:
            SynchronizableTargetWorkingDir.PATCH_NAME_FORMAT = pname_format.strip()
        SynchronizableTargetWorkingDir.REMOVE_FIRST_LOG_LINE = pconfig('remove-first-log-line')
        Changeset.REFILL_MESSAGE = pconfig('refill-changelogs')

        try:
            if not self.exists():
                self.bootstrap()
                if pconfig('start-revision') == 'HEAD':
                    return
            self.update()
        except (UnicodeDecodeError, UnicodeEncodeError), exc:
            raise ConfigurationError('%s: it seems that the encoding '
                                     'used by either the source ("%s") or the '
                                     'target ("%s") repository '
                                     'cannot properly represent at least one '
                                     'of the characters in the upstream '
                                     'changelog. You need to use a wider '
                                     'character set, using "encoding" option, '
                                     'or even "encoding-errors-policy".'
                                     % (exc, self.source.encoding,
                                        self.target.encoding))
        except TailorBug, e:
            self.log.fatal("Unexpected internal error, please report", exc_info=e)
        except EmptySourceRepository, e:
            self.log.warning("Source repository seems empty: %s", e)
        except TailorException:
            raise
        except Exception, e:
            self.log.fatal("Something unexpected!", exc_info=e)

class RecogOption(Option):
    """
    Make it possible to recognize an option explicitly given on the
    command line from those simply coming out for their default value.
    """

    def process (self, opt, value, values, parser):
        setattr(values, '__seen_' + self.dest, True)
        return Option.process(self, opt, value, values, parser)


GENERAL_OPTIONS = [
    RecogOption("-D", "--debug", dest="debug",
                action="store_true", default=False,
                help="Print each executed command. This also keeps "
                     "temporary files with the upstream logs, that are "
                     "otherwise removed after use."),
    RecogOption("-v", "--verbose", dest="verbose",
                action="store_true", default=False,
                help="Be verbose, echoing the changelog of each applied "
                     "changeset to stdout."),
    RecogOption("-c", "--configfile", metavar="CONFNAME",
                help="Centralized storage of projects info.  With this "
                     "option and no other arguments tailor will update "
                     "every project found in the config file."),
    RecogOption("--encoding", metavar="CHARSET", default=None,
                help="Force the output encoding to given CHARSET, rather "
                     "then using the user's default settings specified "
                     "in the environment."),
]

UPDATE_OPTIONS = [
    RecogOption("-F", "--patch-name-format", metavar="FORMAT",
                help="Specify the prototype that will be used "
                     "to compute the patch name.  The prototype may contain "
                     "%(keyword)s such as 'author', 'date', "
                     "'revision', 'firstlogline', 'remaininglog'. It "
                     "defaults to 'Tailorized \"%(revision)s\"'; "
                     "setting it to the empty string means that tailor will "
                     "simply use the original changelog."),
    RecogOption("-1", "--remove-first-log-line", action="store_true",
                default=False,
                help="Remove the first line of the upstream changelog. This "
                     "is intended to pair with --patch-name-format, "
                     "when using its 'firstlogline' variable to build the "
                     "name of the patch."),
    RecogOption("-N", "--refill-changelogs", action="store_true",
                default=False,
                help="Refill every changelog, useful when upstream logs "
                     "are not uniform."),
]

BOOTSTRAP_OPTIONS = [
    RecogOption("-s", "--source-kind", dest="source_kind", metavar="VC-KIND",
                help="Select the backend for the upstream source "
                     "version control VC-KIND. Default is 'cvs'.",
                default="cvs"),
    RecogOption("-t", "--target-kind", dest="target_kind", metavar="VC-KIND",
                help="Select VC-KIND as backend for the shadow repository, "
                     "with 'darcs' as default.",
                default="darcs"),
    RecogOption("-R", "--repository", "--source-repository",
                dest="source_repository", metavar="REPOS",
                help="Specify the upstream repository, from where bootstrap "
                     "will checkout the module.  REPOS syntax depends on "
                     "the source version control kind."),
    RecogOption("-m", "--module", "--source-module", dest="source_module",
                metavar="MODULE",
                help="Specify the module to checkout at bootstrap time. "
                     "This has different meanings under the various upstream "
                     "systems: with CVS it indicates the module, while under "
                     "SVN it's the prefix of the tree you want and must begin "
                     "with a slash. Since it's used in the description of the "
                     "target repository, you may want to give it a value with "
                     "darcs too, even though it is otherwise ignored."),
    RecogOption("-r", "--revision", "--start-revision", dest="start_revision",
                metavar="REV",
                help="Specify the revision bootstrap should checkout.  REV "
                     "must be a valid 'name' for a revision in the upstream "
                     "version control kind. For CVS it may be either a branch "
                     "name, a timestamp or both separated by a space, and "
                     "timestamp may be 'INITIAL' to denote the beginning of "
                     "time for the given branch. Under Darcs, INITIAL is a "
                     "shortcut for the name of the first patch in the upstream "
                     "repository, otherwise it is interpreted as the name of "
                     "a tag. Under Subversion, 'INITIAL' is the first patch "
                     "that touches given repos/module, otherwise it must be "
                     "an integer revision number. "
                     "'HEAD' means the latest version in all backends.",
                default="INITIAL"),
    RecogOption("-T", "--target-repository",
                dest="target_repository", metavar="REPOS", default=None,
                help="Specify the target repository, the one that will "
                     "receive the patches coming from the source one."),
    RecogOption("-M", "--target-module", dest="target_module",
                metavar="MODULE",
                help="Specify the module on the target repository that will "
                     "actually contain the upstream source tree."),
    RecogOption("--subdir", metavar="DIR",
                help="Force the subdirectory where the checkout will happen, "
                     "by default it's the tail part of the module name."),
]

VC_SPECIFIC_OPTIONS = [
    RecogOption("--use-propset", action="store_true", default=False,
                dest="use_propset",
                help="Use 'svn propset' to set the real date and author of "
                     "each commit, instead of appending these information to "
                     "the changelog. This requires some tweaks on the SVN "
                     "repository to enable revision propchanges."),
    RecogOption("--ignore-arch-ids", action="store_true", default=False,
                dest="ignore_ids",
                help="Ignore .arch-ids directories when using a tla source."),
]


class ExistingProjectError(TailorException):
    "Project seems already tailored"


class ProjectNotTailored(TailorException):
    "Not a tailored project"


def main():
    """
    Script entry point.

    Parse the command line options and arguments, and for each
    specified working copy directory (the current working directory by
    default) execute the tailorization steps.
    """

    import sys
    from os import getcwd

    usage = "usage: \n\
       1. %prog [options] [project ...]\n\
       2. %prog test [--help] [...]"
    parser = OptionParser(usage=usage,
                          version=__version__,
                          option_list=GENERAL_OPTIONS)

    bsoptions = OptionGroup(parser, "Bootstrap options")
    bsoptions.add_options(BOOTSTRAP_OPTIONS)

    upoptions = OptionGroup(parser, "Update options")
    upoptions.add_options(UPDATE_OPTIONS)

    vcoptions = OptionGroup(parser, "VC specific options")
    vcoptions.add_options(VC_SPECIFIC_OPTIONS)

    parser.add_option_group(bsoptions)
    parser.add_option_group(upoptions)
    parser.add_option_group(vcoptions)

    options, args = parser.parse_args()

    defaults = {}
    for k,v in options.__dict__.items():
        if k.startswith('__'):
            continue
        if k <> 'configfile' and hasattr(options, '__seen_' + k):
            defaults[k.replace('_', '-')] = str(v)

    if options.configfile or (len(sys.argv)==2 and len(args)==1):
        # Either we have a --configfile, or there are no options
        # and a single argument (to support shebang style scripts)

        if not options.configfile:
            options.configfile = sys.argv[1]
            args = None

        config = Config(open(options.configfile), defaults)

        if not args:
            args = config.projects()

        for projname in args:
            tailorizer = Tailorizer(projname, config)
            try:
                tailorizer()
            except GetUpstreamChangesetsFailure:
                # Do not stop on this kind of error, but keep going
                pass
    else:
        for omit in ['source-kind', 'target-kind',
                     'source-module', 'target-module',
                     'source-repository', 'target-repository',
                     'start-revision', 'subdir']:
            if omit in defaults:
                del defaults[omit]

        config = Config(None, defaults)

        config.add_section('project')
        source = options.source_kind + ':source'
        config.set('project', 'source', source)
        target = options.target_kind + ':target'
        config.set('project', 'target', target)
        config.set('project', 'root-directory', getcwd())
        config.set('project', 'subdir', options.subdir or '.')
        config.set('project', 'state-file', 'tailor.state')
        config.set('project', 'start-revision', options.start_revision)

        config.add_section(source)
        if options.source_repository:
            config.set(source, 'repository', options.source_repository)
        else:
            logger = getLogger('tailor')
            logger.warning("By any chance you forgot either the --source-repository or the --configfile option...")

        if options.source_module:
            config.set(source, 'module', options.source_module)

        config.add_section(target)
        if options.target_repository:
            config.set(target, 'repository', options.target_repository)
        if options.target_module:
            config.set(target, 'module', options.target_module)

        if options.verbose:
            sys.stderr.write("You should put the following configuration "
                             "in some file, adjust it as needed\n"
                             "and use --configfile option with that "
                             "file as argument:\n")
            config.write(sys.stdout)

        if options.debug:
            tailorizer = Tailorizer('project', config)
            tailorizer()
        elif not options.verbose:
            sys.stderr.write("Operation not performed, try --verbose\n")
