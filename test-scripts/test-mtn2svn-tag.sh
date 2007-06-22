#!/bin/sh

# File: test-mtn2svn-tag.sh
# needs: test-mtn2svn.include
# 
# Test for converting 3 revisions with 1 tag from Monotone to Subversion
# and back. Diff between test1.log and test2.log should no have
# minimal difference.
#
# TODO: Tags not supported for subversion source.

. ./test-mtn2svn.include
monotone_setup

# Create one file and 3 revisions, simple linear revisions

echo "foo" > file.txt
mtn_exec add file.txt
mtn_exec commit --message "initial commit"

echo "bar" > file.txt
mtn_exec commit --message "second commit with tag"

head=`mtn_exec automate get_base_revision_id`
mtn_exec tag $head "Tagged-with-number-1.0"

testing_runs
