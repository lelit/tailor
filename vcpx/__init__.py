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

from vcpx.tailor import main, ExistingProjectError, ProjectNotTailored
from vcpx.target import TargetInitializationFailure, ChangesetReplayFailure
from vcpx.source import InvocationError, GetUpstreamChangesetsFailure,\
     ChangesetApplicationFailure
from vcpx.cvsps import EmptyRepositoriesFoolsMe
from vcpx.config import ConfigurationError
from vcpx.project import UnknownProjectError

TailorExceptions = (ExistingProjectError, ProjectNotTailored,
                    TargetInitializationFailure, EmptyRepositoriesFoolsMe,
                    InvocationError, GetUpstreamChangesetsFailure,
                    ChangesetApplicationFailure, ConfigurationError,
                    UnknownProjectError, ChangesetReplayFailure)
