#!/bin/sh

# File: test-darcs2darcs-delete-dir.sh
# needs: test-darcs2darcs.include
#
# Test for converting from Darcs to Darcs self.
# Delete a file and the directory.
#
# Fails on target, it tries "darcs remove deleteme deleteme/foo",
# but would only work with "darcs remove deleteme/foo deleteme"

. ./test-darcs2darcs.include
darcs_setup

mkdir deleteme
echo "foo" > deleteme/foo
darcs add -r deleteme
darcs record -v -a -A Nobody -m "initial commit"

darcs remove deleteme/foo
darcs remove deleteme
darcs record -v -a -A Nobody --ignore-times -m "second commit"

testing_runs
