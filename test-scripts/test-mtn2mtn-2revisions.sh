#!/bin/bash -v

# File: test-mtn2mtn-2revisions.sh
# needs: test-mtn2mtn.include
# 
# Test for converting 2 revisions from Monotone to Monotone self.
# It's a selfchecking for Monotone.  Diff between test1.log and test2.log
# should no have difference.
#
# No errors found.
# Log-diff: PASS

. ./test-mtn2mtn.include
monotone_setup

# Create one file and 2 revisions, simple linear revisions

echo "foo" > file.txt
mtn_exec add file.txt
mtn_exec commit --message "initial commit"

echo "bar" > file.txt
mtn_exec commit --message "second commit"

testing_runs
