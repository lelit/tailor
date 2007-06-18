#!/bin/bash -v

# File: test-mtn2mtn-umlaut-locale2.sh  UNICODE file !
# needs: test-mtn2mtn.include
# 
# Test for converting from Monotone to Monotone self,
# with umlauts in changelog. Uses *YOUR* locale.
#
# After fixup LANG and using "automate certs" inside Tailor
# works for german (DE), italia (IT).
#
# Log-diff: PASS

. ./test-mtn2mtn.include
monotone_setup

# Create one file and one revision

echo "foo" > file.txt
mtn_exec add file.txt
mtn_exec commit --message "Umlauts ä ö ü ß Ä Ö Ü in changelog"

testing_runs
