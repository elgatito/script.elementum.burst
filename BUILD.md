Building script.elementum.burst for release:

```
#!/bin/bash

set -e

TAG=$(git describe --tags)

export GH_TOKEN=aaaaaaaaaaaaaaaaaaaaaaaaaaa # This is an access token from Github
export PATH=$HOME/go/bin:/usr/lib/go-1.9/bin/:$PATH
export GOPATH=$HOME/go

git checkout master

rm -f *.zip

sudo -S true

pip2 install -r requirements.txt

python2.7 -m flake8
./scripts/xgettext.sh
make

if [[ $TAG != *-* ]]
then
	make zip
    make upload
fi

```
