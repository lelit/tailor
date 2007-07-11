#!/bin/sh

# File: test-darcs2darcs-simple.sh
# needs: test-darcs2darcs.include
#
# Test for converting from Darcs to Darcs self.
# Renaming simple dir name, and renaming dir names where subdirs exists.

. ./test-darcs2darcs.include
darcs_setup

mkdir -p dira/subdira
mkdir -p dirb/subdirb/otherdir
echo "foo" > dira/file1.txt
echo "foo" > dirb/subdirb/file2.txt
darcs add -r dira dirb
darcs record -a -A Nobody -m "initial commit"

darcs mv dira dira2
darcs mv dirb dirb2
darcs record -a -A Nobody -m "rename directory where exist subdirs"

testing_runs
