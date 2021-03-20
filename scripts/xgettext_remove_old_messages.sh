#!/usr/bin/env bash

set -o nounset
set -o errexit

which rg > /dev/null || (echo "No ripgrep found, exit" && exit 1)

grep -oP 'msgctxt "#\K\d+' resources/language/messages.pot > ids.pot

while read -r line; do rg -q -g '!*.po' -g '!*.pot' $line . || echo $line; done < ids.pot > orphaned_ids.pot

find resources/ -name "*.po*" |
while read -r file
do
    while read -r line
    do
        sed -i "/$line/,+3d" "$file"
    done < orphaned_ids.pot
done

# TODO: https://stackoverflow.com/questions/10435926/how-to-automatcially-remove-unused-gettext-strings/26469640
# after cleaning pot file we can use msgattrib to clean po files
# msgattrib --set-obsolete --ignore-file=messages.pot -o messages.po messages.po
# msgattrib --no-obsolete -o messages.po messages.po

rm -f ids.pot orphaned_ids.pot
