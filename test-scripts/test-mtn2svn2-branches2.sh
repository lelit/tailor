#!/bin/sh

# File: test-mtn2svn2-branches2.sh
# needs: test-mtn2svn2.include
# 
# Test for converting revisions from Monotone to Subversion and back to
# Monotone again.
# Checks multiple branches and merge.
#
# No merges, because it's to simple. See next script.
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

# Make a side walk in a new branch
echo "bar2" > file2.txt
mtn_exec commit --branch=B --message "File2 changed, create branch B"

echo "bar3" > file2.txt
mtn_exec commit --message "File2 changed"

# go back to older commit and change other file to have two heads
cd ..
mtn_exec --db=test1.mtn co --branch=A monotone-work-a  # --revision $head3
cd monotone-work-a

echo "foo6" > file1.txt
mtn_exec commit --key="key-dummy" --message "File1 changed"

# Merge both branches, should be automatic, because changed different files
mtn_exec propagate B A
mtn_exec update

## Final touch all
echo "touch file1 again" > file1.txt
echo "touch file2 again" > file2.txt
mtn_exec commit --message "change files again"

testing_runs
