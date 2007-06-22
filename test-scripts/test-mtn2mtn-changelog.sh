#!/bin/sh

# File: test-mtn2mtn-changelog.sh
# needs: test-mtn2mtn.include
# 
# Test the new changelog parser (multiple lines, and " and \ " in there)
#
# No errors found.

. ./test-mtn2mtn.include
monotone_setup

echo "foo" > file.txt
mtn_exec add file.txt
mtn_exec commit --message "initial commit with specials in changelog

- with more lines, and
- a mail@domain.com address

\"
Yes, hacked also a nacked '\"'
in the singe line and one empty line before :-)
\"
"

testing_runs
