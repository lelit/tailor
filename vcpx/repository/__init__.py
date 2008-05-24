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
    """
    The name of the "meta" directory used by this kind of repository.
    Subclasses should override this, obviously.
    """

    EXTRA_METADIRS = []
    """
    Other eventual "meta" directories.
    """

    EXECUTABLE = None
    """
    The name of the external command line tool, for some backends.
    """

    def __new__(klass, name, project, which):
        """
        Return the right subclass for kind, if it exists.
        """

        from vcpx import TailorException

        kind = name[:name.index(':')]
        subclass = klass
        subclassname = kind.capitalize() + 'Repository'
        modname = 'vcpx.repository.' + kind
        try:
            concrete = __import__(modname, globals(), locals(), [kind])
            subclass = getattr(concrete, subclassname, klass)
        except SyntaxError, e:
            raise TailorException("Cannot import %r: %s" % (kind, e))
        except (AttributeError, ImportError, AssertionError), e:
            raise TailorException("%r is not a known VCS kind: %s" % (kind, e))
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
        self.log = getLogger('tailor.vcpx.%s.%s' % (self.__class__.__name__,
                                                    which))
        self._load(project)
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

        from os.path import abspath, expanduser, join, normpath
        from locale import getpreferredencoding

        cget = project.config.get
        if project.config.has_section(self.name):
            optname = self.name
        else:
            optname = project.name

        self.repository = cget(optname, 'repository') or \
                          cget(optname, '%s-repository' % self.which)
        if self.repository:
            self.repository = expanduser(self.repository)

        self.module = cget(optname, 'module') or \
                      cget(optname, '%s-module' % self.which)

        rootdir = cget(optname, 'root-directory',
                       vars={'root-directory': project.rootdir})
        self.rootdir = abspath(expanduser(rootdir))
        self.subdir = cget(optname, 'subdir',
                           vars={'subdir': project.subdir})
        if self.subdir:
            self.basedir = normpath(join(self.rootdir, self.subdir))
        else:
            self.basedir = self.rootdir

        self.delay_before_apply = cget(optname, 'delay-before-apply')
        if self.delay_before_apply:
            self.delay_before_apply = float(self.delay_before_apply)

        self.encoding = cget(optname, 'encoding')
        if not self.encoding:
            self.encoding = getpreferredencoding()
        self.encoding_errors_policy = cget(optname,
                                           'encoding-errors-policy', 'strict')
        self.post_commit_check = cget(optname, 'post-commit-check', 'False')

    def _validateConfiguration(self):
        """
        Validate the configuration, possibly altering/completing it.
        """

        if self.EXECUTABLE:
            from os import getenv, pathsep
            from os.path import isabs, exists, join
            from sys import platform
            from vcpx.config import ConfigurationError

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

        from vcpx import TailorException

        try:
            try:
                wdname = self.kind.capitalize() + self.which.capitalize() + 'WorkingDir'
                modname = 'vcpx.repository.' + self.kind + '.' + self.which
                wdmod = __import__(modname, globals(), locals(), [wdname])
                workingdir = getattr(wdmod, wdname)
            except (AttributeError, ImportError), e:
                self.log.debug("%s not found as new-style vcs, trying as monolithic" % self.kind)
                wdname = self.kind.capitalize() + 'WorkingDir'
                modname = 'vcpx.repository.' + self.kind
                wdmod = __import__(modname, globals(), locals(), [wdname])
                workingdir = getattr(wdmod, wdname)
        except SyntaxError, e:
            self.log.exception("Cannot import %r from %r", wdname, modname)
            raise TailorException("Cannot import %r: %s" % (wdname, e))
        except (AttributeError, ImportError), e:
            self.log.critical("Cannot import %r from %r", wdname, modname)
            raise TailorException("%r is not a known VCS kind: %s" %
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

    def create(self):
        """
        Possibly open a connection to the repository. If the repository
        does not exist, create a new one, if at all possible.

        Subclasses implementing the target interface should reimplement
        this method, to create/initialize a new repository at the location
        given by either `self.repository` or `self.basedir`.
        """

        self.log.critical("%s should reimplement the create() method",
                          self.__class__)

    def stateFilePath(self, sfname):
        """
        Build and return the path to the state file.

        If `sfname` is ``hidden`` and this repository has a `METADIR`,
        then the file will be something like ``_darcs/tailor.state``.

        Otherwise, for historical reasons, this returns ``expanduser(sfname)``.
        """

        from os.path import expanduser, join

        if sfname == 'hidden':
            if self.METADIR:
                return join(self.basedir, self.METADIR, 'tailor.state')
            return join(self.basedir, 'tailor.state')
        else:
            return expanduser(sfname)
