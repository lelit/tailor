#!/bin/sh

# File: test-mtn2mtn-1revision.sh
# needs: test-mtn2mtn.include
# 
# Test for converting 1 revision from Monotone to Monotone self.
# It's a selfchecking for Monotone.  Diff between test1.log and test2.log
# should no have difference.
#
# No errors found.

. ./test-mtn2mtn.include
monotone_setup

echo "foo" > file.txt
mtn_exec add file.txt
mtn_exec commit --message "only one commit"

testing_runs
