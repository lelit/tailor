#!/bin/sh

# File: test-mtn2svn-rename-and-back.sh
# needs: test-mtn2svn.include
#
# Test for converting from Monotone to Subversion and back to Monotone again.
# Rename dir and than back into same again.
# Was an error with old exiting directory.

. ./test-mtn2svn.include
monotone_setup

mkdir -p dir/subdir
echo "foo" > dir/subdir/file.txt
mtn_exec add dir/subdir/file.txt
mtn_exec commit --message "initial commit"

mtn_exec rename dir/subdir dir/newdir
mtn_exec commit --message "rename first"

mtn_exec rename dir/newdir dir/subdir
mtn_exec commit --message "rename back"

testing_runs
