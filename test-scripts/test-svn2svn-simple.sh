#!/bin/bash -v

# File: test-svn2svn-simple.sh
# needs: test-svn2svn.include
# 
# Test for converting 2 (3) revisions from Subversion and back to Subversion again.

. ./test-svn2svn.include
subversion_setup

# checkout initial version
svn checkout file://$POSITORY/project-a my-project
cd my-project

# Create one file and 2 revisions, simple linear revisions

echo "foo" > file.txt
svn add file.txt
svn commit --message "initial commit
more 
lines
e
r
t
z
u
i
o
as
r
r
rr
r
t"

echo "bar" > file.txt
svn commit --message "second commit"

testing_runs
