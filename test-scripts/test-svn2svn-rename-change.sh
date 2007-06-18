#!/bin/bash -v

# File: test-svn2svn-simple.sh
# needs: test-svn2svn.include
# 
# Test for converting from Subversion to Subversion self,
# with rename and change the same file.
#
# No errors found.

. ./test-svn2svn.include
subversion_setup

# checkout initial version
svn checkout file://$POSITORY/project-a my-project
cd my-project

# Create one file and 2 revisions, simple linear revisions

echo "foo" > file.txt
svn add file.txt
svn commit --message "initial commit"

echo "bar" > file.txt
svn mv --force file.txt file.new
svn commit --message "rename file, change file"

testing_runs
