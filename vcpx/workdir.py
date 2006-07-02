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
        from logging import getLogger

        self.repository = repository
        self.log = getLogger('tailor.%s.%s' % (self.__class__.__name__,
                                               repository.name))

    def setStateFile(self, state_file):
        """
        Set the state file used to store the revision and pending changesets.
        """

        self.state_file = state_file
