#!/bin/sh

# File: test-svn2svn-delete-dir.sh
# needs: test-svn2svn.include
# 
# Test for converting revisions from Subversion to Subversion self.
# 
# Ticket #131: monotone -> svn can't handle directory deletions
# No errors found.

. ./test-svn2svn.include
subversion_setup

# Create one file and 2 revisions, simple linear revisions

mkdir deleteme
touch deleteme/foo
svn add deleteme
svn commit --message "initial commit"

svn delete deleteme/foo
svn delete deleteme
svn commit --message "file and directory removed"

testing_runs
