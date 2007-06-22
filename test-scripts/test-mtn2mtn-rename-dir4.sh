#!/bin/sh

# File: test-mtn2mtn-dir4.sh
# needs: test-mtn2mtn.include
#
# Test from Monotone to Subversion and back to Monotone again,
# to rename directories and changing files.
#
# No errors found.

. ./test-mtn2mtn.include
monotone_setup

# Create files, rename directory, files and change files on renamed directory.

mkdir dira
mkdir dira/subdir
mkdir dirb
mkdir dirb/subdir
mkdir dirb/subdir/otherdir
echo "foo" > dira/file1.txt
echo "foo" > dirb/subdir/file2.txt
mtn_exec add dira/file1.txt dirb/subdir/file2.txt
mtn_exec commit --message "initial commit"

mtn_exec rename dira dira2
mtn_exec rename dirb dirb2
mtn_exec commit --message "rename directory where exist subdirs"

testing_runs
