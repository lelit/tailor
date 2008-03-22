#!/bin/sh

# File: test-darcs2git-foo-to-foo-slash-bar.sh
# needs: test-darcs2git.include
#
# Test for converting from Darcs to Git.
# Moves foo to foo/bar

. ./test-darcs2git.include
darcs_setup

echo "foo" > foo
darcs add foo
darcs record -v -a -A Nobody -m "add foo"

echo "bar" >> foo
darcs record -v -a -A Nobody -m "update foo"

testing_runs
