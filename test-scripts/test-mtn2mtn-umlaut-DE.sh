#!/bin/sh

# File: test-mtn2mtn-umlaut-DE.sh
# needs: test-mtn2mtn.include
# 
# Test for converting from Monotone to Monotone self, with
# umlauts in file and changelog. Uses fixed locale DE and utf-8.
#
# No errors found.

. ./test-mtn2mtn.include
monotone_setup

# Create one file and 2 revisions, simple linear revisions

# Test Tailor with locale DE now
export LANG="de_DE.UTF-8"

echo "Umlaut ä ö ü ß Ä Ö Ü" > file.txt
mtn_exec add file.txt
mtn_exec commit --message "initial commit, Umlauts in file"

echo "foo" > file.txt
mtn_exec commit --message "change file (Umlauts ä ö ü ß Ä Ö Ü in changelog)"

testing_runs
