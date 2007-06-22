#!/bin/sh

# File: test-mtn2svn-dir-rename-delete2.sh
# needs: test-mtn2svn.include
# 
# Test converting revisions from Monotone to Subversion and back to Monotone again.
# Special: Remove directory after moving files from there.
# Tailer needs to rename file first, than remove directory!
#
# ERROR 1: Fixed by 'monotone-dir-move-and-del.patch'
# ERROR 2: Needs to be fix in svn parser

# ERROR 1:
# --------
# >>> output from "mtn diff" is >>>
# delete "otherdir"
# 
# delete "otherdir/subdir"
# 
# delete "somedir"
# 
# rename "otherdir/subdir/bfile"
#     to "bfile"
# 
# rename "somedir/afile"
#     to "afile"
# <<< end <<<

# ERROR 2:
# --------
# Changelog are different. All "rename" will list as "delete" and "add".
# This error comes from svn to monotone (the svn parser).
#
# File state is OK. Only the log is not complete.

. ./test-mtn2svn.include
monotone_setup

# Create dirs, files, 2 revisions

mkdir "dummydir"
mkdir "somedir"
touch "somedir/afile"

mkdir -p "otherdir/subdir"
touch    "otherdir/subdir/bfile"

mtn_exec add * --recursive
mtn_exec commit --message "initial commit"

# file moved to upper dir
mtn_exec rename "somedir/afile" "afile"
mtn_exec rename "otherdir/subdir/bfile" "bfile"

# dir deletes (single or recursive, does no matter)
#mtn_exec drop "dummydir"
#mtn_exec drop "somedir"
#mtn_exec drop "otherdir/subdir"
#mtn_exec drop "otherdir"

mtn_exec drop --recursive "dummydir" "somedir" "otherdir"

mtn_exec commit --message "chang it"

testing_runs
