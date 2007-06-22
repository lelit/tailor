#!/bin/sh

# File: test-mtn2mtn-umlaut1.sh  UNICODE file !
# needs: test-mtn2mtn.include
# 
# Test for converting from Monotone to Monotone self,
# with umlauts in file. Uses *YOUR* locale.
#
# No errors found. (tested german DE, italia IT)

. ./test-mtn2mtn.include
monotone_setup

echo "Umlauts in file ä ö ü ß Ä Ö Ü" > file.txt
mtn_exec add file.txt
mtn_exec commit --message "initial commit, file with Umlauts"

testing_runs
