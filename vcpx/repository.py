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

        from logging import getLogger
        from weakref import ref

        self.name = name
        self.which = which
        self.projectref = ref(project)
        self._load(project)
        self.log = getLogger('tailor.vcpx.%s.%s' % (self.__class__.__name__,
                                                    which))
        self._validateConfiguration()

    def __str__(self):

        s = REPO_DESCRIPTION % (self.repository, self.kind)
        if self.module:
            s += "\n     Module: %s" % self.module
        return s

    def _load(self, project):
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
        from locale import getpreferredencoding

        cget = project.config.get
        self.repository = cget(self.name, 'repository') or \
                          cget(self.name, '%s-repository' % self.which)
        if self.repository:
            self.repository = expanduser(self.repository)
        self.module = cget(self.name, 'module') or \
                      cget(self.name, '%s-module' % self.which)
        self.rootdir = cget(self.name, 'root-directory',
                            vars={'root-directory': project.rootdir})
        self.subdir = cget(self.name, 'subdir',
                           vars={'subdir': project.subdir})
        self.delay_before_apply = cget(self.name, 'delay-before-apply')
        if self.delay_before_apply:
            self.delay_before_apply = float(self.delay_before_apply)
        self.encoding = cget(self.name, 'encoding')
        if not self.encoding:
            self.encoding = getpreferredencoding()
        self.encoding_errors_policy = cget(self.name,
                                           'encoding-errors-policy', 'strict')

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
                self.log.critical("Cannot find external command %r",
                                  self.EXECUTABLE)
                raise ConfigurationError("The command %r used "
                                         "by %r does not exist in %r!" %
                                         (self.EXECUTABLE, self.name,
                                          getenv('PATH')))

    def encode(self, s):
        """
        If `s` is an unicode object, encode it in the the right charset.
        Return a standard Python string.
        """

        if isinstance(s, unicode):
            return s.encode(self.encoding, self.encoding_errors_policy)
        else:
            return s

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
        except SyntaxError, e:
            self.log.exception("Cannot import %r from %r", wdname, modname)
            raise InvocationError("Cannot import %r: %s" % (wdname, e))
        except (AttributeError, ImportError), e:
            self.log.critical("Cannot import %r from %r", wdname, modname)
            if self.kind == 'bzr':
                from sys import version_info
                if version_info < (2,4):
                    self.log.warning("Bazaar-NG backend requires Python 2.4")
            raise InvocationError("%r is not a known VCS kind: %s" %
                                  (self.kind, e))

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

    def _load(self, project):
        Repository._load(self, project)
        self.EXECUTABLE = project.config.get(self.name, 'arx-command', 'arx')


class BzrRepository(Repository):
    METADIR = '.bzr'

    def _load(self, project):
        Repository._load(self, project)
        ppath = project.config.get(self.name, 'python-path')
        if ppath:
            from sys import path

            if ppath not in path:
                path.insert(0, ppath)


class CdvRepository(Repository):
    METADIR = '.cdv'

    def _load(self, project):
        Repository._load(self, project)
        self.EXECUTABLE = project.config.get(self.name, 'cdv-command', 'cdv')


class CgRepository(Repository):
    METADIR = '.git'

    def _load(self, project):
        Repository._load(self, project)
        self.EXECUTABLE = project.config.get(self.name, 'cg-command', 'cg')


class CvsRepository(Repository):
    METADIR = 'CVS'

    def _load(self, project):
        Repository._load(self, project)
        self.EXECUTABLE = project.config.get(self.name, 'cvs-command', 'cvs')
        self.tag_entries = project.config.get(self.name, 'tag-entries', 'True')
        self.freeze_keywords = project.config.get(self.name, 'freeze-keywords', 'False')

    def _validateConfiguration(self):
        from os.path import split
        from config import ConfigurationError

        Repository._validateConfiguration(self)

        if not self.module and self.repository:
            self.module = split(self.repository)[1]

        if not self.module:
            self.log.critical('Missing module information in %r', self.name)
            raise ConfigurationError("Must specify a repository and maybe "
                                     "a module also")

        if self.module.endswith('/'):
            self.log.debug("Removing final slash from %r in %r",
                           self.module, self.name)
            self.module = self.module.rstrip('/')


class CvspsRepository(CvsRepository):
    def command(self, *args, **kwargs):
        if kwargs.get('cvsps', False):
            kwargs['executable'] = self.__cvsps
        return CvsRepository.command(self, *args, **kwargs)

    def _load(self, project):
        CvsRepository._load(self, project)
        self.__cvsps = project.config.get(self.name, 'cvsps-command', 'cvsps')


class DarcsRepository(Repository):
    METADIR = '_darcs'

    def _load(self, project):
        Repository._load(self, project)
        cget = project.config.get
        self.EXECUTABLE = cget(self.name, 'darcs-command', 'darcs')
        self.use_look_for_adds = cget(self.name, 'look-for-adds', 'False')

    def command(self, *args, **kwargs):
        if args[0] == 'record' and self.use_look_for_adds:
            args = args + ('--look-for-adds',)
        return Repository.command(self, *args, **kwargs)


class GitRepository(Repository):
    METADIR = '.git'

    def _load(self, project):
        Repository._load(self, project)
        self.EXECUTABLE = project.config.get(self.name, 'git-command', 'git')


class HgRepository(Repository):
    METADIR = '.hg'

    def _load(self, project):
        Repository._load(self, project)
        ppath = project.config.get(self.name, 'python-path')
        if ppath:
            from sys import path

            if ppath not in path:
                path.insert(0, ppath)
        self.EXTRA_METADIRS = ['.hgtags']

    def _validateConfiguration(self):
        """
        Mercurial expects all data to be in utf-8, so we disallow other encodings
        """
        Repository._validateConfiguration(self)

        if self.encoding.upper() != 'UTF-8':
            self.log.warning("Forcing UTF-8 encoding instead of " + self.encoding)
            self.encoding = 'UTF-8'

class MonotoneRepository(Repository):
    METADIR = '_MTN'

    def _load(self, project):
        Repository._load(self, project)
        cget = project.config.get
        self.EXECUTABLE = cget(self.name, 'monotone-command', 'mtn')
        self.keyid = cget(self.name, 'keyid')
        self.passphrase = cget(self.name, 'passphrase')
        self.keyfile = cget(self.name, 'keyfile')
        self.keygenid = cget(self.name, 'keygenid')
        self.custom_lua = cget(self.name, 'custom_lua')


class SvnRepository(Repository):
    METADIR = '.svn'

    def command(self, *args, **kwargs):
        if kwargs.get('svnadmin', False):
            kwargs['executable'] = self.__svnadmin
        return Repository.command(self, *args, **kwargs)

    def _load(self, project):
        Repository._load(self, project)
        cget = project.config.get
        self.EXECUTABLE = cget(self.name, 'svn-command', 'svn')
        self.__svnadmin = cget(self.name, 'svnadmin-command', 'svnadmin')
        self.use_propset = cget(self.name, 'use-propset', False)
        self.filter_badchars = cget(self.name, 'filter-badchars', False)
        self.use_limit = cget(self.name, 'use-limit', True)
        self.trust_root = cget(self.name, 'trust-root', False)
        self.ignore_externals = cget(self.name, 'ignore-externals', True)

    def _validateConfiguration(self):
        from vcpx.config import ConfigurationError

        Repository._validateConfiguration(self)

        if not self.repository:
            self.log.critical('Missing repository information in %r', self.name)
            raise ConfigurationError("Must specify the root of the "
                                     "Subversion repository used "
                                     "as %s with the option "
                                     "'repository'" % self.which)
        elif self.repository.endswith('/'):
            self.log.debug("Removing final slash from %r in %r",
                           self.repository, self.name)
            self.repository = self.repository.rstrip('/')

        if not self.module:
            self.log.critical('Missing module information in %r', self.name)
            raise ConfigurationError("Must specify the path within the "
                                     "Subversion repository as 'module'")

        if self.module == '.':
            self.log.warning("Replacing '.' with '/' in module name in %r",
                             self.name)
            self.module = '/'
        elif not self.module.startswith('/'):
            self.log.debug("Prepending '/' to module %r in %r",
                           self.module, self.name)
            self.module = '/' + self.module

    def workingDir(self):
        wd = Repository.workingDir(self)
        wd.USE_PROPSET = self.use_propset
        return wd


class TlaRepository(Repository):
    METADIR = '{arch}'

    def _load(self, project):
        Repository._load(self, project)
        self.EXECUTABLE = project.config.get(self.name, 'tla-command', 'tla')
        self.IGNORE_IDS = project.config.get(self.name, 'ignore-ids', False)
        if self.IGNORE_IDS:
            self.EXTRA_METADIRS = ['.arch-ids']


class BazRepository(TlaRepository):
    def _load(self, project):
        TlaRepository._load(self, project)
        self.EXECUTABLE = project.config.get(self.name, 'baz-command', 'baz')

    def command(self, *args, **kwargs):
        if args:
            if args[0] == 'tree-lint':
                args = list(args)
                args[0] = 'lint'
            elif args[0] == 'missing' and args[1] == '-f':
                args = list(args)
                del args[1]
        return TlaRepository.command(self, *args, **kwargs)
