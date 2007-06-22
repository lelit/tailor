#!/bin/sh

# File: test-mtn2mtn-comments2.sh
# needs: test-mtn2mtn.include
# 
# Test for converting from Monotone to Monotone self.
# It's a selfchecking for Monotone.  Diff between test1.log and test2.log
# should no have difference.
#
# Changelogs, comments and changes in diffrent ways
#
# No errors found.

. ./test-mtn2mtn.include
monotone_setup

echo "foo" > file.txt
mtn_exec add file.txt
mtn_exec commit --message "initial commit"

# get current revision for adding some more to the revision
head=`mtn_exec automate get_base_revision_id`
mtn_exec comment $head "This is a comment (for $head)"

echo "bar" > file.txt
mtn_exec commit --message "2nd commit"

head=`mtn_exec automate get_base_revision_id`
mtn_exec comment $head "And a second comment (for $head)
with more
lines"

echo "foobar" > file.txt
mtn_exec commit --message "3rd commit"

head=`mtn_exec automate get_base_revision_id`
mtn_exec comment $head "Special 'comment'
\"\"\"
with \"marked\" text
in any \"lines\"
(for $head)
\"\"\""

testing_runs
