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

from tla import TlaWorkingDir

class BazWorkingDir(TlaWorkingDir):
    """
    A working directory under ``baz``.
    """

    # For tailor purposes, the only difference between baz and tla
    # is the name of command "lint", that tla calls "tree-lint".
    # The BazRepository takes care of fixing that.
