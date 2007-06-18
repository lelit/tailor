#!/bin/bash -v

# File: test-mtn2svn-attrib-execute.sh
# needs: test-mtn2svn.include
# 
# Test for converting a file with executable attribute from Monotone to Monotone self.
# It's a selfchecking for Monotone.  Diff between test1.log and test2.log
# should no have difference.
#
# No errors after patch monotone-complete-20070604.patch

. ./test-mtn2svn.include
monotone_setup

# Create one executable file and 1 revision

echo "echo \"a simple executable script\"" > script.sh
chmod +x script.sh
echo "a simple file, not a script" > noscript.sh
echo -e "#!/bin/sh\necho \"Script, but no executeable\"" > noexecute.sh
mtn_exec add *.sh
mtn_exec commit --message "inital commit"

testing_runs
