#!/bin/sh

# File: test-mtn2svn2-propagate2.sh
# needs: test-mtn2svn2.include
# 
# Test for converting revisions from Monotone to Subversion and back to
# Monotone again.
# Checking propagate, branches, merge and multiple keys. More complicated.
#
# Henry (at) Bigfoot.de

. ./test-mtn2svn2.include
monotone_setup

# Create 2 files,
# create 2 branches and propagate and merge it,
# create 2 heads from there and merge it,
# works with 2 keys (simulate two different users)
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
mtn_exec commit --key="other-dummy" --branch=B --message "File2 changed, new branch, other key"

echo "bar3" > file2.txt
mtn_exec commit --message "File2 changed"
head6=`mtn_exec automate get_base_revision_id`

# Merge both branches, should be automatic, because changed different files
mtn_exec propagate A B

mtn_exec update

# Go back to an older revs (before the propagate)
mtn_exec update --revision $head6

echo "bar4" > file2.txt
mtn_exec commit --key="key-dummy" --message "File2 changed, multiple heads now, first key"

echo "bar5" > file2.txt
mtn_exec commit --key="key-dummy" --message "File2 changed again"

# Merge both heads, should be automatic, because changed different files
mtn_exec merge
mtn_exec update

## Final touch all
echo "touch file1 again" > file1.txt
echo "touch file2 again" > file2.txt
mtn_exec commit --key="other-dummy" --message "change files again, other key"
head7=`mtn_exec automate get_base_revision_id`

# Go back to branch A
mtn_exec update --revision $head5

echo "foo6" > file1.txt
mtn_exec commit --key="key-dummy" --message "File1 changed, 6th, first key"

testing_runs
