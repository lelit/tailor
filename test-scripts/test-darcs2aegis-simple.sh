#!/bin/sh
#
# Copyright (C) 2008 Walter Franzini
#
# NOTE: TABS in aegis metadata samples below must be preserved.
#

#
# This test expects to be run from the tailor top source dir, change
# the following line if the convention used by tailor developer(s)
# differs.
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


#
# This test follows Aegis convention, where a test must be able to
# work even when the development directory is not writable, this
# happens when running tests in the integration stage.
#
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

cat > $work/darcs-repo/bar.txt <<EOF
This will be baz.txt
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
verbose = true
Debug = true

[project]
patch-name-format = %(revision)s
root-directory = $PWD/rootdir
source = darcs:source
target = aegis:target

[darcs:source]
repository = $work/darcs-repo
subdir = darcs1side
darcs-command = /usr/bin/darcs

[aegis:target]
module = $AEGIS_PROJECT
subdir = aegisside
EOF
if test $? -ne 0; then no_result; fi

activity="run tailor"
python $here/tailor -c $work/tailor.conf > $work/tailor.log 2>&1
if test $? -ne 0; then cat $work/tailor.log; fail; fi

cat > $work/massage_history.awk <<'EOF'
/^Name:/ {print $0}
/^[0-9]/ {print $1, $7, $8, $9}
EOF
if test $? -ne 0; then no_result; fi

activity="check aegis project history"
cat > $work/ok <<EOF
1 10 initial commit
2 11 second commit
3 12 third commit
EOF
if test $? -ne 0; then no_result; fi

aegis -list project_history -unformatted 2> $work/log > $work/history
if test $? -ne 0; then cat $work/log; no_result; fi

awk -f $work/massage_history.awk < history > history.new
if test $? -ne 0; then no_result; fi

diff -u $work/ok $work/history.new
if test $? -ne 0; then fail; fi

activity="check the aegis baseline vs. darcs repository"
diff $work/darcs-repo/baz.txt $workproj/baseline/baz.txt
if test $? -ne 0; then fail; fi

diff $work/darcs-repo/dir/foo.txt $workproj/baseline/dir/foo.txt
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

activity="tag 1.0.0"
darcs tag 1.0.0 --repodir=$work/darcs-repo -A Nobody > log 2>&1
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

#
# Check the aegis project history.
# fixme:  there is a gap in the change number sequence (13 is missing)
#         because currently the change corresponding to the tags is
#         still created even if it cannot be completed because it's empty
#
activity="check aegis project history (again)"

cat > $work/ok <<EOF
1 10 initial commit
2 11 second commit
Name: "1.0.0"
3 12 third commit
4 14 fourth commit
EOF
if test $? -ne 0; then no_result; fi

aegis -list project_history -unformatted 2> log > history
if test $? -ne 0; then cat history; no_result; fi

awk -f $work/massage_history.awk < history > history.new
if test $? -ne 0; then no_result; fi

diff -u ok history.new
if test $? -ne 0; then fail; fi

activity="check change 14 attributes"
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

aegis -ca -l 14 > $work/change_attr 2> log
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

diff -u $work/ok $work/out
if test $? -ne 0; then fail; fi

#
# Check the content of change 11 (second commit)
#
activity="check change 11 content"
cat > $work/ok <<EOF
source create 1 bar.txt
source modify 1 -> 2 dir/foo.txt
EOF
if test $? -ne 0; then no_result; fi

aegis -list change_files -unf -c 11 > $work/out
if test $? -ne 0; then no_result; fi

diff -u $work/ok $work/out
if test $? -ne 0; then fail; fi

#
# Check the content of change 12 (third commit)
#
# Note: we check the change fstate file to verify the rename
#       operation, since the unformatted output lacks some details..
#
activity="check change 12 content"
cat > $work/ok <<EOF
src =
[
	{
		file_name = "bar.txt";
		uuid = "UUID";
		action = remove;
		edit_origin =
		{
			revision = "1";
			encoding = none;
		};
		usage = source;
		move = "baz.txt";
	},
	{
		file_name = "baz.txt";
		uuid = "UUID";
		action = create;
		edit =
		{
			revision = "2";
			encoding = none;
		};
		edit_origin =
		{
			revision = "1";
			encoding = none;
		};
		usage = source;
		move = "bar.txt";
	},
	{
		file_name = "dir/foo.txt";
		uuid = "UUID";
		action = modify;
		edit =
		{
			revision = "3";
			encoding = none;
		};
		edit_origin =
		{
			revision = "2";
			encoding = none;
		};
		usage = source;
	},
];
EOF
if test $? -ne 0; then no_result; fi

check_it ok $workproj/info/change/0/012.fs

#
# Note: there is a gap in the change numbers sequence, the next should
#       be 13, because the aegis target back-end needs to be improved
#       in the case of changeset setting only a tag
#
activity="check change 14 content"
cat > $work/ok <<EOF
source modify 2 -> 3 baz.txt
source remove 3 dir/foo.txt
EOF
if test $? -ne 0; then no_result; fi

aegis -list change_files -unf -c 14 > $work/out
if test $? -ne 0; then no_result; fi

diff -u $work/ok $work/out
if test $? -ne 0; then fail; fi

#
# Check the content of the baseline
#
activity="check the baseline"
cat > $work/ok <<EOF
src =
[
	{
		file_name = "aegis.conf";
		uuid = "UUID";
		action = create;
		edit =
		{
			revision = "1";
			encoding = none;
		};
		edit_origin =
		{
			revision = "1";
			encoding = none;
		};
		usage = config;
		file_fp =
		{
			youngest = TIME;
			oldest = TIME;
			crypto = "GUNK";
		};
		diff_file_fp =
		{
			youngest = TIME;
			oldest = TIME;
			crypto = "GUNK";
		};
	},
	{
		file_name = "bar.txt";
		uuid = "UUID";
		action = remove;
		edit =
		{
			revision = "1";
			encoding = none;
		};
		edit_origin =
		{
			revision = "1";
			encoding = none;
		};
		usage = source;
		move = "baz.txt";
		deleted_by = 12;
	},
	{
		file_name = "baz.txt";
		uuid = "UUID";
		action = create;
		edit =
		{
			revision = "3";
			encoding = none;
		};
		edit_origin =
		{
			revision = "3";
			encoding = none;
		};
		usage = source;
		file_fp =
		{
			youngest = TIME;
			oldest = TIME;
			crypto = "GUNK";
		};
		diff_file_fp =
		{
			youngest = TIME;
			oldest = TIME;
			crypto = "GUNK";
		};
		move = "bar.txt";
	},
	{
		file_name = "dir/foo.txt";
		uuid = "UUID";
		action = remove;
		edit =
		{
			revision = "3";
			encoding = none;
		};
		edit_origin =
		{
			revision = "3";
			encoding = none;
		};
		usage = source;
		diff_file_fp =
		{
			youngest = TIME;
			oldest = TIME;
			crypto = "GUNK";
		};
		deleted_by = 14;
	},
];
EOF
if test $? -ne 0; then no_result; fi

check_it ok $workproj/info/trunk.fs

activity="check aegis.conf baseline copy"
cat > $work/ok <<'EOF'

build_command = "exit 0";
link_integration_directory = true;

history_get_command = "aesvt -check-out -edit ${quote $edit} "
    "-history ${quote $history} -f ${quote $output}";
history_put_command = "aesvt -check-in -history ${quote $history} "
    "-f ${quote $input}";
history_query_command = "aesvt -query -history ${quote $history}";
history_content_limitation = binary_capable;

diff_command = "set +e; $diff $orig $i > $out; test $$? -le 1";
merge_command =
"(diff3 -e $i $orig $mr | sed -e '/^w$$/d' -e '/^q$$/d'; echo '1,$$p') "
"| ed - $i > $out";
patch_diff_command =
"set +e; $diff -C0 -L $index -L $index $orig $i > $out; test $$? -le 1";

shell_safe_filenames = false;
EOF
if test $? -ne 0; then no_result; fi

diff ok $workproj/baseline/aegis.conf
if test $? -ne 0; then fail; fi

diff $work/darcs-repo/baz.txt $workproj/baseline/baz.txt
if test $? -ne 0; then fail; fi

pass
