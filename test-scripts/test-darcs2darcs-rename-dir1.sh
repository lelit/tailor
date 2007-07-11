#!/bin/sh

# File: test-darcs2darcs-rename-dir1.sh
# needs: test-darcs2darcs.include
#
# Test for converting from Darcs to Darcs self.
# Simple dir rename.

. ./test-darcs2darcs.include
darcs_setup

mkdir dira
darcs add dira
darcs record -a -A Nobody -m "initial commit"

darcs mv dira dirb
darcs record -a -A Nobody --ignore-times -m "simple rename directory"

testing_runs
