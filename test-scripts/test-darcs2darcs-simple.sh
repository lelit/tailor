#!/bin/sh

# File: test-darcs2darcs-simple.sh
# needs: test-darcs2darcs.include
#
# Test for converting from Darcs to Darcs self.
# Create one file and 2 revisions, simple linear revisions.

. ./test-darcs2darcs.include
darcs_setup

echo "foo" > file.txt
darcs add file.txt
darcs record -a -A Nobody -m "initial commit"

echo "bar" > file.txt
darcs record -a -A Nobody --ignore-times -m "second commit"

testing_runs
