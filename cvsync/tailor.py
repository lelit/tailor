#! /usr/bin/python
# -*- mode: Python; coding: utf-8 -*-
# :Progetto: Bice -- Sync SVN->SVN
# :Sorgente: $HeadURL: http://svn.bice.dyndns.org/progetti/wip/tools/cvsync/tailor.py $
# :Creato:   lun 03 mag 2004 15:31:34 CEST
# :Autore:   Lele Gaifax <lele@nautilus.homeip.net>
# :Modifica: $LastChangedDate: 2004-05-15 01:29:52 +0200 (sab, 15 mag 2004) $
# :Fatta da: $LastChangedBy: lele $
#

"""Third-party product tailorization machinery.

The performed steps are:

1. Do a ``svn update``

2. In `bootstrap` mode, copy the upstream product and register its URI
   and revision in the properties `bice:upstream-uri` and
   `bice:upstream-rev`.

3. Perform a ``svn merge`` of the upstream changes made since last
   update, updating the `bice:upstream-rev` property.

4. Do a final commit.
"""

__docformat__ = 'reStructuredText'

from optparse import OptionParser, OptionError, OptionGroup, make_option
from cvsync.svn import SvnWorkingDir, getHeadRevision
from cvsync.darcs import DarcsWorkingDir

URI_PROPNAME = "bice:upstream-uri"
"""The name of the svn property used to store the upstream URI of a tree."""

REV_PROPNAME = "bice:upstream-rev"
"""The name of the svn property used to store the upstream revision."""

PRE_COMMIT_PROMPT = """\
I'm about to commit. You can suspend (Ctrl-Z) the session
to inspect the working copy status, or cancel (Ctrl-C) it."""

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
    
class Tailorizer(object):
    """
    Perform the needed steps to merge upstream changes.
    """

    def __init__(self, project, uri=None):
        """
        Initialize a new instance.

        :Arguments:

          `project`
            The directory where the tailorized project (will) live.

          `uri`
            If not None, it's the source URI from where the project
            should be copied from. 
        """

        from os.path import abspath

        self.project = abspath(project)
        """The directory that contains the project."""
        
        self.uri = uri
        """The bootstrap URI, if any."""
        
        self.wc = SvnWorkingDir(self.project)
        """The working copy."""
        
    def mergeAndCommit(self, options):
        """
        Execute the bootstrap/merge and eventually a commit.
        """

        if options.bootstrap:
            self.bootstrap(options)
            do_commit = True
        else:
            ## TODO: handle the --darcs option, executing a svn log
            ##       and replaying the changeset into darcs
            
            if options.svn_update and not options.dry_run:
                self.wc.update()
                
            try:
                do_commit = self.merge(options)
            except ProjectNotTailored, e:
                print e
                return           

        if not options.dry_run:
            if do_commit:
                if options.commit:
                    if options.darcs:
                        self.registerUnderDarcs(patchname, options.message)
                    else:
                        try:
                            print
                            raw_input(PRE_COMMIT_PROMPT)

                            message = options.message or options.auto_message
                            status = self.wc.commit(message=message)
                        except KeyboardInterrupt:
                            print "INTERRUPTED BY THE USER!"
            else:
                print "No changes. Good!"

    def showUpstreamInfo(self):
        """
        Show the ancestry information of this branch.

        The output is deliberately very terse, such that it can be used
        as `--bootstrap` option argument.
        """

        from os.path import commonprefix
        from os import getcwd
        
        try:
            uri, rev = self.getUpstreamInfo()
        except ProjectNotTailored, e:
            print e
        else:
            common = commonprefix([self.project, getcwd()])
            
            print self.project[len(common)+1:], "%s@%s" % (uri, rev)

    def updateUpstreamInfo(self, uri=None, rev=None):
        """
        Update the properties that carry the upstream information.
        """

        if uri and '@' in uri:
            uri, rev = uri.split('@')
        if uri: self.wc.setProperty(self.project, URI_PROPNAME, uri)
        if rev: self.wc.setProperty(self.project, REV_PROPNAME, rev)

    def getUpstreamInfo(self):
        """
        Extract the upstream information from the properties.
        """

        uri = self.wc.getProperty(self.project, URI_PROPNAME)
        rev = self.wc.getProperty(self.project, REV_PROPNAME)

        if not uri:
            raise ProjectNotTailored("%s is not a tailored project, skipping" %
                                     self.project)
        
        return uri, rev

    def setUpstreamInfo(self):
        """
        Just write the properties with the ancestry information given
        by the URI.
        """

        self.updateUpstreamInfo(self.uri)
        
    def bootstrap(self, options):
        """
        Copy the upstream product and update the properties with
        the upstream information.

        If `options.darcs` is true, do a checkout instead of a copy,
        and record the whole subtree under darcs.
        """

        if options.dry_run:
            return
        
        if options.darcs:
            info = self.wc.checkout(self.uri)
            uri = info['URL']
            rev = info['Revision']
        else:
            info = self.wc.copy(self.uri)
            uri = info['Copied From URL']
            rev = info['Copied From Rev']
            self.updateUpstreamInfo(uri=uri, rev=rev)

        if not options.message:
            options.auto_message = "Tailorization of %s, " \
                                   "from revision %s" % (uri, rev)

    def registerUnderDarcs(self, patchname, logmessage):
        """
        Register the checked out tree under darcs.
        """

        dwc = DarcsWorkingDir(self.project)
        dwc.initialize()
        dwc.record(patchname, logmessage)
        
    def diff(self):
        """
        Execute a ``svn diff`` against the upstream sources.
        """

        uri, rev = self.getUpstreamInfo()
        self.wc.diff(uri, rev)
        
    def merge(self, options):
        """
        Fetch the upstream info and perform a merge of the eventual changes,
        then update the properties.
        """

        from os import chdir

        uri, rev = self.getUpstreamInfo()
        
        chdir(self.project)
        head = getHeadRevision(uri, rev)
        if rev <> head:
            merged = self.wc.merge(uri, rev, head,
                                   self.project, dry_run=options.dry_run)
            if merged:
                self.updateUpstreamInfo(rev=head)

                if not options.message:
                    options.auto_message = "Merged upstream changes " \
                                           "(revisions %s:%s)" % (rev, head)
        else:
            merged = False
            
        return merged
        
OPTIONS = [
    make_option("-d", "--dry-run", dest="dry_run",
                action="store_true", default=False,
                help="Do not perform anything harmful, just show what "
                     "could happen.  The collected changelog, if any, "
                     "will be echoed on stdout too."),
    make_option("--darcs", action="store_true", default=False,
                help="Use a darcs repository for the tailorization."),
    make_option("-m", "--message",
                default="", # autogenerated
                help="Commit message, when using --no-changelog."),
    make_option("-u", "--no-svn-update", dest="svn_update",
                action="store_false", default=True,
                help="Do not perform the initial ``svn update``."),
    make_option("-c", "--no-commit", dest="commit",
                action="store_false", default=True,
                help="Do not perform the commit phase."),
    make_option("-D", "--debug", dest="debug",
                action="store_true", default=False),
]    

ACTIONS = [
    make_option("-b", "--bootstrap", action="store_true", default=False,
                help="Bootstrap mode, that is the initial copy of the "
                     "upstream tree, given as an URI possibly followed "
                     "by a revision."),
    make_option("--info",
                action="store_true",
                help="Just show ancestry information."),
    make_option("--diff",
                action="store_true",
                help="Show what's changed from upstream sources."),
    make_option("--set-ancestry",
                action="store_true",
                help="Reset ancestry information of the project.  This is "
                     "similar to --bootstrap, except that the copy is not "
                     "performed."),
]

def main():
    """Script entry point.

       Parse the command line options and arguments, and for each
       specified working copy directory (the current working directory
       by default) execute the tailorization steps."""
    
    from os import getcwd, chdir
    from os.path import abspath, exists
    from shwrap import SystemCommand
    
    parser = OptionParser(usage='%prog [options] [proj [URI[@revision]]]...',
                          option_list=OPTIONS)
    actions = OptionGroup(parser, "Other actions")
    actions.add_options(ACTIONS)
    parser.add_option_group(actions)
    
    options, args = parser.parse_args()
    
    base = getcwd()
    
    if len(args) == 0:
        args.append(base)
       
    while args:
        chdir(base)
        
        proj = args.pop(0)
        if options.bootstrap or options.set_ancestry:
            if options.bootstrap and exists(proj):
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
            
        proj = abspath(proj)

        SystemCommand.VERBOSE = options.debug

        tizer = Tailorizer(proj, uri)
        if options.info:
            tizer.showUpstreamInfo()
        elif options.diff:
            tizer.diff()
        elif options.set_ancestry:
            tizer.setUpstreamInfo()
        else:
            print "Updating '%s':" % proj
            tizer.mergeAndCommit(options)
            print
