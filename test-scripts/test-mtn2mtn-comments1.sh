#!/bin/sh

# File: test-mtn2mtn-comments1.sh
# needs: test-mtn2mtn.include
# 
# Test for changelog parser (special comments).
#
# No errors found.

. ./test-mtn2mtn.include
monotone_setup

echo "foo" > file.txt
mtn_exec add file.txt
mtn_exec commit --message "initial commit"

# get current revision for adding some more to the revision
head=`mtn_exec automate get_base_revision_id`

mtn_exec comment $head "This is a comment"
mtn_exec comment $head "And a second comment
with more
lines"

mtn_exec comment $head "Special 'comment'
\"\"\"
with \"marked\" text
in any \"lines\"
\"\"\""

testing_runs
