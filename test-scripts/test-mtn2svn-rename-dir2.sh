#!/bin/sh

# File: test-mtn2svn-rename-dir2.sh
# needs: test-mtn2svn.include
# 
# Test from Monotone to Subversion and back to Monotone again,
# to rename directories and changing files.
#
# ERROR:
# ------
# The revision "bar" is missing by mtn --> svn convert, because it
# changes a file on a renamed directory.
#
# Problem: The "svn mv" save the current timestamp, so commit see no changes.
# To understand, try these steps after the test script was running:
# $ cd ...testdir/rootdir/svnside
# $ svn diff                                         (no outputs)
# $ svn status -v                                    (see, no 'M' for file.txt)
#                 3        3 key-dummy    .
#                 3        3 hn           dirb
#                 3        3 hn           dirb/file.txt
# $ touch dirb/file.txt
# $ svn diff
# Index: dirb/file.txt
# =============================================
# --- dirb/file.txt(Revision 3)
# +++ dirb/file.txt(Arbeitskopie)
# @@ -1 +1 @@
# -foo
# +bar
# $ svn status -v
#                 3        3 key-dummy    .
#                 3        3 hn           dirb
# M               3        3 hn           dirb/file.txt

# Fixed by svn-dir-move-file-change-delay.patch


. ./test-mtn2svn.include
monotone_setup

# Create one file and 2 revisions, simple linear revisions

mkdir dira
echo "foo" > dira/file.txt
mtn_exec add dira/file.txt
mtn_exec commit --message "initial commit"

echo "bar" > dira/file.txt
mtn_exec rename dira dirb
mtn_exec commit --message "rename directory, change file (Change on file is missing!)"

testing_runs
