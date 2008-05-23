#
# Copyright (C) 2008 Walter Franzini
#

import re

from vcpx.repository import Repository
from vcpx.shwrap import ExternalCommand

from vcpx.target import TargetInitializationFailure

class AegisRepository(Repository):

    def _load(self, project):
        Repository._load (self, project)
        cget = project.config.get
        self.EXECUTABLE = cget(self.name, 'aegis-command', 'aegis')

    def _validateConfiguration(self):
        pass

    def command(self, *args, **kwargs):
        original_command = self.EXECUTABLE
        #
        # aefinish is a different executable.  Take care of it.
        #
        if args[0] == "-finish":
            self.EXECUTABLE = "aefinish"
            args = args[1:]
        args = args + ('-verbose',)
        rc = Repository.command(self, *args, **kwargs)
        self.EXECUTABLE = original_command
        return rc
