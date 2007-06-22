#!/bin/sh

# File: test-mtn2mtn-#113-directory-deletion-and-rename.sh
# needs: test-mtn2mtn.include
# 
# Test from Monotone to Monotone self,
# to moving files and than delete directory
#
# Ticket #113: Fixed.

. ./test-mtn2mtn.include
monotone_setup

# Create files, rename directories

mkdir dir1
touch dir1/a
touch dir1/b
mkdir dir2
mtn_exec add dir1/a dir1/b dir2
mtn_exec commit --message "initial commit"

# Ticket #113:
# * rename dir1/a dir2/a
# * rename dir1/b dir2/b
# * delete dir1

mtn_exec rename dir1/a dir2/a
mtn_exec rename dir1/b dir2/b
mtn_exec drop dir1
mtn_exec commit --message "Move files and than directory"

testing_runs
