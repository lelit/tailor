# -*- mode: python; coding: utf-8 -*-
# :Progetto: vcpx -- baz (Arch 1.x) backend
# :Creato:   sab 13 ago 2005 12:16:16 CEST
# :Autore:   Ollivier Robert <roberto@keltia.freenix.fr>
# :Licenza:  GNU General Public License
#

"""
This module implements the backends for baz (Arch 1.x).
"""

__docformat__ = 'reStructuredText'

from vcpx.repository.tla import TlaRepository, TlaWorkingDir


class BazRepository(TlaRepository):
    def _load(self, project):
        TlaRepository._load(self, project)
        self.EXECUTABLE = project.config.get(self.name, 'baz-command', 'baz')

    def command(self, *args, **kwargs):
        if args:
            if args[0] == 'tree-lint':
                args = list(args)
                args[0] = 'lint'
            elif args[0] == 'missing' and args[1] == '-f':
                args = list(args)
                del args[1]
        return TlaRepository.command(self, *args, **kwargs)


class BazWorkingDir(TlaWorkingDir):
    """
    A working directory under ``baz``.
    """

    # For tailor purposes, the only difference between baz and tla
    # is the name of command "lint", that tla calls "tree-lint".
    # The BazRepository takes care of fixing that.
