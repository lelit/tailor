#!/bin/sh
#
# Copyright (C) 2008 Walter Franzini
#


here=`pwd`

#
# To test against the stable aegis branch add the stable executables
# directory to the PATH.  Only needed for aegis contributors.
#
aegis_stable_baseline=$(aegis -cd -p aegis.stable -bl 2> /dev/null)
if test -n "$aegis_stable_baseline"
then
    PATH=$aegis_stable_baseline/linux-i486/bin:$PATH
fi

#
# Add the development dir to the PATH
#
PATH=$here:$PATH
export PATH

pass()
{
    echo "PASSED:"
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

#
# The following function is used to check aegis metadata files.
#
check_it()
{
	sed	-e "s|$work|...|g" \
		-e 's|= [0-9][0-9]*; /.*|= TIME;|' \
		-e "s/\"$USER\"/\"USER\"/g" \
		-e 's/uuid = ".*"/uuid = "UUID"/' \
		-e 's/19[0-9][0-9]/YYYY/' \
		-e 's/20[0-9][0-9]/YYYY/' \
		-e 's/node = ".*"/node = "NODE"/' \
		-e 's/crypto = ".*"/crypto = "GUNK"/' \
	        < $2 > $work/sed.out
	if test $? -ne 0; then no_result; fi
	diff -B $1 $work/sed.out
	if test $? -ne 0; then no_result; fi
}


work=${TMPDIR-/tmp}/TAILOR.$$
mkdir $work
if test $? -ne 0; then no_result; fi

cd $work

#
# Prepare the darcs repository
#
activity="darcs setup"
mkdir $work/darcs-repo > log 2>&1
if test $? -ne 0; then cat log; no_result; fi

darcs initialize --repodir=$work/darcs-repo > log 2>&1
if test $? -ne 0; then cat log; no_result; fi

activity="create foo"
mkdir $work/darcs-repo/dir
if test $? -ne 0; then no_result; fi

cat > $work/darcs-repo/dir/foo.txt <<EOF
A simple text file
EOF
if test $? -ne 0; then no_result; fi

darcs add dir/foo.txt --repodir=$work/darcs-repo > log 2>&1
if test $? -ne 0; then cat log; no_result; fi

darcs record --repodir=$work/darcs-repo -a -A Nobody -m "initial commit" \
    > log 2>&1
if test $? -ne 0; then cat log; no_result; fi

cat > $work/darcs-repo/dir/foo.txt <<EOF
A simple text file
wit some more text.
EOF
if test $? -ne 0; then no_result; fi

cat > $work/darcs-repo/bar.txt <<EOF
This is bar.txt
EOF
if test $? -ne 0; then no_result; fi

darcs add bar.txt --repodir=$work/darcs-repo > log 2>&1
if test $? -ne 0; then cat log; no_result; fi

darcs record --repodir=$work/darcs-repo -a -A Nobody --ignore-time \
    -m "second commit" > log 2>&1
if test $? -ne 0; then cat log; no_result; fi

cat > $work/darcs-repo/dir/foo.txt <<EOF
A simple text file
wit some more text.
more text again!
EOF
if test $? -ne 0; then no_result; fi

darcs mv bar.txt baz.txt --repodir=$work/darcs-repo > log 2>&1
if test $? -ne 0; then cat log; no_result; fi

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

#
# The project is NOT created by means of tailor since it should be
# created with a different user.
#
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
python $here/tailor -c $work/tailor.conf > $work/tailor.log 2>&1
if test $? -ne 0; then cat $work/tailor.log; fail; fi

cat > $work/ok <<EOF
1 10 initial commit
2 11 second commit
3 12 third commit
EOF
if test $? -ne 0; then no_result; fi

activity="check aegis project history"
aegis -list project_history -unformatted 2> log | cut -d\  -f 1,7- > history
if test $? -ne 0; then cat history; no_result; fi

diff ok history
if test $? -ne 0; then fail; fi

#
# add more darcs changes
#
cat > $work/darcs-repo/baz.txt <<EOF
A simple text file
wit some more text.
more text again!
ancora piu\` test
EOF
if test $? -ne 0; then no_result; fi

darcs remove dir/foo.txt --repodir=$work/darcs-repo > log 2>&1
if test $? -ne 0; then cat log; no_result; fi

cat > $work/logfile <<EOF
fourth commit
This text is now
the description of the aegis change
splitted on multiple lines.
EOF
if test $? -ne 0; then no_result; fi

darcs record --repodir=$work/darcs-repo -a -A Nobody --ignore-time \
    --logfile $work/logfile > log 2>&1
if test $? -ne 0; then cat log; no_result; fi

activity="run tailor again"
python $here/tailor -c $work/tailor.conf > log 2>&1
if test $? -ne 0; then cat log; fail; fi

cat > $work/ok <<EOF
1 10 initial commit
2 11 second commit
3 12 third commit
4 13 fourth commit
EOF
if test $? -ne 0; then no_result; fi

activity="check aegis project history"
aegis -list project_history -unformatted 2> log | cut -d\  -f 1,7- > history
if test $? -ne 0; then cat history; no_result; fi

diff ok history
if test $? -ne 0; then fail; fi

cat > $work/ok <<EOF
brief_description = "fourth commit";
description = "This text is now the description of the aegis change splitted on\n\\
multiple lines.";
cause = external_improvement;
test_exempt = true;
test_baseline_exempt = true;
regression_test_exempt = true;
architecture =
[
	"unspecified",
];
copyright_years =
[
	`date +%Y`,
];
EOF
if test $? -ne 0; then no_result; fi

activity="check project content"
aegis -ca -l 13 > $work/change_attr 2> log
if test $? -ne 0; then cat log; no_result; fi

diff ok change_attr
if test $? -ne 0; then fail; fi

#
# test the change content
#
activity="change 10 content"
cat > $work/ok <<EOF
config create 1 aegis.conf
source create 1 dir/foo.txt
EOF
if test $? -ne 0; then no_result; fi

aegis -list change_files -unf -c 10 > $work/out
if test $? -ne 0; then no_result; fi

diff $work/ok $work/out
if test $? -ne 0; then fail; fi

pass
