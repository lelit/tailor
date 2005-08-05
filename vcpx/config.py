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
    """Configuration error"""

class UnknownProjectError(Exception):
    "Project does not exist"

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
        if fp:
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
            value = SafeConfigParser.get(self, section, option)
            if value == 'None':
                return default
            elif value == 'True':
                return True
            elif value == 'False':
                return False
            else:
                return value
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

    def __getitem__(self, name):
        from project import Project

        if not self.has_section(name):
            raise UnknownProjectError("'%s' is not a known project" % name)

        return Project(name, self)
