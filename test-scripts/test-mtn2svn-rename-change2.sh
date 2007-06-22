#!/bin/sh

# File: --messtest-mtn2svn-rename-change2.sh
# needs: test-mtn2svn.include
# 
# Test converting from Monotone to Subversion and back to Monotone again.
# Changeset copied from Monotone source tree revision b744591ca38f6c4e7d18594e388ca6cbb42d2af8.
#
# ERROR 1:
# --------
# Ticket #113: directory deletion and rename
# Fixed by: svn-rename-directory-hacking3.patch, monotone-dir-move-and-del.patch
#
# ERROR 2:
# --------
# After convert back from Subversion to Monotone, the dirs are added instead renamed
# This error comes from svn to monotone (the svn parser).
#
# File state is OK. Only the log is not complete.

. ./test-mtn2svn.include
monotone_setup

# Create dirs, files, 2 revisions

mkdir -p   "tests/a_tricky_cvs_repository_with_tags"
echo "1" > "tests/a_tricky_cvs_repository_with_tags/__driver__.lua"
mkdir -p   "tests/a_tricky_cvs_repository_with_tags/cvs-repository/t/libasm"
echo "1" > "tests/a_tricky_cvs_repository_with_tags/cvs-repository/t/libasm/ChangeLog,v"
mkdir -p   "tests/a_tricky_cvs_repository_with_tags/cvs-repository/t/libelf-po"
echo "1" > "tests/a_tricky_cvs_repository_with_tags/cvs-repository/t/libelf-po/POTFILES.in,v"

mkdir -p   "tests/cvs_import,_deleted_file_invariant/cvs-repository/test"
echo "1" > "tests/cvs_import,_deleted_file_invariant/cvs-repository/test/afile,v"
echo "1" > "tests/cvs_import,_deleted_file_invariant/cvs-repository/test/bfile,v"
echo "1" > "tests/cvs_import,_deleted_file_invariant/cvs-repository/test/cfile,v"
echo "1" > "tests/cvs_import,_deleted_file_invariant/__driver__.lua"

mkdir -p   "tests/cvs_import,_file_dead_on_head_and_branch/cvs-repository/test"
echo "1" > "tests/cvs_import,_file_dead_on_head_and_branch/cvs-repository/test/cvsfile,v"
echo "1" > "tests/cvs_import,_file_dead_on_head_and_branch/__driver__.lua"

mkdir -p "tests/importing_a_small,_real_cvs_repository/cvs-repository"
echo "1" > "tests/importing_a_small,_real_cvs_repository/cvs-repository/asm-tst3.c,v"
echo "1" > "tests/importing_a_small,_real_cvs_repository/cvs-repository/asm-tst4.c,v"
echo "1" > "tests/importing_a_small,_real_cvs_repository/__driver__.lua"

mkdir -p   "tests/test_problematic_cvs_import/cvs-repository/test"
echo "1" > "tests/test_problematic_cvs_import/cvs-repository/test/rcsfile,v"
echo "1" > "tests/test_problematic_cvs_import/__driver__.lua"

mkdir "contrib"
echo "1" > "contrib/monotone-notify.pl"

mtn_exec add * --recursive
mtn_exec commit --message "initial commit"

# dir renames
mtn_exec rename 'tests/a_tricky_cvs_repository_with_tags/cvs-repository'  'tests/a_tricky_cvs_repository_with_tags/e'
mtn_exec rename 'tests/cvs_import,_deleted_file_invariant/cvs-repository/test'  'tests/cvs_import,_deleted_file_invariant/attest'
mtn_exec rename 'tests/importing_a_small,_real_cvs_repository/cvs-repository'  'tests/importing_a_small,_real_cvs_repository/e'
# file renames
mtn_exec rename 'tests/cvs_import,_file_dead_on_head_and_branch/cvs-repository/test/cvsfile,v'  'tests/cvs_import,_file_dead_on_head_and_branch/cvsfile,v'
mtn_exec rename 'tests/test_problematic_cvs_import/cvs-repository/test/rcsfile,v'  'tests/test_problematic_cvs_import/rcsfile,v'
# dir deletes
mtn_exec drop 'tests/cvs_import,_deleted_file_invariant/cvs-repository'
mtn_exec drop 'tests/cvs_import,_file_dead_on_head_and_branch/cvs-repository/test'
mtn_exec drop 'tests/cvs_import,_file_dead_on_head_and_branch/cvs-repository'
mtn_exec drop 'tests/test_problematic_cvs_import/cvs-repository/test'
mtn_exec drop 'tests/test_problematic_cvs_import/cvs-repository'
# file changes
echo "2" > "contrib/monotone-notify.pl"
echo "2" > "tests/a_tricky_cvs_repository_with_tags/__driver__.lua"
echo "2" > "tests/cvs_import,_deleted_file_invariant/__driver__.lua"
echo "2" > "tests/cvs_import,_file_dead_on_head_and_branch/__driver__.lua"
echo "2" > "tests/importing_a_small,_real_cvs_repository/__driver__.lua"
echo "2" > "tests/test_problematic_cvs_import/__driver__.lua"

mtn_exec commit --message "changes from Monotone source tree"

testing_runs
