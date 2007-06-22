#!/bin/sh

# File: test-svn2svn-rename-dir2.sh
# needs: test-svn2svn.include
#
# Test for converting revisions from Subversion to Subversion self.
# Reneme dir names where a file exists.

. ./test-svn2svn.include
subversion_setup

mkdir dira
echo "foo" > dira/a.txt
svn add dira
svn commit --message "initial commit"

svn mv dira dirb
svn commit --message "rename directory with an existing file"

testing_runs
