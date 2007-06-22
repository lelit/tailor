#!/bin/sh

# File: test-mtn2mtn-multiple-heads.sh
# needs: test-mtn2mtn.include
# 
# Test for converting revisions from Monotone to Monotone self.
# It's a selfchecking for Monotone.  Diff between test1.log and test2.log
# should no have difference.
#
# It checks new working "automate certs" for multiple heads, Tag, Testresult,
# multi-line Changelogs, multiple Comments, multi-line Comments.
#
# ToDo: Testresult should be sort back into Monotone.
# Log-diff: differ (no support for multiple heads).

. ./test-mtn2mtn.include
monotone_setup

echo "foo1" > file1.txt
echo "foo2" > file2.txt
mtn_exec add file*.txt
mtn_exec commit --date 2007-06-01T12:00:00 --message "initial commit"

# Save this resvisions-number for later use
head1=`mtn_exec automate get_base_revision_id`
mtn_exec tag $head1 "first-head"

echo "bar1" > file1.txt
mtn_exec commit --date 2007-06-01T12:10:00 --message "File1 changed"

# go back to initial commit and change other file to have two heads
mtn_exec update --revision $head1
echo "bar2" > file2.txt
mtn_exec commit --date 2007-06-01T12:01:00 --message "File2 changed, multiple head
with more lines
and a mail@domain.com address
in changelog"
# get current revision for adding some more to the revision
head2=`mtn_exec automate get_base_revision_id`

mtn_exec tag $head2 "second-head"
mtn_exec comment $head2 "This is a comment"
mtn_exec comment $head2 "And a second comment
with more
lines"
# Set testresult
mtn_exec testresult $head2 pass 

# Merge both heads, should be automatic, because changed different files
mtn_exec merge --date 2007-06-01T12:20:00
mtn_exec update

# Final touch all
echo "touch file1 again" > file1.txt
echo "touch file2 again" > file2.txt
mtn_exec commit --date 2007-06-01T12:30:00 --message "change files again"

testing_runs
