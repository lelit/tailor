#  -*- Python -*- -*- coding: iso-8859-1 -*-
# :Progetto: Bice -- Sync CVS->SVN
# :Sorgente: $HeadURL: http://svn.bice.dyndns.org/progetti/wip/tools/cvsync/sync.py $
# :Creato:   dom 11 apr 2004 12:20:47 CEST
# :Autore:   Lele Gaifax <lele@nautilus.homeip.net>
# :Modifica: $LastChangedDate: 2004-05-21 14:33:02 +0200 (ven, 21 mag 2004) $
# :Fatta da: $LastChangedBy: lele $
# 

"""CVS syncronization machinery.

The performed steps are:

1. Do a ``svn update``

2. Do a ``cvs update``.  From the log desume what was added, merged,
   removed and eventually the conflicts.
  
3. For each touched entry, do a ``cvs log`` on the revision range and
   collect the date, author and commit message for each one.

4. Perform the needed ``svn add``/``svn remove`` commands.

5. Do a final commit, with the complessive ChangeLog.
"""

__docformat__ = 'reStructuredText'

from optparse import OptionParser, make_option
from cvsync.cvs import CvsWorkingDir, CvsUpdateError, CvsLogError

LOG_MESSAGE_FILE_NAME = 'cvsync.log.message'
"""The filename where the complessive changelog will be written."""

ERR_MESSAGE_FILE_NAME = 'cvsync.err.message'
"""The filename where the output of the ``cvs up`` will be written."""

CHANGESET_CACHE = 'cvsync.cache'
"""The cache file used in the process.  It's a `shelve` archive."""

PRE_COMMIT_PROMPT = """\
I'm about to commit. You can suspend (Ctrl-Z) the session
to inspect the working copy status or abort (Ctrl-C) it."""

CONFIRM_REPLAY_PROMPT = """\
Replaying a previous CVS update log found in "%s", maybe left
after some kind of error.  I will NOT rerun ``svn update``.
Hit Ctrl-C now if that is not what you intended, and remove the file."""

class AbstractSyncronizer(object):
    """Perform the needed steps to syncronize CVS world with SVN."""
    
    def __init__(self, root):
        """Initialize a Syncronizer."""
        
        self.root = root
        """The directory under both CVS and SVN version control."""
        
        self.source_wc = CvsWorkingDir(self.root)
        """The CVS point-of-view."""

        self.target_wc = None
        """The target VC engine."""
        
        self.setTargetWC()

    def setTargetWC(self):
        """The target VC engine."""

        raise "This MUST be overridden by subclasses."        

    def __call__(self, options):
        """Do the mentioned steps :).

           If there is a previous error log, load that one and perform
           the subsequents steps without """

        from os.path import exists
        from os import unlink

        prevlog = None
        if not options.dry_run:
            if exists(ERR_MESSAGE_FILE_NAME):
                try:
                    raw_input(CONFIRM_REPLAY_PROMPT % ERR_MESSAGE_FILE_NAME)
                except KeyboardInterrupt:
                    print "\nReasonable choice!"
                    return
                
                prevlog = open(ERR_MESSAGE_FILE_NAME)
                options.svn_update = False
                
            # Bring the svnwc up-to-date
            if options.svn_update:
                self.target_wc.update()
            
        # Do a cvs update and collect the changes
        try:
            changes = self.source_wc.update(options=options,
                                            prevlog=prevlog)
        except CvsUpdateError, e:
            print "Gasp!  Underlying CVS update command failed: ", e
            return
        except CvsLogError, e:
            print "Gasp!  Underlying CVS log command failed: ", e
            print "I left the CVS update log in %s." % ERR_MESSAGE_FILE_NAME
            print "If not removed, the next run will use that file, and won't"
            print "reexecute the CVS update command."
            return
        except:
            print "Sorry, something went wrong with the CVS update phase :-("
            print "I left the CVS update log in %s." % ERR_MESSAGE_FILE_NAME
            if not options.keep_cache and exists(CHANGESET_CACHE):
                unlink(CHANGESET_CACHE)
            raise

        print
        if not changes:
            print "No changes. Good!"
            if not options.keep_cache and exists(CHANGESET_CACHE):
                unlink(CHANGESET_CACHE)
            if exists(ERR_MESSAGE_FILE_NAME):
                unlink(ERR_MESSAGE_FILE_NAME)
            return
        
        if options.dry_run:
            if not options.debug:
                if not options.keep_cache and exists(CHANGESET_CACHE):
                    unlink(CHANGESET_CACHE)
                if exists(ERR_MESSAGE_FILE_NAME):
                    unlink(ERR_MESSAGE_FILE_NAME)
            else:
                print "I left the logs and the cache, for debug."
                
        if self.source_wc.conflicts or options.dry_run:
            if self.source_wc.conflicts:
                print "CAUTION: the CVS update reported a few conflicts:"
                print ' -', '\n - '.join(self.source_wc.conflicts)
                print
                
            if self.source_wc.obstructing:
                print "Some of the conflicts are due to files that are already"
                print "there, but are not under revision control, yet:"

                print ' -', '\n -'.join(self.source_wc.obstructing)
                print
                
                print "You should remove them, otherwise CVS will refuse to update them.\n"
                
            if self.source_wc.added:
                print "Some files were added and need to be registered with:"
                print "  svn add %s" % ' '.join(self.source_wc.added)
            if self.source_wc.removed:
                print "You should unregister removed files with:"
                print "  svn remove %s" % ' '.join(self.source_wc.removed)

            if options.changelog:
                if not options.dry_run:
                    logname = LOG_MESSAGE_FILE_NAME
                    changelog = open(logname, 'w')
                    changelog.write(str(changes))
                    changelog.close()

                    print "I left the ChangeLog in %s." % logname
                    print "Once solved the conflicts, issue:"
                    print "  svn ci --file %s" % logname
                else:
                    print changes
        else:
            added, removed = self.source_wc.compareDirectories()
            print
            
            added.extend(self.source_wc.added)
            removed.extend(self.source_wc.removed)
            
            for a in added:
                self.target_wc.add(a)

            for r in removed:
                self.target_wc.remove(r)

            if options.commit:
                try:
                    raw_input(PRE_COMMIT_PROMPT)

                    status = self.target_wc.commit(
                        options.message or "Upstream changes", changes)

                    if not status:
                        if not options.debug:
                            if exists(ERR_MESSAGE_FILE_NAME):
                                unlink(ERR_MESSAGE_FILE_NAME)
                            if exists(CHANGESET_CACHE):
                                unlink(CHANGESET_CACHE)
                        else:
                            print "I left the logs and the cache, for debug."
                    if options.changelog:
                        print "I left the ChangeLog in %s." % logname
                except KeyboardInterrupt:
                    print "INTERRUPTED BY THE USER!"
            elif options.changelog:
                print "Later, you may use the ChangeLog I wrote with:"
                print "  svn ci --file %s" % logname


class SyncronizerForSubversion(AbstractSyncronizer):
    """Specialize the syncronizer for Subversion."""

    def setTargetWC(self):
        from cvsync.svn import SvnWorkingDir
        
        self.target_wc = SvnWorkingDir(self.root)


class SyncronizerForDarcs(AbstractSyncronizer):
    """Specialize the syncronizer for Darcs."""
    
    def setTargetWC(self):
        from cvsync.darcs import DarcsWorkingDir
        
        self.target_wc = DarcsWorkingDir(self.root)


OPTIONS = [
    make_option("-d", "--dry-run", dest="dry_run",
                action="store_true", default=False,
                help="Do not perform anything harmful, just show what "
                     "could happen.  The collected changelog, if any, "
                     "will be echoed on stdout too."),
    make_option("-k", "--keep-cache", dest="keep_cache",
                action="store_true", default=False,
                help="Do not delete the cache in dry-run mode. "
                     "NOTE: this is not the wisest things to do, if "
                     "you are not going to execute a normal run soon."),
    make_option("-t", "--cvs-tag", dest="cvstag", default=None,
                help="Do a ``cvs up`` against given tag instead of HEAD."),
    make_option("-n", "--no-changelog", dest="changelog",
                action="store_false", default=True,
                help="Do not build a ChangeLog for the commit."),
    make_option("-m", "--message",
                default="",
                help="Commit message, when using --no-changelog."),
    make_option("--darcs", action="store_true", default=False,
                help="Target is darcs instead of subversion."),
    make_option("-u", "--no-svn-update", dest="svn_update",
                action="store_false", default=True,
                help="Do not perform the initial ``svn update``."),
    make_option("-c", "--no-commit", dest="commit",
                action="store_false", default=True,
                help="Do not perform the commit phase."),
    make_option("-s", "--use-ssh", dest="use_ssh",
                action="store_true", default=False,
                help="Use SSH for the CVS commands."),
    make_option("-D", "--debug", dest="debug",
                action="store_true", default=False,
                help="Do not swallow unrecognised CVS update messages, and "
                     "keep the ``cvs update`` log and the cache."),
]    

def main():
    """Script entry point.

       Parse the command line options and arguments, and for each
       specified working copy directory (the current working directory
       by default) execute the syncronization steps."""
    
    from os import getcwd, chdir, environ
    from os.path import abspath, join   
    
    parser = OptionParser(usage='%prog [options] [working_dir ...]',
                          option_list=OPTIONS)
    
    options, args = parser.parse_args()
    
    if len(args) == 0:
        args.append(getcwd())

    if options.use_ssh:
        print "export CVS_RSH=ssh"
        environ['CVS_RSH'] = 'ssh'

    if options.darcs:
        Syncronizer = SyncronizerForDarcs
    else:
        Syncronizer = SyncronizerForSubversion
        
    base = getcwd()
    for wc in args:
        wc = abspath(wc)
        print "Working on '%s':" % wc
        chdir(wc)
        sync = Syncronizer(wc)
        sync(options)
        chdir(base)
