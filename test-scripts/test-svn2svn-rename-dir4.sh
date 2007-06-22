#!/bin/sh

# File: test-svn2svn-rename-dir4.sh
# needs: test-svn2svn.include
#
# Test for converting revisions from Subversion to Subversion self.
# Renameing simple dir name, and renemaing dir names where subdirs exists.
#
# ERROR 1:
#  File "tailor-0.9.28/vcpx/target.py", line 528, in _renameEntries
#    rename(absnew + '-TAILOR-HACKED-TEMP-NAME', absnew)
#
# ERROR 2:
# Failure applying upstream changes: testdir/rootdir/svn2side $ svn commit --file /tmp/tailorBozvbYsvn . returned status 1 saying
# svn: Commit failed (details follow):
# svn: Working copy 'svn2side/dira2/subdir' is missing or not locked
#
# Fixed by patch: svn-rename-directory-hacking2.patch

. ./test-svn2svn.include
subversion_setup

mkdir dira
mkdir dira/subdira
mkdir dirb
mkdir dirb/subdirb
mkdir dirb/subdirb/otherdir
echo "foo" > dira/file1.txt
echo "foo" > dirb/subdirb/file2.txt
svn add dira dirb
svn commit --message "initial commit"

svn mv dira dira2
svn mv dirb dirb2
svn commit --message "rename directory where exist subdirs"

testing_runs
