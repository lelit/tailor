#!/bin/sh

# File: test-mtn2svn-rename-dir1.sh
# needs: test-mtn2svn.include
# 
# Test from Monotone to Subversion and back to Monotone again,
# to rename directory with files into.
#
# Ticket #97: fails on "rename(absnew + '-TAILOR-HACKED-TEMP-NAME', absnew)"
#
# No errors found.

. ./test-mtn2svn.include
monotone_setup

# Create one file and 2 revisions, simple linear revisions

mkdir dira
echo "foo" > dira/file.txt
mtn_exec add dira/file.txt
mtn_exec commit --message "initial commit"

mtn_exec rename dira dirb
mtn_exec commit --message "rename directory"

testing_runs
