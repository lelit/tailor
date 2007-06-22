#!/bin/sh

# File: test-mtn2mtn-attrib-execute.sh
# needs: test-mtn2mtn.include
# 
# Test for converting a file with executable attribute from Monotone to Monotone self.
# It's a selfchecking for Monotone.  Diff between test1.log and test2.log
# should no have difference.
#
# No errors found.

. ./test-mtn2mtn.include
monotone_setup

echo "echo \"a simple executable script\"" > script.sh
chmod +x script.sh
echo "a simple file, not a script" > noscript.sh
echo -e "#!/bin/sh\necho \"Script, but no executeable\"" > noexecute.sh
mtn_exec add *.sh
mtn_exec commit --message "inital commit"

testing_runs
