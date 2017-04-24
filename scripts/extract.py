#!/usr/bin/env python

import os
import re
import sys
import json
import shutil
import requests
from time import sleep
from zipfile import ZipFile
from StringIO import StringIO
from threading import Thread
from parse_magnetic import parse

repo = 'https://offshoregit.com/pulsarunofficial/magnetic_repo'
r = requests.get(repo)
providers = re.findall(r".*href=\"script\.magnetic\.(.*)\/\"\stitle.*", r.text)

args = []
if len(sys.argv) > 1:
    args = sys.argv[1:]

# TODO use argparse, c'mon...
if '--help' in args:
    print '--exclude-icons   Exclude icons'
    print '--exclude-defs    Exclude definitions'
    print '--print           Just print definitions without saving them'
    print '--providers       Extract only those providers'
    sys.exit(0)

if '--providers' in args:
    offset = 1
    if '--exclude-icons' in args:
        offset += 1
    if '--exclude-defs' in args:
        offset += 1
    if '--print' in args:
        offset += 1
    providers = args[offset:]

getting = "icons and definitions"
if '--exclude-icons' in args:
    getting = "definitions"
if '--exclude-defs' in args:
    getting = "icons"
if '--exclude-icons' in args and '--exclude-defs' in args:
    getting = "nothing"
print "Getting %s for: %s" % (getting, repr(providers))
if getting == 'nothing':
    raise Exception("Nothing to extract...")

definitions = {}
threads = []


def extract_magnetic(provider):
    global definitions

    new_provider = provider.replace('-mc', '')
    addon_xml_path = "%s/script.magnetic.%s/addon.xml" % (repo, provider)
    addon_xml = requests.get(addon_xml_path).text
    last_version = re.findall(r".*version=\"(.*)\"[\s\r\n].*", addon_xml)[1]

    last_zip = "%s/script.magnetic.%s/script.magnetic.%s-%s.zip" % (repo, provider, provider, last_version)
    print "Getting: %s..." % last_zip

    r = requests.get(last_zip, stream=True)
    if r.ok:
        print "Got %s" % last_zip
        with ZipFile(StringIO(r.content)) as zf:
            if '--exclude-icons' not in args:
                with zf.open(os.path.join('script.magnetic.%s' % provider, 'icon.png')) as icon:
                    target = file(os.path.join('burst', 'providers', 'icons', '%s.png' % new_provider), 'wb')
                    with icon, target:
                        shutil.copyfileobj(icon, target)
                print "Extracted %s icon" % new_provider
            if '--exclude-defs' not in args:
                main = zf.read(os.path.join('script.magnetic.%s' % provider, 'main.py'))
                settings = zf.read(os.path.join('script.magnetic.%s' % provider, 'resources', 'settings.xml'))
                definitions[new_provider] = parse(main=main,
                                                  addon=addon_xml,
                                                  settings=settings,
                                                  provider=new_provider)[new_provider]
    else:
        r.raise_for_status()


for provider in providers:
    t = Thread(target=extract_magnetic, args=[provider])
    threads.append(t)

for t in threads:
    t.start()
    sleep(1)

for t in threads:
    t.join()

if '--exclude-defs' not in args and '--print' not in args:
    save_path = os.path.join('burst', 'providers', 'definitions.json')
    with open(save_path, 'w') as defs:
        defs.write(json.dumps(definitions, indent=4, sort_keys=True, separators=(',', ': ')) + "\n")
    print "Extracted %d providers and wrote definitions to %s" % (len(definitions), save_path)
elif '--print' in args:
    print json.dumps(definitions, indent=4, sort_keys=True, separators=(',', ': '))
    print
    print "Sample settings:"
    for provider in definitions:
        print '<setting label="%s" id="use_%s" type="bool" default="false" />' % (definitions[provider]['name'], provider)
