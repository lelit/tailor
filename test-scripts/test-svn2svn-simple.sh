#!/bin/sh

# File: test-svn2svn-simple.sh
# needs: test-svn2svn.include
# 
# Test for converting from Subversion to Subversion self.
# Create one file and 2 revisions, simple linear revisions.

. ./test-svn2svn.include
subversion_setup

echo "foo" > file.txt
svn add file.txt
svn commit --message "initial commit"

echo "bar" > file.txt
svn commit --message "second commit"

testing_runs
