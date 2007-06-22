#!/bin/sh

# File: test-mtn2svn-two-files.sh
# needs: test-mtn2svn.include
#
# No errors found.

. ./test-mtn2svn.include
monotone_setup

# Create two files and 4 revisions, simple linear revisions

echo "foo" > file1.txt
mtn_exec add file1.txt
mtn_exec commit --message "initial commit"

echo "second file" > file2.txt
mtn_exec add file2.txt
mtn_exec commit --message "add file"

echo "bar" > file1.txt
mtn_exec commit --message "change file"

echo "whatever" > file1.txt
mtn_exec commit --message "change file again"

testing_runs
