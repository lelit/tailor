#!/bin/bash -v

# File: test-mtn2mtn-umlaut1.sh  UNICODE file !
# needs: test-mtn2mtn.include
# 
# Test for converting from Monotone to Monotone self,
# with umlauts in file. Uses *YOUR* locale.
#
# (tested german DE, italia IT)
# Log-diff: PASS


. ./test-mtn2mtn.include
monotone_setup

# Create one file and one revision

echo "Umlauts in file ä ö ü ß Ä Ö Ü" > file.txt
mtn_exec add file.txt
mtn_exec commit --message "initial commit, file with Umlauts"

testing_runs
