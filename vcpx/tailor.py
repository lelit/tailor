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
    
class TailorizedProject(object):
    """
    A TailorizedProject has two main capabilities: it may be bootstrapped
    from an upstream repository or brought in sync with current upstream
    revision.
    """
    
    def __init__(self, root):
        import logging
        from os import makedirs
        from os.path import join, exists

        self.root = root
        if not exists(root):
            makedirs(root)
        
        self.logger = logging.getLogger('tailor')
        hdlr = logging.FileHandler(join(root, LOG_FILENAME))
        formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(message)s')
        hdlr.setFormatter(formatter)
        self.logger.addHandler(hdlr) 
        self.logger.setLevel(logging.INFO)

        self.source_kind = self.target_kind = None
                
    def __saveStatus(self):
        """
        Save relevant project information in a persistent way.
        """
        
        from os.path import join, exists

        statusfilename = join(self.root, STATUS_FILENAME)
        f = open(statusfilename, 'w')
        print >>f, self.source_kind
        print >>f, self.target_kind        
        print >>f, self.module        
        print >>f, self.upstream_repos
        print >>f, self.upstream_revision
        f.close()
        
    def __loadStatus(self):
        """
        Load relevant project information.
        """
        
        from os.path import join, exists

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

    def bootstrap(self, source_kind, target_kind,
                  repository, module, revision):
        """
        Bootstrap a new tailorized module.

        Extract a copy of the `repository` at given `revision` in the `root`
        directory and initialize a target repository with its content.

        The actual information on the project are stored in a text file.
        """

        from os.path import join
        
        self.logger.info("Bootstrapping '%s'" % (self.root,))

        dwd = DualWorkingDir(source_kind, target_kind)
        self.logger.info("getting %s revision '%s' of '%s' from '%s'" % (
            source_kind, revision, module, repository))
        actual = dwd.checkoutUpstreamRevision(self.root, repository,
                                              module, revision,
                                              logger=self.logger)
        self.logger.info("initializing %s shadow" % target_kind)
        dwd.initializeNewWorkingDir(self.root, repository, module, actual)

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
        
    def update(self):
        """
        Update an existing tailorized project.

        Fetch the upstream changesets and apply them to the working copy.
        Use the information stored in the `tailor.info` file to ask just
        the new changeset since last bootstrap/synchronization.
        """
        
        from os.path import join
        
        self.__loadStatus()

        proj = join(self.root, self.module)
        self.logger.info("Updating '%s' from revision '%s'" % (
            proj, self.upstream_revision))
        
        dwd = DualWorkingDir(self.source_kind, self.target_kind)
        actual,conflicts = dwd.applyUpstreamChangesets(proj,
                                                       self.upstream_revision,
                                                       applied=self.applied,
                                                       logger=self.logger)
        if actual:
            self.logger.info("Update completed, now at revision '%s'" % (
                self.upstream_revision,))
        else:
            self.logger.info("Update completed with no upstream changes")


from optparse import OptionParser, OptionError, OptionGroup, make_option

OPTIONS = [
    make_option("-D", "--debug", dest="debug",
                action="store_true", default=False),
    make_option("-s", "--source-kind", dest="source_kind", metavar="VC-KIND",
                help="Select the backend for the upstream source "
                     "version control VC-KIND. Default is 'cvs'.",
                default="cvs"),
    make_option("-t", "--target-kind", dest="target_kind", metavar="VC-KIND",
                help="Select VC-KIND as backend for the shadow repository, "
                     "with 'darcs' as default.",
                default="darcs"),    
]    

ACTIONS = [
    make_option("-b", "--bootstrap", action="store_true", default=False,
                help="Bootstrap mode, that is the initial copy of the "
                     "upstream tree, given as an URI possibly followed "
                     "by a revision."),
    make_option("-i", "--info", action="store_true", default=False,
                help="Just show ancestry information."),
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
    
    parser = OptionParser(usage='%prog [options] [proj [URI[@revision]]]...',
                          option_list=OPTIONS)
    actions = OptionGroup(parser, "Other actions")
    actions.add_options(ACTIONS)
    parser.add_option_group(actions)
    
    options, args = parser.parse_args()
    
    SystemCommand.VERBOSE = options.debug
    
    base = getcwd()
    
    if len(args) == 0:
        args.append(base)
       
    while args:
        chdir(base)
        
        proj = args.pop(0)
        root = abspath(proj)

        if exists(join(root, STATUS_FILENAME)):
            basedir = root
        else:
            basedir, module = split(root)
        
        if options.bootstrap:
            if exists(join(basedir, STATUS_FILENAME)):
                raise ExistingProjectError(
                    "Project %r cannot be bootstrapped twice" % proj)
            
            if not args:
                raise OptionError('expected the source URI for %r' % proj,
                                  '--bootstrap')
            uri = args.pop(0)
        else:                
            uri = None
            
        if not options.bootstrap and not exists(proj):
            raise UnknownProjectError("Project %r does not exist" % proj)
            
        tailored = TailorizedProject(basedir)
        
        if options.bootstrap:
            if uri and '@' in uri:
                uri, rev = uri.split('@')
            else:
                rev = 'HEAD'
            tailored.bootstrap(options.source_kind, options.target_kind,
                               uri, module, rev)
        elif options.info:
            pass
        else:
            tailored.update()

