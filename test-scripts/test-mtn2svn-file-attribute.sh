#!/bin/sh

# File: test-mtn2svn-file-attribute.sh
# needs: test-mtn2svn.include
# 
# Test for converting from Monotone to Subversion and back to Monotone again.
#
# Test to change file executable attribute.
# Don't work.  Is no problem, if the file is executabe on ADD.

. ./test-mtn2svn.include
monotone_setup

# Create one file and 2 revisions, simple linear revisions

echo "foo" > file.txt
mtn_exec add file.txt
mtn_exec commit --message "initial commit"

echo "bar" > file.txt
mtn_exec attr set file.txt mtn:execute true
mtn_exec commit --message "make file executable"

testing_runs
