#!/bin/sh

# File: test-svn2svn-rename-dir5.sh
# needs: test-svn2svn.include
#
# Test for converting revisions from Subversion to Subversion self.
# Renameing singe directory name, without moving trees.
#
# ERROR:
#  File "tailor-0.9.28/vcpx/target.py", line 528, in _renameEntries
#    rename(absnew + '-TAILOR-HACKED-TEMP-NAME', absnew)

# ERROR:
# svn commit --message "inner dir renamed: dir/subdir dir/subdir2"
# Deleting       dir/subdir
# svn: Commit failed (details follow):
# svn: Out of date: '/project-a/dir/subdir' in transaction '3-1'
#
# Fixed by patch: svn-rename-directory-hacking2.patch

. ./test-svn2svn.include
subversion_setup

mkdir -p topdir/subdir/otherdir/moredir
echo "foo" > topdir/file1.txt
echo "foo" > topdir/subdir/file2.txt
echo "foo" > topdir/subdir/otherdir/moredir/file3.txt
svn add *
svn commit --message "initial commit"

svn mv --force topdir/subdir/otherdir/moredir topdir/subdir/otherdir/moredir1
svn commit --message "end of tree dir renamed: topdir/subdir/otherdir/moredir --> topdir/subdir/otherdir/moredir1"

# The follow commands have a bug in SVN!
# Can't rename after the commit the line before? Only one of these commits works. Don't know why.
# ERROR message from svn:
#   svn commit --message "inner dir renamed: topdir/subdir --> topdir/subdir2 (this would fails on SVN 1.3.0)"
#   Deleting       dir/subdir
#   svn: Commit failed (details follow):
#   svn: Out of date: '/project-a/dir/subdir' in transaction '3-1'

#svn mv topdir/subdir topdir/subdir2
#svn commit --message "inner dir renamed: topdir/subdir --> topdir/subdir2 (this would fails on SVN 1.3.0)"

#svn mv --force topdir topdir3
#svn commit --message "top dir renamed: topdir --> topdir3"

testing_runs
