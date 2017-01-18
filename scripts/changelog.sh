#!/bin/sh
git tag -l | sort -u -r | while read TAG ; do
    if [ $NEXT ];then
        echo $NEXT
    fi
    GIT_PAGER=cat git log --no-merges --date-order --date=short --format=" * [%ad] %s" $TAG..$NEXT
    NEXT=$TAG
    echo
done
FIRST=$(git tag -l | head -1)
echo $FIRST
GIT_PAGER=cat git log --no-merges --date-order --date=short --format=" * [%ad] %s" $FIRST
echo
