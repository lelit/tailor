#!/bin/sh

# File: test-mtn2svn-#113-directory-deletion-and-rename.sh
# needs: test-mtn2svn.include
# 
# Test from Monotone to Subversion and back to Monotone again,
# to moving files and than delete directory
#
# ERROR 1:
# --------
# Traceback (most recent call last):
#   File "tailor-0.9.28/vcpx/target.py", line 117, in replayChangeset
#   File "tailor-0.9.28/vcpx/target.py", line 320, in _replayChangeset
#   File "tailor-0.9.28/vcpx/target.py", line 474, in _renameEntries
#   File "tailor-0.9.28/vcpx/repository/svn.py", line 633, in _renamePathname
# OSError: [Errno 2] No such file or directory
# 00:38:24 [E] Couldn't replay changeset
# Revision: 603a9ccf04cfd6ec7e991a15b51f7effe34b95bc
# Date: 2007-06-14 22:38:21+00:00
# Author: key-dummy
# Entries: dir1(DEL at 603a9ccf04cfd6ec7e991a15b51f7effe34b95bc), dir2/a(REN from dir1/a), dir2/b(REN from dir1/b)
#
# Implementation should:
# Sort the DEL and REN entries by pathname (bottom up). But must use the oldpath of REN.
# 1. REN from dir2/a
# 2. REN from dir1/a
# 3. DEL      dir1
#
# This should also work for multiple DEL of directories, for example:
# 1. REN from dir3/dir2/dir1/file
# 2. DEL      dir3/dir2/dir1
# 3. DEL      dir3/dir2
#
# Fixed with patch 'monotone-dir-move-and-del.patch'
#
# ERROR 2:
# --------
# After convert back from Subversion to Monotone, the dirs are added instead renamed
# Data ok, changelog incomplete.

. ./test-mtn2svn.include
monotone_setup

# Create files, rename directories

mkdir dir1
touch dir1/a
touch dir1/b
mkdir dir2
mtn_exec add dir1/a dir1/b dir2
mtn_exec commit --message "initial commit"

# From #113:
# * rename dir1/a dir2/a
# * rename dir1/b dir2/b
# * delete dir1

mtn_exec rename dir1/a dir2/a
mtn_exec rename dir1/b dir2/b
mtn_exec drop dir1
mtn_exec commit --message "Move files and than directory"

testing_runs
