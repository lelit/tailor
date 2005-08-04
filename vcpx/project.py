# -*- mode: python; coding: utf-8 -*-
# :Progetto: vcpx -- Project details
# :Creato:   gio 04 ago 2005 13:07:31 CEST
# :Autore:   Lele Gaifax <lele@nautilus.homeip.net>
# :Licenza:  GNU General Public License
#

"""
This module implements a higher level of operations, with a Project
class that knows how to drive the two main activities, bootstrap and
update, layering on top of DualWorkingDir.
"""

__docformat__ = 'reStructuredText'

class StateFile(object):
    """
    State file that stores current revision and pending changesets.
    """
    def __init__(self, fname, config):
        self.filename = fname

    def __str__(self):
        return self.filename

    def load(self):
        """
        Read the source revision and pending changesets from the state file.
        """

        from cPickle import load

        try:
            sf = open(self.filename)
            revision, changesets = load(sf)
            sf.close()
        except IOError:
            revision = None
            changesets = None

        return revision, changesets

    def write(self, revision, changesets):
        """
        Write current source revision and pending changesets in the state file.
        """

        from cPickle import dump

        sf = open(self.filename, 'w')
        dump((revision, changesets), sf)
        sf.close()


class Project(object):
    """
    This class collects the information related to a single project, such
    as its source and target repositories and state file.
    """

    def __init__(self, name, config):
        self.config = config
        self.name = name
        self.dwd = None
        self._load()

    def __str__(self):
        return "Project %s at %s:\n\t" % (self.name, self.root) + \
               "\n\t".join(['%s = %s' % (v, getattr(self, v))
                            for v in ('source', 'target', 'state_file')])

    def _load(self):
        """
        Load relevant information from the configuration.
        """

        from os import getcwd, makedirs
        from os.path import join, exists
        import logging

        self.root = self.config.get(self.name, 'root', getcwd())
        if not exists(self.root):
            makedirs(self.root)
        self.subdir = self.config.get(self.name, 'subdir')
        if not self.subdir:
            self.subdir = '.'

        self.source = self.__loadRepository('source')
        self.target = self.__loadRepository('target')
        self.state_file = StateFile(self.config.get(self.name, 'state-file'),
                                    self.config)

        before = self.config.getTuple(self.name, 'before-commit')
        try:
            self.before_commit = [self.config.namespace[f] for f in before]
        except KeyError, e:
            raise ConfigurationError('Project %s before-commit references '
                                     'unknown function: %s' %
                                     (self.name, str(e)))

        after = self.config.getTuple(self.name, 'after-commit')
        try:
            self.after_commit = [self.config.namespace[f] for f in after]
        except KeyError, e:
            raise ConfigurationError('Project %s after-commit references '
                                     'unknown function: %s' %
                                     (self.name, str(e)))

        self.verbose = self.config.get(self.name, 'verbose', False)
        self.single_commit = self.config.get(self.name, 'single-commit', False)
        self.logger = logging.getLogger('tailor.%s' % self.name)
        logfile = self.config.get(self.name, 'logfile', 'tailor.log')
        hdlr = logging.FileHandler(join(self.root, logfile))
        formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(message)s')
        hdlr.setFormatter(formatter)
        self.logger.addHandler(hdlr)
        self.logger.setLevel(logging.INFO)

    def log_info(self, what):
        """
        Print some info on the log and, in verbose mode, to stdout as well.
        """

        if self.logger:
            self.logger.info(what)

        if self.verbose:
            print what

    def log_error(self, what, exc=False):
        """
        Print an error message, possibly with an exception traceback,
        to the log and to stdout as well.
        """

        if self.logger:
            if exc:
                self.logger.exception(what)
            else:
                self.logger.error(what)

        print "Error:", what,
        if exc:
            from sys import exc_info

            ei = exc_info()
            print ' -- Exception %s: %s' % ei[0:2]
        else:
            print

    def __loadRepository(self, which):
        """
        Given a repository named 'somekind:somename', return a Repository
        (or a subclass of it, if 'SomekindRepository' exists) instance
        that wraps it.
        """

        import repository

        repname = self.config.get(self.name, which)
        kind = repname[:repname.index(':')]
        klassname = kind.capitalize() + 'Repository'
        try:
            klass = getattr(repository, klassname)
        except AttributeError:
            klass = repository.Repository
        return klass(repname, kind, self.config, which)

    def workingDir(self):
        """
        Return a DualWorkingDir instance, ready to work.
        """

        from dualwd import DualWorkingDir

        if self.dwd is None:
            self.dwd = DualWorkingDir(self.source, self.target)
            self.dwd.setStateFile(self.state_file)
        return self.dwd

    def prepareWorkingDirectory(self):
        """
        Prepare the working directory before the bootstrap.
        """

        dwd = self.workingDir()
        dwd.prepareWorkingDirectory(self.root,
                                    self.target.repository,
                                    self.target.module)

    def checkoutUpstreamRevision(self):
        """
        Checkout a working copy from the upstream repository and import
        it in the target system.
        """

        dwd = self.workingDir()
        revision = self.config.get(self.name, 'start-revision', 'INITIAL')
        actual = dwd.checkoutUpstreamRevision(self.root,
                                            self.source.repository,
                                            self.source.module, revision,
                                            subdir=self.subdir,
                                            logger=self.logger)
        dwd.initializeNewWorkingDir(self.root, self.source.repository,
                                    self.source.module, self.subdir,
                                    actual, revision=='INITIAL')

    def _applyable(self, root, changeset):
        """
        Print the changeset being applied.
        """

        if self.verbose:
            print "Changeset %s:" % changeset.revision
            try:
                print changeset.log
            except UnicodeEncodeError:
                print ">>> Non-printable changelog <<<"

        return True

    def _applied(self, root, changeset):
        """
        Save current status.
        """

        if self.verbose:
            print

    def applyPendingChangesets(self):
        """
        Apply pending changesets, eventually fetching latest from upstream.
        """

        from os.path import join

        wdir = join(self.root, self.subdir)
        dwd = self.workingDir()
        try:
            pendings = dwd.getPendingChangesets(wdir,
                                                self.source.repository,
                                                self.source.module)
        except KeyboardInterrupt:
            self.log_info("Leaving '%s' unchanged, stopped by user" % self.name)
            return
        except:
            self.log_error("Unable to get changes for '%s'" % self.name, True)
            raise

        nchanges = len(pendings)
        if nchanges:
            if self.verbose:
                print "Applying %d upstream changesets" % nchanges

            try:
                last, conflicts = dwd.applyPendingChangesets(
                    wdir, self.source.module,
                    applyable=self._applyable, applied=self._applied,
                    logger=self.logger, delayed_commit=self.single_commit)
            except:
                self.log_error('Upstream change application failed', True)
                raise

            if last:
                if single_commit:
                    dwd.commitDelayedChangesets(proj, concatenate_logs)

                self.log_info("Update completed, now at revision '%s'" %
                              self.upstream_revision)
        else:
            self.log_info("Update completed with no upstream changes")
