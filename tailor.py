#!/usr/bin/env python
# -*- mode: python; coding: utf-8 -*-
# :Progetto: vcpx -- Frontend
# :Creato:   lun 03 mag 2004 01:39:00 CEST
# :Autore:   Lele Gaifax <lele@nautilus.homeip.net>
#

"""
Keep a tree in sync with its "upstream" repository of a (possibly)
different format.

For more documentation, see the README file from the distribution.
"""

__docformat__ = 'reStructuredText'

if __name__ == '__main__':
    import sys

    if len(sys.argv)>1 and sys.argv[1] == 'test':
        del sys.argv[1]
        from unittest import main
        main(module='vcpx.tests', argv=sys.argv)
    else:
        from vcpx.tailor import main, ExistingProjectError, ProjectNotTailored
        from vcpx.target import TargetInitializationFailure
        from vcpx.source import InvocationError
        from vcpx.cvs import EmptyRepositoriesFoolsMe
        
        if len(sys.argv) == 1:
            sys.argv.append('--help')

        try:
            main()
        except ExistingProjectError, exc:
            print exc
        except ProjectNotTailored, exc:
            print exc
        except TargetInitializationFailure, exc:
            print exc
        except EmptyRepositoriesFoolsMe, exc:
            print exc, "Maybe wrong module?"
        except InvocationError, exc:
            print exc


