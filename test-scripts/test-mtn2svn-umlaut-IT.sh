#!/bin/sh

# File: test-mtn2svn-umlaut-IT.sh
# needs: test-mtn2svn.include
# 
# Test for converting from Monotone to Subversion and back to Monotone again.
#
# Works after fixup LANG and using "automate certs" inside Tailor.

. ./test-mtn2svn.include

monotone_setup

# Create one file and 2 revisions, simple linear revisions

# Setup with locale DE
export LANG="de_DE.UTF-8"

echo "Umlaut ä ö ü ß Ä Ö Ü" > file.txt
mtn_exec add file.txt
mtn_exec commit --message "initial commit, Umlauts in file"

echo "foo" > file.txt
mtn_exec commit --message "change file (Umlauts ä ö ü ß Ä Ö Ü in changelog)"

# Test Tailor with locale IT now
export LANG="it_IT.UTF-8"

testing_runs
