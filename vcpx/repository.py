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

        from os.path import split

        self.repository = config.get(self.name, 'repository') or \
                          config.get(self.name, '%s-repository' % which)
        self.module = config.get(self.name, 'module') or \
                      config.get(self.name, '%s-module' % which)
        if not self.module:
            self.module = split(self.repository)[1]

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


class ArxRepository(Repository):
    METADIR = '_arx'

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
