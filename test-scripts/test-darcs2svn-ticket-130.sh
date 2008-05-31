#!/bin/sh

. $(dirname $0)/test-darcs2svn.include

darcs_setup

echo foo >file
mkdir subdir
darcs add file subdir
darcs record -v -a -A Nobody -m "initial state"

darcs mv file subdir
darcs mv subdir newsubdir
darcs record -v -a -A Nobody -m "move file into subdir and renamed the latter"

testing_runs
