#!/bin/sh

# File: test-mtn2svn-rename-dir4.sh
# needs: test-mtn2svn.include
# 
# Test from Monotone to Subversion and back to Monotone again,
# to rename directories and changing files.
#
# ERROR:
# Failure applying upstream changes: testdir/rootdir/svnside $ svn commit --file /tmp/tailordhhT7esvn . returned status 1 saying
# svn: Commit failed (details follow):
# svn: Working copy 'testdir/rootdir/svnside/dirb2/subdir' is missing or not locked
# 
# Fixed by patch: svn-rename-directory-hacking2.patch


. ./test-mtn2svn.include
monotone_setup

# Create files, rename directories

mkdir dira
mkdir dira/subdir
mkdir dirb
mkdir dirb/subdir
mkdir dirb/subdir/otherdir
echo "foo" > dira/file1.txt
echo "foo" > dirb/subdir/file2.txt
mtn_exec add dira/file1.txt dirb/subdir/file2.txt
mtn_exec commit --message "initial commit"

mtn_exec rename dira dira2
mtn_exec rename dirb dirb2
mtn_exec commit --message "rename directory where exist subdirs"

testing_runs
