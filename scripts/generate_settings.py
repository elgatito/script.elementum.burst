#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
    This script is used to generate Kodi settings file and insert there providers list.
    List is checked through providers.json and inserting only providers with enabled:true,
    while default providers should have predefined:true.
"""

import os
import re
import json

mandatory_fields = {'name': '', 'predefined': False, 'enabled': False, 'private': False, 'id': '', 'languages': ''}
public = []
private = []
settings = ""

languages = {
    'int': 32110,
    'en': 32111,
    'it': 32112,
    'fr': 32113,
    'ru': 32114,
    'ua': 32115,
    'bg': 32116,
    'ro': 32117,
    'hu': 32118,
}

def cleanup_settings(path):
    global settings
    global public
    global private

    print "Cleaning settings at %s" % (path)
    try:
        with open(path) as file:
            settings = file.read()
            file.close()
        settings = re.sub(r"(<!-- Providers-\w+-Begin -->).*?(<!-- Providers-\w+-End -->)", "\\1\n    \\2", settings, flags=re.DOTALL)

    except Exception as e:
        print "Failed removing settings from %s: %s" % (path, repr(e))


def load_providers(path):
    global settings
    global public
    global private

    print "Loading providers from %s" % (path)
    try:
        with open(path) as file:
            providers = json.load(file)

        # Setting default values for each provider
        # to avoid missing dict items
        for provider in providers:
            for k, v in mandatory_fields.iteritems():
                if k not in providers[provider]:
                    providers[provider][k] = v

        for provider in sorted(providers, key=lambda x: providers[x]['name'].lower()):
            if not providers[provider]['enabled']:
                continue

            providers[provider]['id'] = provider
            providers[provider]['name'] = "[B]" + providers[provider]['name'] + "[/B]   [COLOR gray]" + get_languages(providers[provider]['languages']) + "[/COLOR]"

            if providers[provider]['private']:
                private.append(providers[provider])
            else:
                public.append(providers[provider])

    except Exception as e:
        print "Failed importing providers from %s: %s" % (path, repr(e))


def store_providers(path):
    global settings
    global public
    global private

    public_string = ""
    private_string = ""
    public_predefined_string = ""
    private_predefined_string = ""

    public_count = 0
    private_count = 0

    print "Saving providers to %s" % (path)

    for p in public:
        public_count += 1

        item = """
    <setting label="{name}" id="use_{id}" type="bool" default="{default}" />
      <setting id="{id}_alias" label="32077" type="text" default="" subsetting="true" visible="eq(-1,true)" />
      <setting id="{id}_contains" type="enum" label="32080" subsetting="true" lvalues="32081|32082|32083" visible="eq(-2,true)" />
      """.format(id=p['id'], name=p['name'].encode('utf8'), default=str(p['predefined']).lower())

        if not p['predefined']:
            public_string += item
        else:
            public_predefined_string += item

    for p in private:
        private_count += 1

        item = """
    <setting label="{name}" id="use_{id}" type="bool" default="{default}" />
      <setting id="{id}_username" label="32015" type="text" default="" subsetting="true" visible="eq(-1,true)" />
      <setting id="{id}_password" label="32016" type="text" default="" option="hidden" subsetting="true" visible="eq(-2,true)" />
      <setting id="{id}_alias" label="32077" type="text" default="" subsetting="true" visible="eq(-3,true)" />
      <setting id="{id}_contains" type="enum" label="32080" subsetting="true" lvalues="32081|32082|32083" visible="eq(-4,true)" />
      """.format(id=p['id'], name=p['name'].encode('utf8'), default=str(p['predefined']).lower())

        if not p['predefined']:
            private_string += item
        else:
            private_predefined_string += item

    try:
        settings = re.sub(r"(<!-- Providers-Public-Begin -->).*?(<!-- Providers-Public-End -->)", "\\1\n" + public_predefined_string + public_string + "\\2", settings, flags=re.DOTALL)
        settings = re.sub(r"(<!-- Providers-Private-Begin -->).*?(<!-- Providers-Private-End -->)", "\\1\n" + private_predefined_string + private_string + "\\2", settings, flags=re.DOTALL)

        with open(path, 'w') as file:
            file.write(settings)
            file.close()
            print "Saved %d public, %d private providers to %s" % (public_count, private_count, path)

    except Exception as e:
        print "Failed removing settings from %s: %s" % (path, repr(e))

def get_languages(langs):
    if not langs:
        return ""

    res = ""
    for l in langs.replace(" ", "").split(","):
        if l in languages:
            if res:
                res += ", "

            res += "$ADDON[script.elementum.burst " + str(languages[l]) + "]"

    if res:
        res = "[" + res + "]"

    return res


cleanup_settings(os.path.join('resources', 'settings.xml'))
load_providers(os.path.join('burst', 'providers', 'providers.json'))
store_providers(os.path.join('resources', 'settings.xml'))
