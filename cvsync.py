#! /usr/bin/env python
#  -*- Python -*- -*- coding: iso-8859-1 -*-
# :Progetto: Bice -- Sync CVS->SVN
# :Sorgente: $HeadURL: http://svn.bice.dyndns.org/progetti/wip/tools/cvsync.py $
# :Creato:   mer 24 mar 2004 17:30:23 CET
# :Autore:   Lele Gaifax <lele@nautilus.homeip.net>
# :Modifica: $LastChangedDate: 2004-05-04 20:02:07 +0200 (mar, 04 mag 2004) $
# :Fatta da: $LastChangedBy: lele $
# 

"""Automatize the process of tracking CVS-based software within a SVN wc.

This script makes it easier to keep some third-party CVS-based software
up-to-date.  It is able to perform a ``cvs update``, collecting the
changed entries with the respective log, informing SVN about addition and
deletion and performing a commit.

Given that CVS repositories are a little flaky, the script keeps a cache
of each session, to be able to restart the job from where it failed, the
next invocation.

Examples::

  # What happened?
  $ cvsync.py -d -k docutils | less

  # Ok, do the update, possibly reusing the logs
  $ cvsync.py docutils

  # Execute the testsuite
  $ cvsync.py test -v
"""

__docformat__ = 'reStructuredText'

if __name__ == '__main__':
    import sys

    if sys.argv[1] == 'test':
        del sys.argv[1]
        from unittest import main
        main(module='cvsync.tests', argv=sys.argv)
    else:
        from cvsync.sync import main
        main()
