# -*- mode: python; coding: utf-8 -*-
# :Progetto: vcpx -- Aegis details
# :Creato:   sab 24 mag 2008 15:44:00 CEST
# :Autore:   Walter Franzini <walter.franzini@gmail.com>
# :Licenza:  GNU General Public License
#

from vcpx.repository import Repository

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
