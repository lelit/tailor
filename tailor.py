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

  # Bootstrap a new product, fetching from CVS and storing under SVN
  $ tailor.py --source-kind cvs --target-kind svn -b ~/wc/prod :pserver:...

  # Merge upstream changes since last update/bootstrap
  $ tailor.py ~/svnwc/MyProduct
"""

__docformat__ = 'reStructuredText'

if __name__ == '__main__':
    import sys

    if len(sys.argv)>1 and sys.argv[1] == 'test':
        del sys.argv[1]
        from unittest import main
        main(module='vcpx.tests', argv=sys.argv)
    else:
        from vcpx.tailor import main

        if len(sys.argv) == 1:
            sys.argv.append('--help')
            
        main()
