#!/bin/sh

# File: test-mtn2mtn-replace.sh
# needs: test-mtn2mtn.include
#
# Test for converting 2 revisions from Monotone to Monotone self.
#
# ERROR: File a.txt will be missing in the end.

SHAREDDIR=yes

. ./test-mtn2mtn.include
monotone_setup

echo "1" > 1.txt
echo "foo" > a.txt
mtn_exec add a.txt 1.txt
mtn_exec commit --message "initial commit"

mtn_exec rename 1.txt 2.txt
mtn_exec rename a.txt b.txt

echo "bar" > a.txt
mtn_exec add a.txt
mtn_exec commit --message "second commit"

testing_runs
