#!/bin/sh

# File: test-mtn2svn-delete-dir.sh
# needs: test-mtn2svn.include
# 
# Test from Monotone to Subversion and back to Monotone again,
# to delete directories and delete file in there.
#
# Ticket #131: monotone -> svn can't handle directory deletions
# No errors found.

. ./test-mtn2svn.include
monotone_setup

mkdir deleteme
touch deleteme/foo
mtn_exec add deleteme/foo
mtn_exec commit --message "initial commit"

mtn_exec rm deleteme/foo
mtn_exec rm deleteme
mtn_exec commit --message "file and directory removed"

testing_runs
