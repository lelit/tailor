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

from cStringIO import StringIO
from ConfigParser import SafeConfigParser, NoSectionError, DEFAULTSECT
from vcpx import TailorException


class ConfigurationError(TailorException):
    """Configuration error"""


LOGGING_SUPER_SECTION = '[[logging]]'
BASIC_LOGGING_CONFIG = """\
[formatters]
keys = console

[formatter_console]
format =  %(asctime)s [%(levelname).1s] %(message)s
datefmt = %H:%M:%S

[loggers]
keys = root

[logger_root]
level = INFO
handlers = console

[handlers]
keys = console

[handler_console]
class = StreamHandler
formatter = console
args = (sys.stdout,)
level = INFO
"""


class Config(SafeConfigParser):
    '''
    Syntactic sugar around standard ConfigParser, for easier access to
    the configuration. To access any single project use the configuration
    as a dictionary.

    The file may be a full fledged Python script, starting
    with the usual ``"#!..."`` notation: in this case, it gets evaluated and
    its documentation becomes the actual configuration, while the functions
    it defines may be referenced by the `before-commit` and `after-commit`
    slots.

    This is where the logging system gets initialized, possibly merging a
    logging specific configuration section, introduced by a *supersection*
    ``[[logging]]``.
    '''

    def __init__(self, fp, defaults):
        SafeConfigParser.__init__(self)
        self.namespace = {}

        loggingcfg = None
        if fp:
            if fp.read(2) == '#!':
                fp.seek(0)
                exec fp.read() in globals(), self.namespace
                config = self.namespace['__doc__']
            else:
                fp.seek(0)
                config = fp.read()

            # Look for a [[logging]] separator, that introduce a
            # standard logging  section
            cfgs = config.split(LOGGING_SUPER_SECTION)
            if len(cfgs) == 2:
                tailorcfg, loggingcfg = cfgs
            else:
                tailorcfg = cfgs[0]

            self.readfp(StringIO(tailorcfg))

        # Override the defaults with the command line options
        if defaults:
            self._defaults.update(defaults)

        self._setupLogging(loggingcfg and loggingcfg or BASIC_LOGGING_CONFIG)

    def _setupLogging(self, config):
        """
        Tailor own's approach at file based logging configuration.
        """

        import logging, logging.handlers

        cp = SafeConfigParser()
        cp.readfp(StringIO(config), self._defaults)

        #first, do the formatters...
        flist = cp.get("formatters", "keys")
        if flist:
            flist = flist.split(',')
            formatters = {}
            for form in flist:
                sectname = "formatter_%s" % form
                opts = cp.options(sectname)
                if "format" in opts:
                    fs = cp.get(sectname, "format", 1)
                else:
                    fs = None
                if "datefmt" in opts:
                    dfs = cp.get(sectname, "datefmt", 1)
                else:
                    dfs = None
                f = logging.Formatter(fs, dfs)
                formatters[form] = f
        #next, do the handlers...
        dbglevel = self._defaults.get('debug', False) and 'DEBUG' or None
        try:
            hlist = cp.get("handlers", "keys")
            if hlist:
                handlers = {}
                fixups = [] #for inter-handler references
                for hand in hlist.split(','):
                    try:
                        sectname = "handler_%s" % hand
                        klass = cp.get(sectname, "class")
                        opts = cp.options(sectname)
                        if "formatter" in opts:
                            fmt = cp.get(sectname, "formatter")
                        else:
                            fmt = None
                        klass = eval(klass, vars(logging))
                        args = cp.get(sectname, "args")
                        args = eval(args, vars(logging))
                        h = apply(klass, args)
                        if dbglevel:
                            level = dbglevel
                        elif "level" in opts:
                            level = cp.get(sectname, "level")
                        else:
                            level = None
                        if level:
                            h.setLevel(logging._levelNames[level])
                        if fmt:
                            h.setFormatter(formatters[fmt])
                        #temporary hack for FileHandler and MemoryHandler.
                        if klass == logging.handlers.MemoryHandler:
                            if "target" in opts:
                                target = cp.get(sectname,"target")
                            else:
                                target = ""
                            if len(target):
                                # the target handler may not be loaded
                                # yet, so keep for later...
                                fixups.append((h, target))
                        handlers[hand] = h
                    except:
                        #if an error occurs when instantiating a
                        #handler, too bad this could happen
                        #e.g. because of lack of privileges
                        raise #pass
                #now all handlers are loaded, fixup inter-handler references...
                for h,t in fixups:
                    h.setTarget(handlers[t])
            #at last, the loggers...first the root...
            llist = cp.get("loggers", "keys")
            if llist:
                llist = llist.split(',')
            llist.remove("root")
            sectname = "logger_root"
            root = logging.root
            opts = cp.options(sectname)
            if dbglevel:
                level = dbglevel
            elif "level" in opts:
                level = cp.get(sectname, "level")
            else:
                level = None
            if level:
                root.setLevel(logging._levelNames[level])
            for h in root.handlers[:]:
                root.removeHandler(h)
            hlist = cp.get(sectname, "handlers")
            if hlist:
                for h in hlist.split(','):
                    root.addHandler(handlers[h])
            #and now the others...
            for log in llist:
                sectname = "logger_%s" % log
                qn = cp.get(sectname, "qualname", log)
                opts = cp.options(sectname)
                if "propagate" in opts:
                    propagate = cp.getint(sectname, "propagate")
                else:
                    propagate = 1
                logger = logging.getLogger(qn)
                if dbglevel:
                    level = dbglevel
                elif "level" in opts:
                    level = cp.get(sectname, "level")
                else:
                    level = None
                if level:
                    logger.setLevel(logging._levelNames[level])
                for h in logger.handlers[:]:
                    logger.removeHandler(h)
                logger.propagate = propagate
                logger.disabled = 0
                hlist = cp.get(sectname, "handlers")
                if hlist:
                    for h in hlist.split(','):
                        logger.addHandler(handlers[h])
        except:
            from sys import exc_info, stderr
            from traceback import print_exception
            ei = exc_info()
            print_exception(ei[0], ei[1], ei[2], None, stderr)
            del ei

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
        `raw` is true.  Additional substitutions may be provided using the
        `vars` argument, which must be a dictionary whose contents overrides
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
            pass
        option = self.optionxform(option)
        try:
            value = d[option]
        except KeyError:
            value = default

        if not raw:
            value = self._interpolate(section, option, str(value), d)

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
