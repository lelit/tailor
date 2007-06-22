#!/bin/sh

# File: test-mtn2svn-tags.sh
# needs: test-mtn2svn.include
# 
# Test for converting 5 revisions with 1+2 tags from Monotone to Subversion and back.
# Diff between test1.log and test2.log should no have difference.
#
# TODO: Tags not supported for subversion source.

. ./test-mtn2svn.include
monotone_setup

# Create one file and 3 revisions, simple linear revisions

echo "foo" > file.txt
mtn_exec add file.txt
mtn_exec commit --message "initial commit"

echo "bar" > file.txt
mtn_exec commit --message "second commit, with a tag"

head=`mtn_exec automate get_base_revision_id`
mtn_exec tag $head "Tagged/with number-1.0"

echo "third" > file.txt
mtn_exec commit --message "third commit"

echo "4th" > file.txt
mtn_exec commit --message "4th commit, with two tags"

head=`mtn_exec automate get_base_revision_id`
mtn_exec tag $head "Tagged with number 4.0"
mtn_exec tag $head "Tagged again 4.0.1"

echo "5th" > file.txt
mtn_exec commit --message "5th commit"

testing_runs
