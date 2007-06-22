#!/bin/sh

# File: test-mtn2mtn-umlaut-locale2.sh  UNICODE file !
# needs: test-mtn2mtn.include
# 
# Test for converting from Monotone to Monotone self,
# with umlauts in changelog. Uses *YOUR* locale.
#
# No errors found. Works for german (DE), italia (IT).

. ./test-mtn2mtn.include
monotone_setup

echo "foo" > file.txt
mtn_exec add file.txt
mtn_exec commit --message "Umlauts ä ö ü ß Ä Ö Ü in changelog"

testing_runs
