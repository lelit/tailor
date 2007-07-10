#!/bin/sh

# File: test-svn2svn-#113-directory-deletion-and-rename.sh
# needs: test-svn2svn.include
# 
# Test for converting revisions from Subversion to Subversion self
# to moving files and than delete directory
# 
# small ERROR (found by compair the logs):
# The source from "rename" will be lose. Subversion deletes the old path and creates the file as new in other path.
#
# First log:
#   Changed paths:
#      D /project/dir1
#      A /project/dir2/a (from /project/dir1/a:2)
#      A /project/dir2/b (from /project/dir1/b:2)
#
# second log:
#   Changed paths:
#      D /project/dir1
#      A /project/dir2/a
#      A /project/dir2/b
#   
# ####
#
# Was an old error in log and is OK now.


. ./test-svn2svn.include
subversion_setup

# Ticket #113:
# * rename dir1/a dir2/a
# * rename dir1/b dir2/b
# * delete dir1

mkdir dir1
touch dir1/a
touch dir1/b
mkdir dir2
svn add dir1 dir2
svn commit --message "initial commit"

svn rename dir1/a dir2/a
svn rename dir1/b dir2/b
svn delete dir1
svn commit --message "file and directory removed after moving files outside"

testing_runs
