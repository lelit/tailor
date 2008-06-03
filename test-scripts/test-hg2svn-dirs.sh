#! /bin/bash

# Exit immediately if a command exits with a non-zero
set -e

# 1 create a project file
# 2 create a sample HG repo
# 3 attempt to import into svn using tailor

# start with a clean directory
rm -rf testcase
mkdir testcase
cd testcase

# create a project file
cat <<EOF > project.tailor
[DEFAULT]
verbose = True

[project]
target = svn:target
start-revision = INITIAL
root-directory = $PWD/working
state-file = tailor.state
source = hg:test
subdir = .

[hg:test]
repository = $PWD/hg

[svn:target]
module = /
repository = file://$PWD/svn
EOF

# create a simple hg repo with 3 changesets, the second one
# creating a file in a new directory, the third moving the
# file in another dir
mkdir hg
cd hg
hg init
echo string1 > file1
hg add file1
hg ci -m"commit 1"
mkdir a_dir
echo string2 > a_dir/file2
hg add a_dir/file2
hg ci -m"commit 2"
mkdir b_dir
hg rename a_dir/file2 b_dir
hg ci -m"commit 3"
cd ..

# attempt to port to svn
# THIS WILL FAIL
../tailor --configfile project.tailor

# see how far we actually got
svn co file:///$PWD/svn svn-co

diff -Naur -x .hg -x .svn hg svn-co