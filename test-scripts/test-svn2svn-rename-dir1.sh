#!/bin/sh

# File: test-svn2svn-rename-dir1.sh
# needs: test-svn2svn.include
#
# Test for converting revisions from Subversion to Subversion self.
# Simple dir rename.

. ./test-svn2svn.include
subversion_setup

mkdir dira
svn add dira
svn commit --message "initial commit"

svn mv dira dirb
svn commit --message "simple rename directory"

testing_runs
