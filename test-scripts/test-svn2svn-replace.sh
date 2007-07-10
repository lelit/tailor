#!/bin/sh

# File: test-svn2svn-replace.sh
# needs: test-svn2svn.include
# 
# Test for converting from Subversion to Subversion self.
# Special: replace a renamed file with newer file.

# ... found in source. Check, that is working after code modifing ...
#
# In svn parlance, 'R' means Replaced: a typical
# scenario is
#   $ svn mv a.txt b.txt
#   $ touch a.txt
#   $ svn add a.txt

# Dosn't work. File a.txt will be losed, see different logs:

# Source:                                 | Target:
# ----------------------------------------| --------------------------------------
# Changed paths:                          | Changed paths:
# R /project/a.txt                        | D /project/a.txt
# A /project/b.txt (from /proj-a/a.txt:2) | A /project/b.txt (from /prj-a/a.txt:2)

# Problem: a.txt was sorted before b.txt and tailer reoprted it as
# "add a.txt" and than "mv a.txt b.txt"
#
# Fixed now: Append all "replacements" at the end, after renames.

. ./test-svn2svn.include
subversion_setup

echo "foo" > a.txt
svn add a.txt
svn commit --message "initial commit"

svn mv a.txt b.txt
echo "bar" > a.txt
svn add a.txt
svn commit --message "second commit"

testing_runs
