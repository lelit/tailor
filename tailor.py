#! /usr/bin/python
# -*- mode: python; coding: utf-8 -*-
# :Progetto: vcpx -- Frontend
# :Creato:   lun 03 mag 2004 01:39:00 CEST
# :Autore:   Lele Gaifax <lele@nautilus.homeip.net>
#

"""Keep in sync a tree with its "upstream" repository.

This script makes it easier to keep the upstream changes merged in
a branch of a product, storing needed information such as the upstream
URI and revision in special properties on the branched directory.

Examples::

  # Bootstrap a new taylored project, starting at upstream revision 10
  $ tailor.py -b -s svn -R http://svn.server/Product -r 10 ~/darcs/MyProduct 

  # Bootstrap a new product, fetching from CVS and storing under SVN: this
  # will create the directory "~/svnwc/cmfcore"; "~/svnwc" must be already
  # under SVN.
  $ tailor.py --source-kind cvs --target-kind svn --bootstrap \
              --repository :pserver:cvs.zope.org:/cvs-repository \
              --module CMF/CMFCore ~/svnwc/cmfcore
  
  # Showing each command bootstrap a new DARCS repos in "~/darcs/cmftopic"
  # under which the upstream module will be extracted as "CMFTopic" (ie, the
  # last component of the module name).
  $ tailor.py -D -b -R :pserver:anonymous@cvs.zope.org:/cvs-repository/ \
              -m CMF/CMFTopic ~/darcs/cmftopic
              
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
