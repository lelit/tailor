#!/bin/sh
#
# Copyright (C) 2008 Walter Franzini
#

here=`pwd`

#
# Add the development dir to the PATH
#
PATH=$here:$PATH
export PATH

pass()
{
    exit 0
}

fail()
{
    echo "FAILED: $activity"
    exit 1
}

no_result()
{
    echo "NO_RESULT: $activity"
    exit 2
}

work=${TMPDIR-/tmp}/TAILOR.$$
mkdir $work
if test $? -ne 0; then no_result; fi

cd $work

activity="darcs setup"
mkdir $work/darcs-repo > log 2>&1
if test $? -ne 0; then cat log; no_result; fi

darcs initialize --repodir=$work/darcs-repo > log 2>&1
if test $? -ne 0; then cat log; no_result; fi

activity="create foo"
cat > $work/darcs-repo/foo.txt <<EOF
A simple text file
EOF
if test $? -ne 0; then no_result; fi

darcs add foo.txt --repodir=$work/darcs-repo > log 2>&1
if test $? -ne 0; then cat log; no_result; fi

darcs record --repodir=$work/darcs-repo -a -A Nobody -m "initial commit" \
    > log 2>&1
if test $? -ne 0; then cat log; no_result; fi

cat > $work/darcs-repo/foo.txt <<EOF
A simple text file
wit some more text.
EOF
if test $? -ne 0; then no_result; fi

darcs record --repodir=$work/darcs-repo -a -A Nobody --ignore-time \
    -m "second commit" > log 2>&1
if test $? -ne 0; then cat log; no_result; fi

cat > $work/darcs-repo/foo.txt <<EOF
A simple text file
wit some more text.
more text again!
EOF
if test $? -ne 0; then no_result; fi

darcs record --repodir=$work/darcs-repo -a -A Nobody --ignore-time \
    -m "third commit" > log 2>&1
if test $? -ne 0; then cat log; no_result; fi

#
# Initialize the aegis repository
#

unset AEGIS_PROJECT
unset AEGIS_CHANGE
unset AEGIS_PATH
unset AEGIS
umask 022

LINES=24
export LINES
COLS=80
export COLS

USER=${USER:-${LOGNAME:-`whoami`}}

PAGER=cat
export PAGER
AEGIS_FLAGS="delete_file_preference = no_keep; \
        lock_wait_preference = always; \
        diff_preference = automatic_merge; \
        pager_preference = never; \
        persevere_preference = all; \
        log_file_preference = never; \
        default_development_directory = \"$work\";"
export AEGIS_FLAGS
AEGIS_THROTTLE=-1
export AEGIS_THROTTLE

# This tells aeintegratq that it is being used by a test.
AEGIS_TEST_DIR=$work
export AEGIS_TEST_DIR

if test $? -ne 0; then exit 2; fi

AEGIS_DATADIR=$here/lib
export AEGIS_DATADIR

AEGIS_MESSAGE_LIBRARY=$work/no-such-dir
export AEGIS_MESSAGE_LIBRARY
unset LANG
unset LANGUAGE
unset LC_ALL

AEGIS_PROJECT=example
export AEGIS_PROJECT
AEGIS_PATH=$work/lib
export AEGIS_PATH

mkdir $AEGIS_PATH

chmod 777 $AEGIS_PATH
if test $? -ne 0; then no_result; cat log; fi

workproj=$work/foo.proj
workchan=$work/foo.chan

activity="new project"
aegis -npr $AEGIS_PROJECT -version "" -lib $AEGIS_PATH \
    -dir $workproj/ > log 2>&1
if test $? -ne 0; then cat log; no_result; fi

activity="project_acttributes"
cat > $work/pa <<EOF
description = "A bogus project created to test tailor functionality.";
developer_may_review = true;
developer_may_integrate = true;
reviewer_may_integrate = true;
default_test_exemption = true;
develop_end_action = goto_awaiting_integration;
EOF
if test $? -ne 0 ; then no_result; fi

aegis -pa -f $work/pa > log 2>&1
if test $? -ne 0 ; then cat log; no_result; fi

#
# add the staff
#
activity="staff 62"
aegis -nd $USER > log 2>&1
if test $? -ne 0 ; then cat log; no_result; fi
aegis -nrv $USER > log 2>&1
if test $? -ne 0 ; then cat log; no_result; fi
aegis -ni $USER > log 2>&1
if test $? -ne 0 ; then cat log; no_result; fi

#
# tailor config
#
cat > $work/tailor.conf <<EOF
[DEFAULT]
verbose = True
Debug = True

[project]
patch-name-format = %(revision)s
root-directory = $PWD/rootdir
source = darcs:source
target = aegis:target

[darcs:source]
repository = $work/darcs-repo
#module = project
subdir = darcs1side

[aegis:target]
module = $AEGIS_PROJECT
subdir = aegisside
EOF
if test $? -ne 0; then no_result; fi

activity="run tailor"
python $here/tailor -c $work/tailor.conf > log 2>&1
if test $? -ne 0; then cat log; fail; fi

activity="check aegis project history"
aegis -list project_history -unformatted
if test $? -ne 0; then cat log; no_result; fi

pass
