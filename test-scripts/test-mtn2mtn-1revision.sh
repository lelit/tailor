#!/bin/bash -v

# File: test-mtn2mtn-1revision.sh
# needs: test-mtn2mtn.include
# 
# Test for converting 1 revision from Monotone to Monotone self.
# It's a selfchecking for Monotone.  Diff between test1.log and test2.log
# should no have difference.
#
# It fails with:
#  File "tailor-0.9.28-henry/vcpx/repository/monotone.py", line 726, in _convert_head_initial
#    effective_rev=revlist[0]
#  IndexError: list index out of range
#
# No errors after patch monotone-complete-20070604.patch
# Log-diff: PASS

. ./test-mtn2mtn.include
monotone_setup

# Create one file and 1 revision

echo "foo" > file.txt
mtn_exec add file.txt
mtn_exec commit --message "only one commit"

testing_runs
