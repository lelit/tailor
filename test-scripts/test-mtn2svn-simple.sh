#!/bin/sh

# File: test-mtn2svn-simple.sh
# needs: test-mtn2svn.include
# 
# Test for converting 2 revisions from Monotone to Subversion and back to Monotone again.

. ./test-mtn2svn.include
monotone_setup

# Create one file and 2 revisions, simple linear revisions

echo "foo" > file.txt
mtn_exec add file.txt
mtn_exec commit --message "initial commit"

echo "bar" > file.txt
mtn_exec commit --message "second commit"

testing_runs
