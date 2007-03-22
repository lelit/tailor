# -*- mode: python; coding: utf-8 -*-
# :Progetto: vcpx -- p4 source (using p4lib)
# :Creato:   Fri Mar 16 22:10:41 PDT 2007
# :Autore:   Dustin Sallings <dustin@spy.net>
# :Licenza:  GNU General Public License
#

"""
This module implements the parts of the backend for p4 using p4lib.
"""

__docformat__ = 'reStructuredText'

from vcpx.config import ConfigurationError
from vcpx.repository import Repository
from vcpx.shwrap import ExternalCommand, PIPE
from vcpx.target import TargetInitializationFailure

import exceptions
import p4lib

class P4Repository(Repository):

    def _load(self, project):
        Repository._load(self, project)
        self.EXECUTABLE = project.config.get(self.name, 'p4-command', 'p4')
        self.depot_path = project.config.get(self.name, 'depot-path')
        self.p4client = project.config.get(self.name, 'p4-client', None)
        self.p4port = project.config.get(self.name, 'p4-port', None)

        self.env = {}

