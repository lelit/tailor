#!/bin/sh

# File: test-darcs2git-foo-to-foo-slash-bar.sh
# needs: test-darcs2git.include
#
# Test for converting from Darcs to Git.
# Moves foo to foo/bar

. ./test-darcs2git.include
darcs_setup

touch foo
darcs add foo
darcs record -v -a -A Nobody -m "add foo"

darcs mv foo bar
mkdir foo
darcs add foo
darcs mv bar foo/bar
darcs record -v -a -A Nobody -m "move foo to foo/bar"

testing_runs
