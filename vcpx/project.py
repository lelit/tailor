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

from cPickle import load, dump

class StateFile(object):
    """
    State file that stores current revision and pending changesets.

    It behaves as an iterator, and source backends loop over not yet
    applied changesets, calling .applied() after each one: that writes
    the applied changeset in a `journal` file, much more atomic than
    rewriting the whole archive each time.

    When the source backend finishes it's job, either because there
    are no more pending changeset or stopped by an error, it calls
    .finalize(), that in presence of a journal file adjust the
    archive filtering out already applied changesets.

    Should an hard error prevent .finalize() call, it will happen
    automatically next time the state file is loaded.
    """

    def __init__(self, fname, config):
        self.filename = fname
        self.archive = None
        self.last_applied = None
        self.current = None
        self.queuelen = 0

    def _load(self):
        """
        Open the pickle file and load the first two items, respectively
        the revision and the number of pending changesets.
        """

        # Take care of the journal file, if present.
        self.finalize()

        self.current = None
        try:
            self.archive = open(self.filename)
            self.last_applied = load(self.archive)
            self.queuelen = load(self.archive)
        except IOError:
            self.archive = None
            self.last_applied = None
            self.queuelen = 0

    def _write(self, changesets):
        """
        Write the state file.
        """

        sf = open(self.filename, 'w')
        dump(self.last_applied, sf)
        dump(len(changesets), sf)
        for cs in changesets:
            dump(cs, sf)
        sf.close()

    def __str__(self):
        return self.filename

    def __iter__(self):
        return self

    def next(self):
        if not self.archive:
            raise StopIteration
        try:
            self.current = load(self.archive)
        except EOFError:
            self.archive.close()
            self.archive = None
            raise StopIteration
        self.queuelen -= 1
        return self.current

    def __len__(self):
        if self.archive is None:
            self._load()
        return self.queuelen

    def applied(self, current=None):
        """
        Write the applied changeset to the journal file.
        """

        self.last_applied = current or self.current
        journal = open(self.filename + '.journal', 'w')
        dump(self.last_applied, journal)
        journal.close()

    def finalize(self):
        """
        If there is a journal file, adjust the archive accordingly,
        dropping already applied changesets.
        """

        from os.path import exists
        from os import unlink, rename

        if self.archive is not None:
            self.archive.close()
            self.archive = None

        if not exists(self.filename + '.journal'):
            return

        # Load last applied changeset from the journal
        journal = open(self.filename + '.journal')
        last_applied = load(journal)
        journal.close()

        # If there is an actual archive (ie, this is not bootstrap time)
        # load the changesets from there, skipping the changesets until
        # the last_applied one, then transfer the remaining to the new
        # archive.
        if exists(self.filename):
            old = open(self.filename)
            load(old) # last applied
            queuelen = load(old)
            cs = load(old)

            # Skip already applied changesets
            while cs <> last_applied:
                queuelen -= 1
                cs = load(old)

            sf = open(self.filename + '.new', 'w')
            dump(last_applied, sf)
            dump(queuelen-1, sf)

            while True:
                try:
                    cs = load(old)
                except EOFError:
                    break
                dump(cs, sf)
            sf.close()
            old.close()
            unlink(self.filename)
            rename(sf.name, self.filename)
        else:
            sf = open(self.filename, 'w')
            dump(last_applied, sf)
            dump(0, sf)
            sf.close()

        unlink(journal.name)

    def lastAppliedChangeset(self):
        """
        Return the last applied changeset, if any, None otherwise.
        """

        if self.archive is None:
            self._load()
        return self.last_applied

    def setPendingChangesets(self, changesets):
        """
        Write pending changesets to the state file.
        """

        if self.archive is not None:
            self.archive.close()
            self.archive = None

        self._write(changesets)
        self._load()


class UnknownProjectError(Exception):
    "Project does not exist"


class Project(object):
    """
    This class collects the information related to a single project, such
    as its source and target repositories and state file.
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
                      expanduser(self.config.get(self.name, 'state-file')))
        self.state_file = StateFile(sfpath, self.config)

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
