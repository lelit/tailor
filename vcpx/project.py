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

from vcpx.config import ConfigurationError
from vcpx.statefile import StateFile

class UnknownProjectError(Exception):
    "Project does not exist"


class Project(object):
    """
    This class collects the information related to a single project, such
    as its source and target repositories and state file. All the setup
    comes from a section in the configuration file (.ini-like format) with
    the same name as the project.

    Mandatory options are:

    root-directory
      This is where all the fun will happen: this directory will contain
      the source and the target working copy, and usually the state and
      the log file. It support the conventional "~user" to indicate user's
      home directory.

    subdir
      This is the subdirectory, relative to the root-directory, where
      tailor will extract the source working copy. It may be '.' for some
      backend kinds.

    state-file
      Name of the state file needed to store tailor last activity.

    source
      The source repository: a repository name is something like
      "darcs:somename", that will be loaded from the homonymous section
      in the configuration.

    target
      The counterpart of `source`, the repository that will receive the
      changes coming from there.

    Non mandatory options:

    before-commit
      This is a function name, or a sequence of function names enclosed
      by brackets, that will be executed on each changeset just before
      it get replayed on the target system: this may be used to perform
      any kind of alteration on the content of the changeset, or to skip
      some of them.

    after-commit
      This is a function name, or a sequence of function names enclosed
      by brackets, that will be executed on each changeset just after
      the commit on the target system: this may be used for example to
      create a tag.

    start-revision
      This identifies from when tailor should start the migration. It can
      be either ``INITIAL``, to indicate the start of the history, or
      ``HEAD`` to indicate the current latest changeset, or a backend
      specific way of indicate a particular revision/tag in the history.
    """

    def __init__(self, name, config):
        if not config.has_section(name):
            raise UnknownProjectError("'%s' is not a known project" % name)

        self.config = config
        self.name = name
        self.dwd = None
        self._load()

    def __str__(self):
        return "Project %s at %s:\n\t" % (self.name, self.rootdir) + \
               "\n\t".join(['%s = %s' % (v, getattr(self, v))
                            for v in ('source', 'target', 'state_file')])

    def _load(self):
        """
        Load relevant information from the configuration.
        """

        from os import getcwd, makedirs
        from os.path import join, exists, expanduser
        import logging

        self.rootdir = self.config.get(self.name, 'root-directory', getcwd())
        if not exists(self.rootdir):
            makedirs(self.rootdir)
        self.subdir = self.config.get(self.name, 'subdir')
        if not self.subdir:
            self.subdir = '.'

        self.source = self.__loadRepository('source')
        self.target = self.__loadRepository('target')
        sfpath = join(self.rootdir,
                      expanduser(self.config.get(self.name,
                                                 'state-file',
                                                 self.name + '.state')))
        self.state_file = StateFile(sfpath, self.config)

        before = self.config.getTuple(self.name, 'before-commit')
        try:
            self.before_commit = [self.config.namespace[f] for f in before]
        except KeyError, e:
            raise ConfigurationError('Project "%s" before-commit references '
                                     'unknown function: %s' %
                                     (self.name, str(e)))

        after = self.config.getTuple(self.name, 'after-commit')
        try:
            self.after_commit = [self.config.namespace[f] for f in after]
        except KeyError, e:
            raise ConfigurationError('Project "%s" after-commit references '
                                     'unknown function: %s' %
                                     (self.name, str(e)))

        self.verbose = self.config.get(self.name, 'verbose', False)
        self.logger = logging.getLogger('tailor.%s' % self.name)
        self.logfile = join(self.rootdir,
                            expanduser(self.config.get(self.name, 'logfile',
                                                       'tailor.log')))
        hdlr = logging.FileHandler(self.logfile)
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
        return klass(repname, kind, self, which)

    def exists(self):
        """
        Return True if the project exists, False otherwise.
        """

        return self.state_file.lastAppliedChangeset() is not None

    def workingDir(self):
        """
        Return a DualWorkingDir instance, ready to work.
        """

        from dualwd import DualWorkingDir

        if self.dwd is None:
            self.dwd = DualWorkingDir(self.source, self.target)
            self.dwd.setStateFile(self.state_file)
            self.dwd.setLogfile(self.logfile)
        return self.dwd
