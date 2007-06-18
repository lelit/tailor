#!/bin/bash -v

# File: test-mtn2mtn-#113-directory-deletion-and-rename.sh
# needs: test-mtn2mtn.include
# 
# Test from Monotone to Monotone self,
# to moving files and than delete directory
#
# ERROR:
# 07:45:19 [I] testdir/rootdir/mtn2side $ mtn drop --recursive -- dir1
# 07:45:19 [I] [Ok]
# Error stream:
# mtn: dropping dir1/b from workspace manifest
# mtn: dropping dir1/a from workspace manifest
# mtn: dropping dir1 from workspace manifest
# 07:45:19 [I] testdir/rootdir/mtn2side $ mtn rename -- dir1/a dir2/a
# 07:45:19 [W] [Status 1]
# Error stream:
# mtn: misuse: source file dir1/a is not versioned
# 07:45:19 [E] Failure replaying: Revision: 603a9ccf04cfd6ec7e991a15b51f7effe34b95bc
# Date: 2007-06-15 05:45:17+00:00
# Author: key-dummy
# Entries: dir1(DEL at 603a9ccf04cfd6ec7e991a15b51f7effe34b95bc), dir2/a(REN from dir1/a), dir2/b(REN from dir1/b)
# Log: remove file and than directory
# 
# linearized ancestor: 8e735146388c89dc3335c87ec40778fd13c1eb8f
# real ancestor(s): 8e735146388c89dc3335c87ec40778fd13c1eb8f
# Traceback (most recent call last):
#   File "tailor-0.9.28-henry/vcpx/target.py", line 117, in replayChangeset
#     self._replayChangeset(changeset)
#   File "tailor-0.9.28-henry/vcpx/target.py", line 320, in _replayChangeset
#     action(group)
#   File "tailor-0.9.28-henry/vcpx/target.py", line 477, in _renameEntries
#     self._renamePathname(e.old_name, e.name)
#   File "tailor-0.9.28-henry/vcpx/repository/monotone.py", line 971, in _renamePathname
#     raise ChangesetApplicationFailure(
# ChangesetApplicationFailure: testdir/rootdir/mtn2side $ mtn rename -- dir1/a dir2/a returned status 1
#----------------
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

. ./test-mtn2mtn.include
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
