#! /usr/bin/python
# -*- mode: python; coding: utf-8 -*-
# :Progetto: Bice -- Sync SVN->SVN
# :Sorgente: $HeadURL: http://svn.bice.dyndns.org/progetti/wip/tools/tailor.py $
# :Creato:   lun 03 mag 2004 01:39:00 CEST
# :Autore:   Lele Gaifax <lele@nautilus.homeip.net>
# :Modifica: $LastChangedDate: 2004-05-05 01:13:37 +0200 (mer, 05 mag 2004) $
# :Fatta da: $LastChangedBy: lele $
#

"""Keep in sync a tree with its "upstream" repository.

This script makes it easier to keep the upstream changes merged in
a branch of a product, storing needed information such as the upstream
URI and revision in special properties on the branched directory.

Examples::

  # Bootstrap a new taylored project, starting at revision 10
  $ tailor.py --bootstrap ~/svnwc/MyProduct http://svn.example.com/Product@10

  # Merge upstream changes since last update/bootstrap
  $ tailor.py ~/svnwc/MyProducts

  # Show what's changed in current working directory
  $ tailor.py --diff

  # Manually set ancestry information
  $ tailor.py --set-ancestry ~/svnwc/Other http://svn.example.com/trunk@10
"""

__docformat__ = 'reStructuredText'

if __name__ == '__main__':
    import sys

    if sys.argv[1] == 'test':
        del sys.argv[1]
        from unittest import main
        main(module='cvsync.tests', argv=sys.argv)
    else:
        from cvsync.tailor import main
        main()
