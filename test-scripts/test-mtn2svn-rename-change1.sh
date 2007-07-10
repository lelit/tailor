#!/bin/sh

# File: test-mtn2svn-rename-change1.sh
# needs: test-mtn2svn.include
# 
# Test converting revisions from Monotone to Subversion and back to Monotone again.
# It dropped informations on changed files, if an other file was 'removed' or 'deleted'.
# Was an old error: The file1.txt revision "bar1" was losed.
#
# A more complexe testing script is 'test-mtn-svn-del-ren-add-change.sh'
#
# No errors found.

. ./test-mtn2svn.include
monotone_setup

# Create 2 files, 3 revisions
echo "foo1" > file1.txt
echo "foo2" > file2.txt
mtn_exec add file1.txt file2.txt
mtn_exec commit --message "initial commit"

echo "bar1 (this will be missing later)" > file1.txt
mtn_exec rename file2.txt file2b.txt
mtn_exec commit --message "File1 changed, File2 renamed"

#echo "touch file1 again" > file1.txt
#mtn_exec commit --message "change file 1 again"

testing_runs
