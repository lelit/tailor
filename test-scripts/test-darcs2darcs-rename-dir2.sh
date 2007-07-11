#!/bin/sh

# File: test-darcs2darcs-rename-dir2.sh
# needs: test-darcs2darcs.include
#
# Test for converting from Darcs to Darcs self.
# Rename dir names where a file exists.

. ./test-darcs2darcs.include
darcs_setup

mkdir dira
echo "foo" > dira/a.txt
darcs add -r dira
darcs record -a -A Nobody -m "initial commit"

darcs mv dira dirb
darcs record -a -A Nobody --ignore-times -m "simple rename directory"

testing_runs
