#!/bin/sh

# File: test-svn2svn-rename-change.sh
# needs: test-svn2svn.include
# 
# Test for converting from Subversion to Subversion self,
# with rename and change the same file.
#
# No errors found.

. ./test-svn2svn.include
subversion_setup

# Create one file and 2 revisions, simple linear revisions

echo "foo" > a.txt
svn add a.txt
svn commit --message "initial commit"

echo "bar" > a.txt
svn mv --force a.txt b.txt
svn commit --message "rename file, change file"

testing_runs
