# -*- mode: python; coding: utf-8 -*-
# :Progetto: vcpx - Version Control Patch eXchanger
# :Creato:   mer 16 giu 2004 00:15:54 CEST
# :Autore:   Lele Gaifax <lele@nautilus.homeip.net>
# :Licenza:  GNU General Public License
#

"""
vcpx - Version Control Patch eXchanger
======================================

This package encapsulates the machinery needed to keep the patches in
sync across different VC systems.
"""

__docformat__ = 'reStructuredText'


class TailorException(Exception):
    "Common base for tailor exceptions"

class TailorBug(TailorException):
    "Tailor bug (please report)"
