# -*- mode: python; coding: utf-8 -*-
# :Progetto: vcpx -- Frontend capabilities
# :Creato:   dom 04 lug 2004 00:40:54 CEST
# :Autore:   Lele Gaifax <lele@nautilus.homeip.net>
# :Licenza:  GNU General Public License
#

"""
Implement the basic capabilities of the frontend.

This implementation stores the relevant project information, needed to
keep the whole thing going on, such as the last synced revision, in a
unversioned file named ``tailor.info`` at the root.
"""

__docformat__ = 'reStructuredText'

__version__ = '0.9.1'

from optparse import OptionParser, OptionGroup, make_option
from config import Config
from source import InvocationError
from session import interactive

class Tailorizer(object):
    """
    A Tailorizer has two main capabilities: its able to bootstrap a
    new Project, or brought it in sync with its current upstream
    revision.
    """

    def __init__(self, project):
        self.project = project

    def bootstrap(self):
        """
        Bootstrap a new tailorized module.

        First of all prepare the target system working directory such
        that it can host the upstream source tree. This is backend
        specific.

        Then extract a copy of the upstream repository and import its
        content into the target repository.
        """

        self.project.log_info("Bootstrapping '%s'" % self.project.root)

        try:
            self.project.prepareWorkingDirectory()
        except:
            self.project.log_error('Cannot prepare working directory!', True)
            raise

        try:
            self.project.checkoutUpstreamRevision()
        except:
            self.project.log_error("Checkout of '%s' failed!" %
                                   self.project.name, True)
            raise

        self.project.log_info("Bootstrap completed")

    def update(self):
        """
        Update an existing tailorized project.
        """

        self.project.log_info("Updating '%s'" % self.project.name)

        try:
            self.project.applyPendingChangesets()
        except:
            self.project.log_error("Cannot update '%s'!" % self.project.name,
                                   True)
            raise

        self.project.log_info("Update completed")

    def __call__(self, options):
        if options.bootstrap:
            self.bootstrap()
        else:
            self.update()

GENERAL_OPTIONS = [
    make_option("-i", "--interactive", default=False, action="store_true",
                help="Start an interactive session."),
    make_option("-D", "--debug", dest="debug",
                action="store_true", default=False,
                help="Print each executed command. This also keeps "
                     "temporary files with the upstream logs, that are "
                     "otherwise removed after use."),
    make_option("-v", "--verbose", dest="verbose",
                action="store_true", default=False,
                help="Be verbose, echoing the changelog of each applied "
                     "changeset to stdout."),
    make_option("--configfile", metavar="CONFNAME",
                help="Centralized storage of projects info.  With this "
                     "option and no other arguments tailor will update "
                     "every project found in the config file."),
    make_option("--migrate-config", dest="migrate",
                action="store_true", default=False,
                help="Migrate old configuration to new centralized storage."),
    make_option("--encoding", metavar="CHARSET", default=None,
                help="Force the output encoding to given CHARSET, rather "
                     "then using the user default settings specified in the "
                     "environment."),
]

UPDATE_OPTIONS = [
    make_option("--update", action="store_true", default=True,
                help="Update the given repositories, fetching upstream "
                     "changesets, applying and re-registering each one. "
                     "This is the default behaviour."),
    make_option("-S", "--single-commit", action="store_true", default=False,
                help="Do a single, final commit on the target VC, effectively "
                     "grouping together all upstream changeset into a single "
                     "one, from the target VC point of view."),
    make_option("-C", "--concatenate-logs", action="store_true", default=False,
                help="With --single-commit, concatenate each changeset "
                     "message log to the final changelog, instead of just "
                     "the name of the patch."),
    make_option("-F", "--patch-name-format", metavar="FORMAT",
                help="Specify the prototype that will be used "
                     "to compute the patch name.  The prototype may contain "
                     "%(keyword)s such as 'module', 'author', 'date', "
                     "'revision', 'firstlogline', 'remaininglog' for normal "
                     "updates, otherwise 'module', 'authors', 'nchangesets', "
                     "'mindate' and 'maxdate' when using --single-commit. It "
                     "defaults to '%(module)s: changeset %(revision)s'; "
                     "setting it to the empty string means that tailor will "
                     "simply use the original changelog."),
    make_option("-1", "--remove-first-log-line", action="store_true",
                default=False,
                help="Remove the first line of the upstream changelog. This "
                     "is intended to go in pair with --patch-name-format, "
                     "when using it's 'firstlogline' variable to build the "
                     "name of the patch."),
    make_option("-N", "--dont-refill-changelogs", action="store_true",
                default=False,
                help="Do not refill every changelog, but keep them as is. "
                     "This is usefull when using --patch-name-format, or "
                     "when upstream developers are already formatting their "
                     "notes with a consistent layout."),
]

BOOTSTRAP_OPTIONS = [
    make_option("-b", "--bootstrap", action="store_true", default=False,
                help="Bootstrap mode, that is the initial copy of the "
                     "upstream tree, given as an URI (see -R) and maybe "
                     "a revision (-r).  This overrides --update."),
    make_option("-s", "--source-kind", dest="source_kind", metavar="VC-KIND",
                help="Select the backend for the upstream source "
                     "version control VC-KIND. Default is 'cvs'.",
                default="cvs"),
    make_option("-t", "--target-kind", dest="target_kind", metavar="VC-KIND",
                help="Select VC-KIND as backend for the shadow repository, "
                     "with 'darcs' as default.",
                default="darcs"),
    make_option("-R", "--repository", "--source-repository",
                dest="source_repository", metavar="REPOS",
                help="Specify the upstream repository, from where bootstrap "
                     "will checkout the module.  REPOS syntax depends on "
                     "the source version control kind."),
    make_option("-m", "--module", "--source-module", dest="source_module",
                metavar="MODULE",
                help="Specify the module to checkout at bootstrap time. "
                     "This has different meanings under the various upstream "
                     "systems: with CVS it indicates the module, while under "
                     "SVN it's the prefix of the tree you want and must begin "
                     "with a slash. Since it's used in the description of the "
                     "target repository, you may want to give it a value with "
                     "darcs too even if it is otherwise ignored."),
    make_option("-r", "--revision", dest="revision", metavar="REV",
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
                     "'HEAD', the default, means the latest version in all "
                     "backends.",
                default="HEAD"),
    make_option("-T", "--target-repository",
                dest="target_repository", metavar="REPOS", default=None,
                help="Specify the target repository, the one that will "
                     "receive the patches coming from the source one."),
    make_option("-M", "--target-module", dest="target_module",
                metavar="MODULE",
                help="Specify the module on the target repository that will "
                     "actually contain the upstream source tree."),
    make_option("--subdir", metavar="DIR",
                help="Force the subdirectory where the checkout will happen, "
                     "by default it's the tail part of the module name."),
]

VC_SPECIFIC_OPTIONS = [
    make_option("--use-svn-propset", action="store_true", default=False,
                help="Use 'svn propset' to set the real date and author of "
                     "each commit, instead of appending these information to "
                     "the changelog. This requires some tweaks on the SVN "
                     "repository to enable revision propchanges."),
]

class ExistingProjectError(Exception):
    "Project seems already tailored"

class UnknownProjectError(Exception):
    "Project does not exist"

class ProjectNotTailored(Exception):
    "Not a tailored project"

def main():
    """
    Script entry point.

    Parse the command line options and arguments, and for each
    specified working copy directory (the current working directory by
    default) execute the tailorization steps.
    """

    from os import getcwd, chdir
    from os.path import abspath, exists, join
    from shwrap import ExternalCommand
    from target import SyncronizableTargetWorkingDir
    from changes import Changeset

    parser = OptionParser(usage='%prog [options] [project ...]',
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

    ExternalCommand.VERBOSE = options.debug
    if options.encoding:
        ExternalCommand.FORCE_ENCODING = options.encoding

        # Make printouts be encoded as well. A better solution would be
        # using the replace mechanism of the encoder, and keep printing
        # in the user LC_CTYPE/LANG setting.

        import codecs, sys
        sys.stdout = codecs.getwriter(options.encoding)(sys.stdout)

    if options.patch_name_format is not None:
        SyncronizableTargetWorkingDir.PATCH_NAME_FORMAT = options.patch_name_format
    SyncronizableTargetWorkingDir.REMOVE_FIRST_LOG_LINE = options.remove_first_log_line
    Changeset.REFILL_MESSAGE = not options.dont_refill_changelogs

    if options.interactive:
        interactive(options, args)
    elif options.configfile:
        defaults = {}
        for k,v in options.__dict__.items():
            defaults[k.replace('_', '-')] = v

        config = Config(open(options.configfile), defaults)

        if not args:
            args = config.projects()

        for projname in args:
            project = config[projname]
            tailorizer = Tailorizer(project)
            tailorizer(options)
    else:
        # Good (?) old way

        config = None

        base = getcwd()

        if len(args) == 0:
            args.append(base)

        while args:
            chdir(base)

            proj = args.pop(0)
            root = abspath(proj)

            if options.bootstrap:
                if exists(join(root, STATUS_FILENAME)):
                    raise ExistingProjectError(
                        "Project %r cannot be bootstrapped twice" % proj)

                if not options.source_repository:
                    raise InvocationError('Need a repository to bootstrap %r' %
                                          proj)
            else:
                if not exists(proj):
                    raise UnknownProjectError("Project %r does not exist" %
                                              proj)

                if not exists(join(root, STATUS_FILENAME)):
                    raise UnknownProjectError(
                        "%r is not a tailorized project" % proj)

            tailored = TailorizedProject(root, options.verbose, config)

            if options.bootstrap:
                tailored.bootstrap(options.source_kind, options.target_kind,
                                   options.source_repository,
                                   options.source_module,
                                   options.revision,
                                   options.target_repository,
                                   options.target_module,
                                   options.subdir)
            elif options.update:
                tailored.update(options.single_commit,
                                options.concatenate_logs)
