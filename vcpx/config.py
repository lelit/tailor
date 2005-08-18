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

from ConfigParser import SafeConfigParser, NoSectionError, DEFAULTSECT

class ConfigurationError(Exception):
    """Configuration error"""

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

    def get(self, section, option, default=None, raw=False, vars=None):
        """Get an option value for a given section or the default value.

        All % interpolations are expanded in the return values, based on the
        defaults passed into the constructor, unless the optional argument
        `raw' is true.  Additional substitutions may be provided using the
        `vars' argument, which must be a dictionary whose contents overrides
        any pre-existing defaults, but not those in the given section.

        The section DEFAULT is special.
        """

        # Reimplement parent behaviour, that uses `vars` to override even
        # the value in the specific section... Overriding the defaults
        # seems a better idea

        d = self._defaults.copy()
        # Update with the entry specific variables
        if vars is not None:
            d.update(vars)
        try:
            d.update(self._sections[section])
        except KeyError:
            if section != DEFAULTSECT:
                raise NoSectionError(section)
        option = self.optionxform(option)
        try:
            value = d[option]
        except KeyError:
            value = default

        if not raw:
            value = self._interpolate(section, option, value, d)

        if value == 'None':
            return default
        elif value == 'True':
            return True
        elif value == 'False':
            return False
        else:
            return value

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
