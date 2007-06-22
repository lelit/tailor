#!/bin/sh

# File: test-mtn2mtn-simple.sh
# needs: test-mtn2mtn.include
# 
# Test for converting 2 revisions from Monotone to Monotone self.
#
# No errors found.

. ./test-mtn2mtn.include
monotone_setup

# Create one file and 2 revisions, simple linear revisions

echo "foo" > file.txt
mtn_exec add file.txt
mtn_exec commit --message "initial commit"

echo "bar" > file.txt
mtn_exec commit --message "second commit"

testing_runs
