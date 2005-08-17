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

class Repository(object):
    """
    Collector for the configuration of a single repository.
    """

    def __init__(self, name, kind, project, which):
        self.name = name
        self.kind = kind
        self.project = project
        self._load(project.config, which)

    def __str__(self):
        return "%s repository at %s%s" % (self.kind, self.repository,
                                          self.module or '')

    def _load(self, config, which):
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

        self.repository = config.get(self.name, 'repository') or \
                          config.get(self.name, '%s-repository' % which)
        if self.repository:
            self.repository = expanduser(self.repository)
        self.module = config.get(self.name, 'module') or \
                      config.get(self.name, '%s-module' % which)
        self.rootdir = config.get(self.name, 'root-directory',
                                  vars={'root-directory': self.project.rootdir})
        self.subdir = config.get(self.name, 'subdir',
                                 vars={'subdir': self.project.subdir})

    def _validateConfiguration(self):
        """
        Validate the configuration, possibly altering/completing it.
        """

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

        self._validateConfiguration()

        wdname = self.kind.capitalize() + 'WorkingDir'
        modname = 'vcpx.' + self.kind
        try:
            wdmod = __import__(modname, globals(), locals(), [wdname])
            workingdir = getattr(wdmod, wdname)
        except (AttributeError, ImportError):
            raise InvocationError("Unhandled source VCS kind: " + self.kind)

        return workingdir(self)


class ArxRepository(Repository):
    METADIR = '_arx'
    ARX_CMD = "arx"

    def _load(self, config, which):
        Repository._load(self, config, which)
        self.ARX_CMD = config.get(self.name, 'arx-command', self.ARX_CMD)



class BzrRepository(Repository):
    METADIR = '.bzr'
    BZR_CMD = 'bzr'

    def _load(self, config, which):
        Repository._load(self, config, which)
        self.BZR_CMD = config.get(self.name, 'bzr-command', self.BZR_CMD)


class CdvRepository(Repository):
    METADIR = '.cdv'
    CDV_CMD = 'cdv'

    def _load(self, config, which):
        Repository._load(self, config, which)
        self.CDV_CMD = config.get(self.name, 'cdv-command', self.CDV_CMD)


class CvsRepository(Repository):
    METADIR = 'CVS'
    CVS_CMD = 'cvs'

    def _load(self, config, which):
        Repository._load(self, config, which)
        self.CVS_CMD = config.get(self.name, 'cvs-command', self.CVS_CMD)

    def _validateConfiguration(self):
        from os.path import split
        from config import ConfigurationError


        if not self.module and self.repository:
            self.module = split(self.repository)[1]

        if not self.module:
            raise ConfigurationError("Must specify a repository and maybe a module also")

class CvspsRepository(CvsRepository):
    CVSPS_CMD = 'cvsps'

    def _load(self, config, which):
        CvsRepository._load(self, config, which)
        self.CVSPS_CMD = config.get(self.name, 'cvsps-command', self.CVSPS_CMD)


class DarcsRepository(Repository):
    METADIR = '_darcs'
    DARCS_CMD = 'darcs'

    def _load(self, config, which):
        Repository._load(self, config, which)
        self.DARCS_CMD = config.get(self.name, 'darcs-command', self.DARCS_CMD)


class HgRepository(Repository):
    METADIR = '.hg'
    HG_CMD = "hg"

    def _load(self, config, which):
        Repository._load(self, config, which)
        self.HG_CMD = config.get(self.name, 'hg-command', self.HG_CMD)


class MonotoneRepository(Repository):
    METADIR = 'MT'
    MONOTONE_CMD = "monotone"

    def _load(self, config, which):
        Repository._load(self, config, which)
        self.MONOTONE_CMD = config.get(self.name,
                                       'monotone-command', self.MONOTONE_CMD)
        self.passphrase = config.get(self.name, 'passphrase')


class SvnRepository(Repository):
    METADIR = '.svn'
    SVN_CMD = "svn"
    SVNADMIN_CMD = "svnadmin"

    def _load(self, config, which):
        Repository._load(self, config, which)
        self.SVN_CMD = config.get(self.name, 'svn-command', self.SVN_CMD)
        self.SVNADMIN_CMD = config.get(self.name,
                                       'svnadmin-command', self.SVNADMIN_CMD)
        self.use_propset = config.get(self.name, 'use-propset', False)

    def _validateConfiguration(self):
        if not self.module:
            raise ConfigurationError("Must the path within the "
                                     "Subversion repository")

        if not self.module.startswith('/'):
            self.project.log_info("Prepending '/' to module")
            self.module = '/' + self.module

    def workingDir(self):
        wd = Repository.workingDir(self)
        wd.USE_PROPSET = self.use_propset
        return wd


class TlaRepository(Repository):
    METADIR = '{arch}'
    TLA_CMD = "tla"

    def _load(self, config, which):
        Repository._load(self, config, which)
        self.TLA_CMD = config.get(self.name, 'tla-command', self.TLA_CMD)
