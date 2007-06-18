#!/bin/bash -v

# File: test-svn2svn-rename-dir6.sh
# needs: test-svn2svn.include
# 
# Test for converting revisions from Subversion and to Subversion.
# 
# ERROR 1:
# --------
# Failure applying upstream changes: testdir/rootdir/svn2side $ svn commit --file /tmp/tailorBozvbYsvn . returned status 1 saying
# svn: Commit failed (details follow):
# svn: Working copy 'svn2side/dir2/subdir' is missing or not locked
#
# Fixed by patch: svn-rename-directory-hacking2.patch
#
# ERROR 2:
# --------
# small ERROR (found by compair the logs):
# The source from "rename" will be lose. Subversion deletes the old path and
# creates the file as new in other path.
# See also "test-svn2svn-#113-directory-deletion-and-rename.sh".
#
# File state is OK. Only the log is not complete.

. ./test-svn2svn.include
subversion_setup

# checkout initial version
svn checkout file://$POSITORY/project-a my-project
cd my-project

# Create one file and 2 revisions, rename directorys where subdirs exist

mkdir dir
mkdir dir/middledir
mkdir dir/middledir/otherdir
echo "foo" > dir/middledir/otherdir/file.txt
svn add *
svn commit --message "initial commit"

svn rename --force dir/middledir/otherdir dir/otherdir
svn delete --force dir/middledir
svn commit --message "dir renamed: dir/middledir/otherdir --> dir/otherdir (remove 'middledir')"

mkdir dir/innerdir
svn add dir/innerdir
svn commit --message "create new 'innerdir'"

svn rename --force dir/otherdir dir/innerdir/otherdir
svn commit --message "dir renamed: dir/otherdir --> dir/innerdir/otherdir"

testing_runs
