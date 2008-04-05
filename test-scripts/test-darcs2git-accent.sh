#!/bin/sh

# File: test-darcs2git-accent.sh
# needs: test-darcs2git.include
#
# Test for converting from Darcs to Git.
# This test ensures tailor won't fail if there are accents in the author
# name.

. ./test-darcs2git.include
darcs_setup

echo "foo" > foo
darcs add foo
darcs record -v -a -A "Nobodyéáõû" -m "add foo"

testing_runs
