#!/bin/sh

# File: test-mtn2mtn-umlaut-POSIX.sh  UNICODE file !
# needs: test-mtn2mtn.include
# 
# Test for converting from Monotone to Monotone self.
#
# FAILS: Can not commit changelog to monotone

. ./test-mtn2mtn.include
monotone_setup

# Create one file and 2 revisions, simple linear revisions

# Must be German, because testing Umlauts here (in html &auml; &ouml; ...)
export LANG="de_DE.UTF-8"

echo "Umlaut ä ö ü ß Ä Ö Ü" > file.txt
mtn_exec add file.txt
mtn_exec commit --message "initial commit, Umlauts in file"

echo "foo" > file.txt
mtn_exec commit --message "change file (Umlauts ä ö ü ß Ä Ö Ü in changelog)"

# Test Tailor with POSIX
export LANG="POSIX"

testing_runs
