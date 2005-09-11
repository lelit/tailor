# -*- mode: python; coding: utf-8 -*-
# :Progetto: vcpx -- Configuration details about known repository kinds
# :Creato:   gio 04 ago 2005 13:32:55 CEST
# :Autore:   Lele Gaifax <lele@nautilus.homeip.net>
# :Licenza:  GNU General Public License
#

"""
This module holds a simple abstraction of what a repository is for
Tailor purposes.
"""

__docformat__ = 'reStructuredText'

REPO_DESCRIPTION = """\
 Repository: %s
       Kind: %s"""

class Repository(object):
    """
    Collector for the configuration of a single repository.
    """
    METADIR = None
    EXTRA_METADIRS = []
    EXECUTABLE = None

    def __new__(klass, name, project, which):
        """
        Return the right subclass for kind, if it exists.
        """

        kind = name[:name.index(':')]
        subclass = klass
        subclassname = kind.capitalize() + 'Repository'
        if subclassname in globals():
            subclass = globals()[subclassname]
        instance = super(Repository, klass).__new__(subclass, name,
                                                    project, which)
        instance.kind = kind
        return instance

    def __init__(self, name, project, which):
        """
        Initialize a new instance of Repository, with a `name` and
        associated to given `project`; `which` is either "source"
        or "target".
        """

        self.name = name
        self.project = project
        self.which = which
        self._load(project.config)
        self._validateConfiguration()

    def __str__(self):

        s = REPO_DESCRIPTION % (self.repository, self.kind)
        if self.module:
            s += "\n     Module: %s" % self.module
        return s

    def _load(self, config):
        """
        Load the configuration for this repository.

        The two main and mandatory attributes, ``repository`` and ``module``
        can be specified either on the specific slot in the config file, or
        as ``source-repository`` (or ``target-repository``) in its [DEFAULT]
        section.

        If the configuration does not specify a specific ``root-directory``
        take the one from the project.
        """

        from os.path import split, expanduser
        from sys import getdefaultencoding

        self.repository = config.get(self.name, 'repository') or \
                          config.get(self.name, '%s-repository' % self.which)
        if self.repository:
            self.repository = expanduser(self.repository)
        self.module = config.get(self.name, 'module') or \
                      config.get(self.name, '%s-module' % self.which)
        self.rootdir = config.get(self.name, 'root-directory',
                                  vars={'root-directory': self.project.rootdir})
        self.subdir = config.get(self.name, 'subdir',
                                 vars={'subdir': self.project.subdir})
        self.encoding = config.get(self.name, 'encoding')
        if self.encoding is None:
            self.encoding = getdefaultencoding()

    def _validateConfiguration(self):
        """
        Validate the configuration, possibly altering/completing it.
        """

        if self.EXECUTABLE:
            from os import getenv, pathsep
            from os.path import isabs, exists, join
            from vcpx.config import ConfigurationError
            from sys import platform

            if isabs(self.EXECUTABLE):
                ok = exists(self.EXECUTABLE)
            else:
                ok = False
                mswindows = (platform == "win32")
                for path in getenv('PATH').split(pathsep):
                    if exists(join(path, self.EXECUTABLE)):
                        ok = True
                    elif mswindows:
                        for ext in ['.exe', '.bat']:
                            if exists(join(path, self.EXECUTABLE + ext)):
                                self.EXECUTABLE += ext
                                ok = True
                                break
                    if ok:
                        break
            if not ok:
                raise ConfigurationError("The command %r used "
                                         "by %r does not exist in %r!" %
                                         (self.EXECUTABLE, self.name,
                                          getenv('PATH')))

    def log_info(self, what):
        """
        Print some info on the log and, in verbose mode, to stdout as well.
        """

        self.project.log_info(what)

    def log_error(self, what, exc=False):
        """
        Print an error message, possibly with an exception traceback,
        to the log and to stdout as well.
        """

        self.project.log_error(what, exc)

    def workingDir(self):
        """
        Return an instance of the specific WorkingDir for this kind of
        repository.
        """

        from source import InvocationError

        wdname = self.kind.capitalize() + 'WorkingDir'
        modname = 'vcpx.' + self.kind
        try:
            wdmod = __import__(modname, globals(), locals(), [wdname])
            workingdir = getattr(wdmod, wdname)
        except (AttributeError, ImportError):
            raise InvocationError("Unhandled source VCS kind: " + self.kind)

        return workingdir(self)

    def command(self, *args, **kwargs):
        """
        Return the base external command, a sequence suitable to be used
        to init an ExternalCommand instance.

        This return None if the backend uses a different way to execute
        its actions.
        """

        executable = kwargs.get('executable', self.EXECUTABLE)
        if executable:
            cmd = [executable]
            cmd.extend(args)
            return cmd


class ArxRepository(Repository):
    METADIR = '_arx'

    def _load(self, config):
        Repository._load(self, config)
        self.EXECUTABLE = config.get(self.name, 'arx-command', 'arx')


class BzrRepository(Repository):
    METADIR = '.bzr'

    def _load(self, config):
        Repository._load(self, config)
        self.EXECUTABLE = config.get(self.name, 'bzr-command', 'bzr')


class BzrngRepository(Repository):
    METADIR = '.bzr'

    def _load(self, config):
        Repository._load(self, config)
        ppath = config.get(self.name, 'python-path')
        if ppath:
            from sys import path

            if ppath not in path:
                path.insert(0, ppath)


class CdvRepository(Repository):
    METADIR = '.cdv'

    def _load(self, config):
        Repository._load(self, config)
        self.EXECUTABLE = config.get(self.name, 'cdv-command', 'cdv')


class CgRepository(Repository):
    METADIR = '.git'

    def _load(self, config):
        Repository._load(self, config)
        self.EXECUTABLE = config.get(self.name, 'cg-command', 'cg')


class CvsRepository(Repository):
    METADIR = 'CVS'

    def _load(self, config):
        Repository._load(self, config)
        self.EXECUTABLE = config.get(self.name, 'cvs-command', 'cvs')
        self.tag_entries = config.get(self.name, 'tag-entries', 'True')

    def _validateConfiguration(self):
        from os.path import split
        from config import ConfigurationError

        Repository._validateConfiguration(self)

        if not self.module and self.repository:
            self.module = split(self.repository)[1]

        if not self.module:
            raise ConfigurationError("Must specify a repository and maybe "
                                     "a module also")


class CvspsRepository(CvsRepository):
    def command(self, *args, **kwargs):
        if kwargs.get('cvsps', False):
            kwargs['executable'] = self.__cvsps
        return CvsRepository.command(self, *args, **kwargs)

    def _load(self, config):
        CvsRepository._load(self, config)
        self.__cvsps = config.get(self.name, 'cvsps-command', 'cvsps')
        self.tag_entries = config.get(self.name, 'tag-entries', 'True')


class DarcsRepository(Repository):
    METADIR = '_darcs'

    def _load(self, config):
        Repository._load(self, config)
        self.EXECUTABLE = config.get(self.name, 'darcs-command', 'darcs')


class GitRepository(Repository):
    METADIR = '.git'

    def _load(self, config):
        Repository._load(self, config)
        self.EXECUTABLE = config.get(self.name, 'git-command', 'git')


class HgRepository(Repository):
    METADIR = '.hg'

    def _load(self, config):
        Repository._load(self, config)
        self.EXECUTABLE = config.get(self.name, 'hg-command', 'hg')


class HglibRepository(Repository):
    METADIR = '.hg'

    def _load(self, config):
        Repository._load(self, config)
        ppath = config.get(self.name, 'python-path')
        if ppath:
            from sys import path

            if ppath not in path:
                path.insert(0, ppath)


class MonotoneRepository(Repository):
    METADIR = 'MT'

    def _load(self, config):
        Repository._load(self, config)
        self.EXECUTABLE = config.get(self.name, 'monotone-command', 'monotone')
        self.keyid = config.get(self.name, 'keyid')
        self.passphrase = config.get(self.name, 'passphrase')
        self.keyfile = config.get(self.name, 'keyfile')


class SvnRepository(Repository):
    METADIR = '.svn'

    def command(self, *args, **kwargs):
        if kwargs.get('svnadmin', False):
            kwargs['executable'] = self.__svnadmin
        return Repository.command(self, *args, **kwargs)

    def _load(self, config):
        Repository._load(self, config)
        self.EXECUTABLE = config.get(self.name, 'svn-command', 'svn')
        self.__svnadmin = config.get(self.name, 'svnadmin-command', 'svnadmin')
        self.use_propset = config.get(self.name, 'use-propset', False)

    def _validateConfiguration(self):
        from vcpx.config import ConfigurationError

        Repository._validateConfiguration(self)

        if not self.repository:
            raise ConfigurationError("Must specify the root of the "
                                     "Subversion repository used "
                                     "as %s with the option "
                                     "'repository'" % self.which)

        if not self.module:
            raise ConfigurationError("Must specify the path within the "
                                     "Subversion repository as 'module'")

        if not self.module.startswith('/'):
            self.project.log_info("Prepending '/' to module")
            self.module = '/' + self.module

    def workingDir(self):
        wd = Repository.workingDir(self)
        wd.USE_PROPSET = self.use_propset
        return wd


class SvndumpRepository(Repository):

    def _validateConfiguration(self):
        Repository._validateConfiguration(self)

        if self.module and self.module.startswith('/'):
            self.project.log_info("Removing starting '/' from module")
            self.module = self.module[1:]
        if self.module and not self.module.endswith('/'):
            self.module = self.module+'/'


class TlaRepository(Repository):
    METADIR = '{arch}'

    def _load(self, config):
        Repository._load(self, config)
        self.EXECUTABLE = config.get(self.name, 'tla-command', 'tla')
        self.IGNORE_IDS = config.get(self.name, 'ignore-ids', False)
        if self.IGNORE_IDS:
            self.EXTRA_METADIRS = ['.arch-ids']


class BazRepository(TlaRepository):
    def _load(self, config):
        TlaRepository._load(self, config)
        self.EXECUTABLE = config.get(self.name, 'baz-command', 'baz')

    def command(self, *args, **kwargs):
        if args:
            if args[0] == 'tree-lint':
                args[0] = 'lint'
        return TlaRepository.command(self, *args, **kwargs)
