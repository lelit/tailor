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

from optparse import OptionParser, OptionGroup, make_option
from dualwd import DualWorkingDir
from source import InvocationError
from session import interactive

STATUS_FILENAME = 'tailor.info'
LOG_FILENAME = 'tailor.log'

def relpathto(source, dest):
    """
    Compute the relative path needed to point ``source`` from ``dest``.

    Warning: ``dest`` is assumed to be a directory.
    """
    
    from os.path import abspath, split, commonprefix
    
    source = abspath(source)
    dest = abspath(dest)

    if source.startswith(dest):
        return source[len(dest)+1:]
    
    prefix = commonprefix([source, dest])

    source = source[len(prefix):]
    dest = dest[len(prefix):]

    return '../' * len(dest.split('/')) + source


class TailorConfig(object):
    """
    Configuration of a set of tailorized projects.

    The configuration is stored in a persistent dictionary keyed on the
    relative path of each project. The information about a single project
    is another dictionary.
    """
    
    def __init__(self, options):
        from os.path import abspath, split
        
        self.options = options
        self.configfile = abspath(options.configfile)
        self.basedir = split(self.configfile)[0]
        
    def __call__(self, args):
        from os.path import join, exists, split
        from source import ChangesetApplicationFailure
        
        self.__load()

        if len(args) == 0:
            fromconfig = True
            if self.options.bootstrap:
                f = lambda x: not exists(x)
            else:
                f = exists
                
            args = [p for p in [join(self.basedir, r)
                                for r in self.config.keys()] if f(p)]
            args.sort()
        else:
            fromconfig = False
            
        try:
            for root in args:
                if self.options.bootstrap:                
                    if not (fromconfig or self.options.repository):
                        raise InvocationError('Need a repository to bootstrap '
                                              '%r' % root, '--bootstrap')
                else:
                    if not self.config.has_key(relpathto(root, self.basedir)):
                        raise UnknownProjectError("Project %r does not exist" %
                                                  root)
                    
                tailored = TailorizedProject(root, self.options.verbose, self)

                if self.options.bootstrap:
                    if fromconfig:                        
                        info = self.loadProject(root=root)
                        self.options.source_kind = info['source_kind']
                        self.options.target_kind = info['target_kind']
                        self.options.repository = info['upstream_repos']
                        self.options.module = info['module']
                        self.options.subdir = info.get('subdir',
                                                       split(info['module'])[1])
                        self.options.revision = info['upstream_revision']
                        
                    tailored.bootstrap(self.options.source_kind,
                                       self.options.target_kind,
                                       self.options.repository,
                                       self.options.module,
                                       self.options.revision,
                                       self.options.subdir)
                elif self.options.migrate:
                    tailored.migrateConfiguration()
                elif self.options.update:
                    try:
                        tailored.update(self.options.single_commit,
                                        self.options.concatenate_logs)
                    except ChangesetApplicationFailure, e:
                        print "Skipping '%s' because of errors:" % root, e
        finally:
            self.__save()
        
    def __save(self):
        from pprint import pprint

        configfile = open(self.configfile, 'w')
        pprint(self.config, configfile)
        configfile.close()

    def __load(self):
        from os.path import exists

        if exists(self.options.configfile):
            configfile = open(self.configfile)
            self.config = eval(configfile.read())
            configfile.close()
        else:
            self.config = {}
            
    def loadProject(self, project=None, root=None):
        from os.path import split
        
        relpath = relpathto(project and project.root or root, self.basedir)
        
        info = self.config.get(relpath)
        if info and project:
            project.source_kind = info['source_kind']
            project.target_kind = info['target_kind']
            project.module = info['module']
            project.subdir = info.get('subdir', split(project.module)[1])
            project.upstream_repos = info['upstream_repos']
            project.upstream_revision = info['upstream_revision']

        return info
        
    def saveProject(self, project):
        relpath = relpathto(project.root, self.basedir)
        
        self.config[relpath] = { 
            'source_kind': project.source_kind,
            'target_kind': project.target_kind,
            'module': project.module,
            'subdir': project.subdir,
            'upstream_repos': project.upstream_repos,
            'upstream_revision': project.upstream_revision,
            }

    
class TailorizedProject(object):
    """
    A TailorizedProject has two main capabilities: it may be bootstrapped
    from an upstream repository or brought in sync with current upstream
    revision.
    """
    
    def __init__(self, root, verbose=False, config=None):
        import logging
        from os import makedirs
        from os.path import join, exists, split

        self.root = root
        if not exists(root):
            makedirs(root)

        self.verbose = verbose
        self.logger = logging.getLogger('tailor.%s' % split(root)[1])
        hdlr = logging.FileHandler(join(root, LOG_FILENAME))
        formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(message)s')
        hdlr.setFormatter(formatter)
        self.logger.addHandler(hdlr) 
        self.logger.setLevel(logging.INFO)

        self.source_kind = self.target_kind = None

        self.config = config

    def migrateConfiguration(self):
        self.__loadOldStatus()
        self.__saveStatus()
        
    def __saveOldStatus(self):
        from os.path import join

        statusfilename = join(self.root, STATUS_FILENAME)
        f = open(statusfilename, 'w')
        print >>f, self.source_kind
        print >>f, self.target_kind        
        print >>f, self.module        
        print >>f, self.upstream_repos
        print >>f, self.upstream_revision
        print >>f, self.subdir
        f.close()

    def __saveStatus(self):
        """
        Save relevant project information in a persistent way.
        """

        if self.config:
            self.config.saveProject(self)
        else:
            self.__saveOldStatus()

    def __loadOldStatus(self):
        from os.path import join, split

        statusfilename = join(self.root, STATUS_FILENAME)
        f = open(statusfilename)
        self.source_kind = f.readline()[:-1]
        self.target_kind = f.readline()[:-1]
        self.module = f.readline()[:-1]
        self.upstream_repos = f.readline()[:-1]
        self.upstream_revision = f.readline()[:-1]
        subdir = f.readline()
        if subdir:
            self.subdir = subdir[:-1]
        else:
            self.subdir = split(self.module)[1]            
        f.close()

    def __loadStatus(self):
        """
        Load relevant project information.
        """

        if self.config:
            self.config.loadProject(self)
        else:
            self.__loadOldStatus()

        # Fix old configs
        
        if self.source_kind == 'svn' and not '/' in self.module:
            self.logger.warning('OLD config values for SVN')
            print "The project at '%s' contains old values for" % self.root
            print "the upstream repository (%s)" % self.upstream_repos
            print "and module (%s)." % self.module
            print "Please correct them, specifying the exact URL of the"
            print "root of the SVN repository and then the prefix path up"
            print "to the point you want, that must start with a slash."
            print "This usually means splitting the repository URL above in"
            print "two parts. For example, that could be"
            
            crepo = self.upstream_repos
            example_split = crepo.rfind('/', 6, crepo.rfind('/'))
            if example_split > 0:
                example_repo = crepo[:example_split]
                example_module = crepo[example_split:]
            else:
                example_repo = 'http://svn.plone.org/collective'
                example_module = '/ATContentTypes/trunk'
            
            print "  Repository=%s" % example_repo
            print "  Module=%s" % example_module
            print "but your situation may vary, that's just an example!"
            print
            try:
                self.repository = raw_input('Repository: ')
                self.module = raw_input('Module/prefix: ')
            except KeyboardInterrupt:
                self.logger.warning("Leaving old config values, stopped by user")
                raise
            
    def bootstrap(self, source_kind, target_kind,
                  repository, module, revision, subdir):
        """
        Bootstrap a new tailorized module.

        Extract a copy of the ``repository`` at given ``revision`` in the
        ``root`` directory and initialize a target repository with its content.

        The actual information on the project are stored in a text file.
        """

        from os.path import split, sep

        if source_kind == 'svn':
            if not (module and module.startswith(sep)):
                raise InvocationError('With SVN the module argument is '
                                      'mandatory and must start '
                                      'with a "%s"' % sep)

        if repository.endswith(sep):
            repository = repository[:-1]

        if module and module.endswith(sep):
            module = module[:-1]
            
        if not subdir:
            subdir = split(module or repository)[1] or ''
            
        self.logger.info("Bootstrapping '%s'" % (self.root,))

        dwd = DualWorkingDir(source_kind, target_kind)
        self.logger.info("getting %s revision '%s' of '%s' from '%s'" % (
            source_kind, revision, module, repository))

        try:
            actual = dwd.checkoutUpstreamRevision(self.root, repository,
                                                  module, revision,
                                                  subdir=subdir,
                                                  logger=self.logger)
        except:
            self.logger.exception('Checkout failed!')
            raise
        
        # the above machinery checked out a copy under of the wc
        # in the directory named as the last component of the module's name

        if not module:
            module = split(repository)[1]

        try:
            dwd.initializeNewWorkingDir(self.root, repository, module, subdir, actual)
        except:
            self.logger.exception('Working copy initialization failed!')
            raise
        
        self.source_kind = source_kind
        self.target_kind = target_kind
        self.upstream_repos = repository
        self.module = module
        self.subdir = subdir
        self.upstream_revision = actual

        self.__saveStatus()

        self.logger.info("Bootstrap completed")

    def applyable(self, root, changeset):
        """
        Print the changeset being applied.
        """

        if self.verbose:
            print "Changeset %s:" % changeset.revision
            print changeset.log

        return True
    
    def applied(self, root, changeset):
        """
        Save current status.
        """

        self.upstream_revision = changeset.revision
        self.__saveStatus()
        if self.verbose:
            print

    def update(self, single_commit, concatenate_logs):
        """
        Update an existing tailorized project.

        Fetch the upstream changesets and apply them to the working copy.
        Use the information stored in the ``tailor.info`` file to ask just
        the new changeset since last bootstrap/synchronization.
        """
        
        from os.path import join

        self.__loadStatus()
        proj = join(self.root, self.subdir)

        self.logger.info("Updating '%s' from revision '%s'" % (
            self.module, self.upstream_revision))

        if self.verbose:
            print "\nUpdating '%s' from revision '%s'" % (
                self.module, self.upstream_revision)

        try:
            dwd = DualWorkingDir(self.source_kind, self.target_kind)
            changesets = dwd.getUpstreamChangesets(proj,
                                                   self.upstream_repos,
                                                   self.module,
                                                   self.upstream_revision)
        except KeyboardInterrupt:
            print "Leaving '%s' unchanged" % proj
            self.logger.info("Leaving '%s' unchanged, stopped by user" % proj)
            return
        except:
            self.logger.exception("Unable to get changes for '%s'" % proj)
            raise
        
        nchanges = len(changesets)
        if nchanges:
            if self.verbose:
                print "Applying %d upstream changesets" % nchanges

            try:
                last, conflicts = dwd.applyUpstreamChangesets(
                    proj, self.module, changesets, applyable=self.applyable,
                    applied=self.applied, logger=self.logger,
                    delayed_commit=single_commit)
            except:
                self.logger.exception('Upstream change application failed')
                raise
            
            if last:
                if single_commit:
                    dwd.commitDelayedChangesets(proj, concatenate_logs)

                self.logger.info("Update completed, now at revision '%s'" % (
                    self.upstream_revision,))
        else:
            self.logger.info("Update completed with no upstream changes")


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
                     "'mindate' and 'maxdate' when using --single-commit."),
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
    make_option("-R", "--repository", dest="repository", metavar="REPOS",
                help="Specify the upstream repository, from where bootstrap "
                     "will checkout the module.  REPOS syntax depends on "
                     "the source version control kind."),
    make_option("-m", "--module", dest="module", metavar="MODULE",
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
                     "name, a timestamp or both separated by a space. "
                     "'HEAD', the default, means the latest version in all "
                     "backends.",
                default="HEAD"),
    make_option("--subdir", metavar="DIR",
                help="Force the subdirectory where the checkout will happen, "
                     "by default it's the tail part of the module name."),
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
                          option_list=GENERAL_OPTIONS)
    
    bsoptions = OptionGroup(parser, "Bootstrap options")
    bsoptions.add_options(BOOTSTRAP_OPTIONS)

    upoptions = OptionGroup(parser, "Update options")
    upoptions.add_options(UPDATE_OPTIONS)
    
    parser.add_option_group(bsoptions)
    parser.add_option_group(upoptions)
    
    options, args = parser.parse_args()
    
    ExternalCommand.VERBOSE = options.debug
    if options.encoding:
        ExternalCommand.FORCE_ENCODING = options.encoding

        # Make printouts be encoded as well. A better solution would be
        # using the replace mechanism of the encoder, and keep printing
        # in the user LC_CTYPE/LANG setting.
        
        import codecs, sys
        sys.stdout = codecs.getwriter(options.encoding)(sys.stdout)

    if options.patch_name_format:
        SyncronizableTargetWorkingDir.PATCH_NAME_FORMAT = options.patch_name_format
    SyncronizableTargetWorkingDir.REMOVE_FIRST_LOG_LINE = options.remove_first_log_line
    Changeset.REFILL_MESSAGE = not options.dont_refill_changelogs

    if options.interactive:
        interactive(options, args)
    elif options.configfile:
        config = TailorConfig(options)

        config(map(abspath, args))
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

                if not options.repository:
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
                                   options.repository,
                                   options.module,
                                   options.revision,
                                   options.subdir)
            elif options.update:
                tailored.update(options.single_commit,
                                options.concatenate_logs)
