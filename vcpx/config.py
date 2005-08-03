# -*- mode: python; coding: utf-8 -*-
# :Progetto: vcpx -- Configuration bits
# :Creato:   sab 30 lug 2005 20:51:28 CEST
# :Autore:   Lele Gaifax <lele@nautilus.homeip.net>
# :Licenza:  GNU General Public License
#

"""
Handle the configuration details.
"""

__docformat__ = 'reStructuredText'

from ConfigParser import SafeConfigParser

class ConfigurationError(Exception):
    """
    Raised on invalid configuration.
    """

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
        self._load()

    def __str__(self):
        return "Project %s at %s:\n\t" % (self.name, self.root) + \
               "\n\t".join(['%s = %s' % (v, getattr(self, v))
                            for v in ('source', 'target', 'state_file')])

    def _load(self):
        """
        Load relevant information from the configuration.
        """

        from os import getcwd

        self.root = self.config.get(self.name, 'root', getcwd())
        self.source = self.__loadRepository('source')
        self.target = self.__loadRepository('target')
        self.state_file = StateFile(self.config.get(self.name, 'state-file'),
                                    self.config)
        before = self.config.getTuple(self.name, 'before-commit')
        try:
            self.before_commit = [self.config.namespace[f] for f in before]
        except KeyError, e:
            raise ConfigurationError('Project %s before-commit references '
                                     'unknown function: '%self.name + str(e))
        after = self.config.getTuple(self.name, 'after-commit')
        try:
            self.after_commit = [self.config.namespace[f] for f in after]
        except KeyError, e:
            raise ConfigurationError('Project %s after-commit references '
                                     'unknown function: '%self.name + str(e))

    def __loadRepository(self, which):
        """
        Given a repository named 'somekind:somename', return a Repository
        (or a subclass of it, if 'SomekindRepository' exists) instance
        that wraps it.
        """

        repname = self.config.get(self.name, which)
        kind = repname[:repname.index(':')]
        klassname = kind.capitalize() + 'Repository'
        try:
            klass = globals()[klassname]
        except KeyError:
            klass = Repository
        return klass(repname, kind, self.config, which)

    def workingDir(self):
        """
        Return a DualWorkingDir instance, ready to work.
        """

        dwd = DualWorkingDir(self.source, self.target)
        dwd.setStateFile(self.state_file)


class Repository(object):
    """
    Collector for the configuration of a single repository.
    """

    def __init__(self, name, kind, config, which):
        self.name = name
        self.kind = kind
        self._load(config, which)

    def __str__(self):
        return "%s repository at %s" % (self.kind, self.repository)

    def _load(self, config, which):
        """
        Load the configuration for this repository.

        The two main and mandatory attributes, ``repository`` and ``module``
        can be specified either on the specific slot in the config file, or
        as ``source-repository`` (or ``target-repository``) in its [DEFAULT]
        section.
        """

        self.repository = config.get(self.name, 'repository') or \
                          config.get(self.name, '%s-repository' % which)
        self.module = config.get(self.name, 'module') or \
                      config.get(self.name, '%s-module' % which)

    def workingDir(self):
        """
        Return an instance of the specific WorkingDir for this kind of
        repository.
        """

        wdname = self.kind.capitalize() + 'WorkingDir'
        modname = 'vcpx.' + self.kind
        try:
            wdmod = __import__(modname, globals(), locals(), [wdname])
            workingdir = getattr(wdmod, wdname)
        except (AttributeError, ImportError):
            raise InvocationError("Unhandled source VCS kind: " + self.kind)
        return workingdir()

class BzrRepository(Repository):
    METADIR = '.bzr'

class CdvRepository(Repository):
    METADIR = '.cdv'

class CvsRepository(Repository):
    METADIR = 'CVS'

class CvspsRepository(CvsRepository):
    pass

class DarcsRepository(Repository):
    METADIR = '_darcs'

class HgRepository(Repository):
    METADIR = '.hg'

class MonotoneRepository(Repository):
    METADIR = 'MT'

    def _load(self, config, which):
        Repository._load(self, config, which)
        self.passphrase = config.get(self.name, 'passphrase')

class SvnRepository(Repository):
    METADIR = '.svn'

    def _load(self, config, which):
        Repository._load(self, config, which)
        self.use_propset = config.get(self.name, 'use-propset', False)

    def workingDir(self):
        wd = Repository.workingDir(self)
        wd.USE_PROPSET = self.use_propset
        return wd


class Config(SafeConfigParser):
    """
    Syntactic sugar around standard ConfigParser, for easier access to
    the configuration. To access any single project use the configuration
    as a dictionary.

    The file may be a full fledged Python script, starting
    with the usual "#!..." notation: in this case, it gets evaluated and
    its documentation becomes the actual configuration, while the functions
    it defines may be referenced by the 'before-commit' and 'after-commit'
    slots.
    """

    def __init__(self, fp, defaults):
        from cStringIO import StringIO

        SafeConfigParser.__init__(self, defaults)
        self.namespace = {}
        if fp.read(2) == '#!':
            fp.seek(0)
            exec fp.read() in globals(), self.namespace
            config = StringIO(self.namespace['__doc__'])
            self.readfp(config)
        else:
            fp.seek(0)
            self.readfp(fp)

    def projects(self):
        """
        Return either the default projects or all the projects in the
        in the configuration.
        """

        defaultp = self.getTuple('DEFAULT', 'projects')
        return defaultp or [s for s in self.sections() if not ':' in s]

    def get(self, section, option, default=None):
        """
        Return the requested option value if present, otherwise the default.
        """
        if self.has_option(section, option):
            return SafeConfigParser.get(self, section, option)
        else:
            return default

    def getTuple(self, section, option, default=None):
        """
        Parse the requested option as a tuple, if its value starts with
        an open bracket, otherwise consider the value a single item
        tuple.
        """

        value = self.get(section, option, default)
        if value:
            if value.startswith('('):
                items = value.strip()[1:-1]
            else:
                items = value
            return [i.strip() for i in items.split(',')]
        else:
            return []

    def __getitem__(self, project):
        return Project(project, self)
