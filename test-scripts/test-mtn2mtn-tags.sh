#!/bin/sh

# File: test-mtn2mtn-tags.sh
# needs: test-mtn2mtn.include
# 
# Test for converting 5 revisions with 1+2 tags from Monotone to Monotone self.
#
# No errors found.

. ./test-mtn2mtn.include
monotone_setup

# Create one file and 2 revisions, simple linear revisions

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
