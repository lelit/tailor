#  -*- Python -*- -*- coding: iso-8859-1 -*-
# :Progetto: Bice -- Sync CVS->SVN
# :Sorgente: $HeadURL: http://svn.bice.dyndns.org/progetti/wip/tools/cvsync/__init__.py $
# :Creato:   sab 10 apr 2004 16:36:48 CEST
# :Autore:   Lele Gaifax <lele@nautilus.homeip.net>
# :Modifica: $LastChangedDate: 2004-05-05 01:13:37 +0200 (mer, 05 mag 2004) $
# :Fatta da: $LastChangedBy: lele $
# 

"""Third-party & external sources tracking aid.

This module allows to keep in sync a Subversion repository with a CVS
one, and makes a little bit easier to "tailorize" a product.  This is
almost the same as a branch of some upstream SVN subtree, where usually
some customizations get done, and now and then merged with upstream
changes. 

The functionalities are spread over a few submodules:

shwrap
      Basic wrapper class to easily execute subprocess.
      
cvs
      The CVS point of view of a working copy directory.

svn
      The Subversion counterpart.

sync
      The CVS->SVN syncronization machinery.

tailor
      The SVN->SVN tailorization machinery.
"""

__docformat__ = 'reStructuredText'

