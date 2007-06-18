
# create dirs for logging
rm -rf log-FAIL log-OK summary-OK summary-FAIL
mkdir log-FAIL
mkdir log-OK

ls \
    test-mtn2mtn-*.sh \
    test-svn2svn-*.sh \
    test-mtn2svn-*.sh \
| while read name
do
    echo -n "Testing $name ..."
    result="FAIL"
    if ./$name >testing.log 2>testing.err
    then
        if grep -q "Upstream change application failed" < testing.log
        then
            echo -n " (log detection)"
        else
            result="OK"
        fi
    else
        echo -n " (errorlevel $?)"
    fi

    echo -e "\t$result"
    echo "$name" >> summary-$result

    mv testing.log log-$result/$name.log
    mv testing.err log-$result/$name.err
done
