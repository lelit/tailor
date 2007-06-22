#!/bin/sh

# File: test-mtn2svn-1revision.sh
# needs: test-mtn2svn.include
# 
# Test for converting 1 revision from Monotone to Subversion and back to Monotone again.
#
# No errors found.

. ./test-mtn2svn.include
monotone_setup

echo "foo" > file.txt
mtn_exec add file.txt
mtn_exec commit --message "only one commit"

testing_runs
