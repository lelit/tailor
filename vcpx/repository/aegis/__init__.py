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
        #
        # Run aegis in verbose mode
        #
        args = args + ('-verbose',)

        #
        # Disable the log file functionality
        #
        if not kwargs.has_key('env'):
            kwargs['env'] = {}
        kwargs['env']['AEGIS_FLAGS'] = "log_file_preference = never;"

        #
        # aefinish is a different executable.  Take care of it.
        #
        original_command = self.EXECUTABLE
        if args[0] == "-finish":
            self.EXECUTABLE = "aefinish"
            args = args[1:]

        rc = Repository.command(self, *args, **kwargs)
        self.EXECUTABLE = original_command
        return rc
