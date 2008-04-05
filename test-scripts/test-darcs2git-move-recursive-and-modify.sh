#!/bin/sh

# File: test-darcs2git-move-recursive-and-modify.sh
# needs: test-darcs2git.include
#
# Test for converting from Darcs to Git.
# Tests if we can update a file which is just moved recursively within
# this patch.

. ./test-darcs2git.include
darcs_setup

mkdir -p dir1/subdir
echo foo >dir1/subdir/file
darcs add dir1/subdir/file
darcs record -v -a -A Nobody -m "import file"

mkdir dir2
darcs add dir2
darcs mv dir1/subdir dir2
echo bar >> dir2/subdir/file
darcs record -v -a -A Nobody -m "move subdir to dir2 and update file"

testing_runs
