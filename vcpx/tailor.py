#! /usr/bin/python
# -*- mode: python; coding: utf-8 -*-
# :Progetto: vcpx -- Frontend capabilities
# :Creato:   dom 04 lug 2004 00:40:54 CEST
# :Autore:   Lele Gaifax <lele@nautilus.homeip.net>
# 

"""
Implement the basic capabilities of the frontend.

This implementation stores the relevant project information, needed to
keep the whole thing going on, such as the last synced revision, in a
unversioned file named `tailor.info` at the root.
"""

__docformat__ = 'reStructuredText'

from dualwd import DualWorkingDir

STATUS_FILENAME = 'tailor.info'
LOG_FILENAME = 'tailor.log'

class TailorConfig(object):
    def __init__(self, options):
        self.options = options
        
    def __call__(self, args):
        from os.path import abspath
        
        self.__load()

        if len(args) == 0 and self.options.update:
            args = self.config.keys()

        for a in args:
            root = abspath(a)
            
            tailored = TailorizedProject(root, self.options.verbose, self)
            
            if self.options.bootstrap:                
                tailored.bootstrap(self.options.source_kind,
                                   self.options.target_kind,
                                   self.options.repository,
                                   self.options.module,
                                   self.options.revision)
            elif self.options.migrate:
                tailored.migrateConfiguration()
            elif self.options.update:
                tailored.update(self.options.single_commit,
                                self.options.concatenate_logs)

        self.__save()
        
    def __save(self):
        from pprint import pprint

        configfile = open(self.options.configfile, 'w')
        pprint(self.config, configfile)
        configfile.close()

    def __load(self):
        from os.path import exists

        if exists(self.options.configfile):
            configfile = open(self.options.configfile)
            self.config = eval(configfile.read())
            configfile.close()
        else:
            self.config = {}
            
    def loadProject(self, project):
        info = self.config.get(project.root)

        if info:
            project.source_kind = info['source_kind']
            project.target_kind = info['target_kind']
            project.module = info['module']
            project.upstream_repos = info['upstream_repos']
            project.upstream_revision = info['upstream_revision']

        return info
        
    def saveProject(self, project):
        self.config[project.root] = { 
            'source_kind': project.source_kind,
            'target_kind': project.target_kind,
            'module': project.module,
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
        from os.path import join

        statusfilename = join(self.root, STATUS_FILENAME)
        f = open(statusfilename)
        (srck, dstk,
         module, upstream_repos, upstream_revision) = f.readlines()
        self.source_kind = srck[:-1]
        self.target_kind = dstk[:-1]
        self.module = module[:-1]
        self.upstream_repos = upstream_repos[:-1]
        self.upstream_revision = upstream_revision[:-1]
        f.close()

    def __loadStatus(self):
        """
        Load relevant project information.
        """

        if self.config:
            self.config.loadProject(self)
        else:
            self.__loadOldStatus()
            
    def bootstrap(self, source_kind, target_kind, repository, module,revision):
        """
        Bootstrap a new tailorized module.

        Extract a copy of the `repository` at given `revision` in the `root`
        directory and initialize a target repository with its content.

        The actual information on the project are stored in a text file.
        """

        from os.path import split
        
        self.logger.info("Bootstrapping '%s'" % (self.root,))

        dwd = DualWorkingDir(source_kind, target_kind)
        self.logger.info("getting %s revision '%s' of '%s' from '%s'" % (
            source_kind, revision, module, repository))
        actual = dwd.checkoutUpstreamRevision(self.root, repository,
                                              module, revision,
                                              logger=self.logger)

        # the above machinery checked out a copy under of the wc
        # in the directory named as the last component of the module's name

        dwd.initializeNewWorkingDir(self.root, repository,
                                    split(module)[1], actual)

        self.source_kind = source_kind
        self.target_kind = target_kind
        self.upstream_repos = repository
        self.module = module        
        self.upstream_revision = actual

        self.__saveStatus()

        self.logger.info("Bootstrap completed")

    def applied(self, root, changeset):
        """
        Save current status.
        """

        self.upstream_revision = changeset.revision
        self.__saveStatus()
        if self.verbose:
            print "# Applied changeset %s" % changeset.revision
            print changeset.log

    def update(self, single_commit, concatenate_logs):
        """
        Update an existing tailorized project.

        Fetch the upstream changesets and apply them to the working copy.
        Use the information stored in the `tailor.info` file to ask just
        the new changeset since last bootstrap/synchronization.
        """
        
        from os.path import join, split
        
        self.__loadStatus()

        proj = join(self.root, split(self.module)[1])
        self.logger.info("Updating '%s' from revision '%s'" % (
            self.module, self.upstream_revision))

        if self.verbose:
            print "\nUpdating '%s' from revision '%s'" % (self.module,
                                                          self.upstream_revision)
        
        dwd = DualWorkingDir(self.source_kind, self.target_kind)
        changesets = dwd.getUpstreamChangesets(proj, self.upstream_revision)

        nchanges = len(changesets)
        if nchanges:
            if self.verbose:
                print "Applying %d upstream changesets" % nchanges
                
            l,c = dwd.applyUpstreamChangesets(proj, changesets,
                                              applied=self.applied,
                                              logger=self.logger,
                                              delayed_commit=single_commit)
            if l:
                if single_commit:
                    dwd.commitDelayedChangesets(proj, concatenate_logs)

                self.logger.info("Update completed, now at revision '%s'" % (
                    self.upstream_revision,))
        else:
            self.logger.info("Update completed with no upstream changes")


from optparse import OptionParser, OptionError, OptionGroup, make_option

GENERAL_OPTIONS = [
    make_option("-D", "--debug", dest="debug",
                action="store_true", default=False,
                help="Print each executed command."),
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
                help="Specify the module to checkout at bootstrap time."),
    make_option("-r", "--revision", dest="revision", metavar="REV",
                help="Specify the revision bootstrap should checkout.  REV "
                     "must be a valid 'name' for a revision in the upstream "
                     "version control kind.  For CVS it may be a tag/branch. "
                     "'HEAD', the default, means the latest version in all "
                     "backends.",
                default="HEAD"),
]

class ExistingProjectError(Exception):
    """
    Raised when, in bootstrap mode, the directory for the project is already
    there.
    """

class UnknownProjectError(Exception):
    """
    Raised when, in normal mode, the directory for the project does not
    exist.
    """

class ProjectNotTailored(Exception):
    """
    Raised when trying to do something on a project that has not been
    tailored.
    """
    
def main():
    """
    Script entry point.

    Parse the command line options and arguments, and for each
    specified working copy directory (the current working directory by
    default) execute the tailorization steps.
    """
    
    from os import getcwd, chdir
    from os.path import abspath, exists, join, split
    from shwrap import SystemCommand
    
    parser = OptionParser(usage='%prog [options] [project ...]',
                          option_list=GENERAL_OPTIONS)
    
    bsoptions = OptionGroup(parser, "Bootstrap options")
    bsoptions.add_options(BOOTSTRAP_OPTIONS)

    upoptions = OptionGroup(parser, "Update options")
    upoptions.add_options(UPDATE_OPTIONS)
    
    parser.add_option_group(bsoptions)
    parser.add_option_group(upoptions)
    
    options, args = parser.parse_args()
    
    SystemCommand.VERBOSE = options.debug

    base = getcwd()
        
    if options.configfile:
        config = TailorConfig(options)

        config(args)
    else:
        # Good (?) old way
        
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
                    raise OptionError('Need a repository to bootstrap %r' %
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
                                   options.revision)
            elif options.update:
                tailored.update(options.single_commit,
                                options.concatenate_logs)

