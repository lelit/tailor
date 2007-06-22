#!/bin/sh

# File: test-mtn2svn-del-ren-add-change.sh
# needs: test-mtn2svn.include
# 
# Test for converting from Monotone to Subversion and back to Monotone again.
# Check for errors: It dropps informations on changed files, if other file
# was 'removed', 'deleted' or 'added'.
#
# After this script the Monotone changelog "test1.log" and "test2.log" in
# testdir should be no differ.
# A shorter testing script is 'test-mtn-svn-rename-change.sh'.
#
# No errors found.

. ./test-mtn2svn.include
monotone_setup

# Create 3 files, change, rename, delete, add something. Linear revisions.
echo "foo1" > file1.txt
echo "foo2" > file2.txt
echo "foo3" > file3.txt
mtn_exec add file*.txt
mtn_exec commit --message "initial commit"

mv file2.txt file2b.txt
echo "bar1 (this will be missing later)" > file1.txt
mtn_exec rename file2.txt file2b.txt
mtn_exec commit --message "File1 changed, File2 renamed"

echo "touch file1 again" > file1.txt
mtn_exec commit --message "change file 1 again"

mv file2b.txt file2c.txt
echo "bar2 change after rename" > file2c.txt
mtn_exec rename file2b.txt file2c.txt
mtn_exec commit --message "File2 renamed and changed"

echo "touch file2c again" > file2c.txt
mtn_exec commit --message "change file 2 again"

rm file3.txt
echo "touch file1, rename file2 and delete file3 (the change will be lose later)" > file1.txt
mtn_exec rename file2c.txt file2d.txt
mtn_exec drop file3.txt
mtn_exec commit --message "File1 changed, File2 renamed, File3 deleted"

rm file2d.txt
echo "touch file1 and delete file2 (the change will be lose later)" > file1.txt
mtn_exec drop file2d.txt
mtn_exec commit --message "File1 changed, File2 deleted"

echo "touch file1" > file1.txt
mtn_exec commit --message "change file 1, to see the missing"

echo "touch file1, add file4 (the change will be lose later)" > file1.txt
echo "foo4" > file4.txt
mtn_exec add file4.txt
mtn_exec commit --message "change file 1, add file4"

echo "touch file1 at last" > file1.txt
mtn_exec commit --message "change file 1 as last, to see the missing"

testing_runs
