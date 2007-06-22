#!/bin/sh

# File: test-mtn2svn-dir-rename-delete1.sh
# needs: test-mtn2svn.include
# 
# Test converting revisions from Monotone to Subversion and back to Monotone again.
# Special: Remove directory after moving files from there.
# Tailer needs to rename file first, than remove directory!
# A more complexe testing script is 'test-mtn2svn-dir-rename-delete2.sh'
#
# ERROR 1: Fixed by 'monotone-dir-move-and-del.patch'
# ERROR 2: Needs to be fix in the svn parser

# ERROR 1:
# --------
# 2007-06-16 14:46:06 CRITICAL: Cannot rename 'testdir/rootdir/svnside/file' back to 'testdir/rootdir/svnside/somedir/file'
# 2007-06-16 14:46:06    ERROR: Failure replaying: Revision: c85d76cc6d99fae438caaa16e4c7f7238a9c17ce
# Date: 2007-06-16 12:46:02+00:00
# Author: key-dummy
# Entries: somedir(DEL at c85d76cc6d99fae438caaa16e4c7f7238a9c17ce), file(REN from somedir/file)
# Log: changes
# 
# linearized ancestor: e8713b95b73fc42b353f07454849d4b517104167
# real ancestor(s): e8713b95b73fc42b353f07454849d4b517104167
# Traceback (most recent call last):
#   File "tailor-0.9.28-henry/vcpx/target.py", line 117, in replayChangeset
#     self._replayChangeset(changeset)
#   File "tailor-0.9.28-henry/vcpx/target.py", line 320, in _replayChangeset
#     action(group)
#   File "tailor-0.9.28-henry/vcpx/target.py", line 477, in _renameEntries
#     self._renamePathname(e.old_name, e.name)
#   File "tailor-0.9.28-henry/vcpx/repository/svn.py", line 732, in _renamePathname
#     rename(newpath, oldpath)
# OSError: [Errno 2] No such file or directory

# >>> output from "mtn diff" >>>
# delete "somedir"
# 
# rename "somedir/file"
#     to "file"
# <<< end <<<

# ERROR 2:
# --------
# Changelog are different. The "rename somedir/file file" will list as
# "delete somedir/file" and "add file".
# This error comes from svn to monotone (the svn parser).
#
# File state is OK. Only the log is not complete.

. ./test-mtn2svn.include
monotone_setup

# Create dirs, files, 2 revisions

mkdir "somedir"
touch "somedir/file"

mtn_exec add * --recursive
mtn_exec commit --message "initial commit"

# file renames
mtn_exec rename "somedir/file" "file"

# dir deletes
mtn_exec drop "somedir"

mtn_exec commit --message "changes"

testing_runs
