#!/bin/sh

# File: test-mtn2svn-rename-dir3.sh
# needs: test-mtn2svn.include
# 
# Test from Monotone to Subversion and back to Monotone again,
# to rename directories and changing files.
#
# Was an older error: It's missing some changes on file ("bar").
# Fixed now.

. ./test-mtn2svn.include
monotone_setup

# Create files, rename directory, files and change files on renamed directory.

mkdir dira
mkdir dirb
echo "foo" > dira/file1.txt
echo "foo" > dirb/file2.txt
mtn_exec add dira/file1.txt dirb/file2.txt
mtn_exec commit --message "initial commit"

echo "bar" > dira/file1.txt
mtn_exec rename dira dira2
mtn_exec commit --message "rename directory, change file in there (will be missing)"

mtn_exec rename dira2 dira3
mtn_exec rename dirb dirb3
mtn_exec commit --message "rename two directories"

echo "bar" > dirb3/file2.txt
mtn_exec rename dira3 dira4
mtn_exec rename dirb3 dirb4
mtn_exec commit --message "change file on a changed directory"

mtn_exec rename dira4 dira5
mtn_exec rename dirb4/file2.txt dirb4/renamed.txt
mtn_exec commit --message "rename directory, rename file"

testing_runs
