# -*- mode: python; coding: utf-8 -*-
# :Progetto: vcpx -- Abstract working directory
# :Creato:   sab 06 ago 2005 10:41:13 CEST
# :Autore:   Lele Gaifax <lele@nautilus.homeip.net>
# :Licenza:  GNU General Public License
#

"""
"""

__docformat__ = 'reStructuredText'

class WorkingDir(object):
    """
    This is the common ancestor for working directories, associated
    to some kind of repository.
    """

    def __init__(self, repository):
        from os.path import join, normpath

        self.repository = repository
        if repository.subdir:
            self.basedir = normpath(join(repository.rootdir, repository.subdir))
        else:
            self.basedir = repository.rootdir

    def log_info(self, what):
        """
        Print some info on the log and, in verbose mode, to stdout as well.
        """

        self.repository.log_info(what)

    def log_error(self, what, exc=False):
        """
        Print an error message, possibly with an exception traceback,
        to the log and to stdout as well.
        """

        self.repository.log_error(what, exc)
