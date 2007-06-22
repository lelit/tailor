#!/bin/sh

# File: test-mtn2svn2-propagate1.sh
# needs: test-mtn2svn2.include
# 
# Test for converting revisions from Monotone to Subversion and back to
# Monotone again.
# Testings with two brancehs and merges.
#
# Henry (at) Bigfoot.de

. ./test-mtn2svn2.include
monotone_setup

# Create 2 files, create multiple heads and merge it
echo "foo1" > file1.txt
echo "bar1" > file2.txt
mtn_exec add file*.txt
mtn_exec commit --key="key-dummy" --message "initial commit"

echo "foo2" > file1.txt
mtn_exec commit --message "File1 changed, 2nd"

echo "foo3" > file1.txt
mtn_exec commit --message "File1 changed 3th"

# Save this resvisions-number for later use
# get current revision for adding some more to the revision
head3=`mtn_exec automate get_base_revision_id`

echo "foo4" > file1.txt
mtn_exec commit --message "File1 changed 4th"

echo "foo5" > file1.txt
mtn_exec commit --message "File1 changed 5th"
head5=`mtn_exec automate get_base_revision_id`

# Go back to an older revs
mtn_exec update --revision $head3

# Make a side walk, create new branch
echo "bar2" > file2.txt
mtn_exec commit --branch=B --message "File2 changed, new branch"

echo "bar3" > file2.txt
mtn_exec commit --message "File2 changed"

# Merge both heads, should be automatic, because changed different files
mtn_exec propagate A B
mtn_exec update

## Final touch all
echo "touch file1 again" > file1.txt
echo "touch file2 again" > file2.txt
mtn_exec commit --message "change files again"

testing_runs
