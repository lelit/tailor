#!/bin/sh

# File: test-darcs2darcs-empty.sh
# needs: test-darcs2darcs.include
#
# http://bugs.debian.org/cgi-bin/bugreport.cgi?bug=428322

. $(dirname $0)/test-darcs2darcs.include

darcs_setup

testing_runs
