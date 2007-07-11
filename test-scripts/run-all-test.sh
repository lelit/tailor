
# Set it to use shared basedir in tests:
# SHAREDDIR=yes

# create dirs for logging
rm -rf log-FAIL log-OK summary-OK summary-FAIL
mkdir log-FAIL
mkdir log-OK

for name in \
    test-darcs2darcs*.sh \
    test-mtn2mtn*.sh \
    test-svn2svn*.sh \
    test-mtn2svn*.sh
do
    echo -n "Testing $name ..."
    result="FAIL"
    info=""
    if ./$name >testing.log 2>testing.err
    then
        if grep -q "Upstream change application failed" < testing.log
        then
            info=" (log detection)"
        else
            result="OK"
        fi
    else
        info=" (errorlevel $?)"
    fi

    echo -e "$info\t$result"
    echo "$name$info" >> summary-$result

    mv testing.log log-$result/$name.log
    mv testing.err log-$result/$name.err
done
