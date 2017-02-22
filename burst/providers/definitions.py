# -*- coding: utf-8 -*-
"""
Overrides for provider definitions
"""
import os
import sys
import json
import xbmc
import xbmcaddon
import collections
from glob import glob
from urlparse import urlparse
from quasar.provider import log

ADDON = xbmcaddon.Addon()
definitions = {}


def load_providers(path, fix_seasons=False):
    try:
        with open(path) as file:
            providers = json.load(file)
        for provider in providers:
            update_definition(provider, providers[provider], fix_seasons)
    except Exception as e:
        import traceback
        log.error("Failed importing providers from %s: %s", path, repr(e))
        map(log.error, traceback.format_exc().split("\n"))


def load_overrides(path, custom=False):
    try:
        if custom:
            sys.path.append(path)
            from overrides import overrides
        else:
            from burst_overrides import overrides
        if custom:
            log.debug("Imported overrides: %s", repr(overrides))
        for provider in overrides:
            update_definition(provider, overrides[provider])
        if custom:
            log.info("Successfully loaded overrides from %s", os.path.join(path, "overrides.py"))
    except Exception as e:
        import traceback
        log.error("Failed importing %soverrides: %s", "custom " if custom else "", repr(e))
        map(log.error, traceback.format_exc().split("\n"))


def update_definition(provider, definition, fix_seasons=False):
    if 'base_url' in definition:
        parsed_url = urlparse(definition['base_url'])
        root_url = '%s://%s' % (parsed_url.scheme, parsed_url.netloc)
        definition['root_url'] = root_url

    if fix_seasons:
        if 'season_keywords' in definition and definition['season_keywords']:
            definition['season_keywords'] = definition['season_keywords'].replace('Season_{season}', 'season {season:2}')
        if 'season_keywords2' in definition and definition['season_keywords2']:
            definition['season_keywords2'] = definition['season_keywords2'].replace('Season{season}', 's{season:2}')

    if provider in definitions:
        update(definitions[provider], definition)
    else:
        definitions[provider] = definition


def update(d, u):
    for k, v in u.iteritems():
        if isinstance(v, collections.Mapping):
            r = update(d.get(k, {}), v)
            d[k] = r
        else:
            d[k] = u[k]
    return d


# T411
def t411season(season):
    real_s = season + 967
    if season == 25:
        real_s = 994
    if 25 < season < 28:
        real_s = season + 966
    return real_s


def t411episode(episode):
    real_ep = 936
    if 8 < episode < 31:
        real_ep = episode + 937
    if 30 < episode < 61:
        real_ep = episode + 1057
    return real_ep


is_mock = "%s" % type(xbmcaddon) == "<class 'sphinx.ext.autodoc._MockModule'>"

# Load generated providers
if not is_mock:
    load_providers(os.path.join(ADDON.getAddonInfo("path"), 'burst', 'providers', 'definitions.json'), True)
else:
    load_providers(os.path.join('..', 'burst', 'providers', 'definitions.json'))

# Load built-in providers
if not is_mock:
    load_providers(os.path.join(ADDON.getAddonInfo("path"), 'burst', 'providers', 'providers.json'))
else:
    load_providers(os.path.join('..', 'burst', 'providers', 'providers.json'))

# Load providers overrides
if not is_mock:
    load_overrides(os.path.join(ADDON.getAddonInfo("path"), 'burst', 'providers'))
else:
    load_overrides(os.path.join('..', 'burst', 'providers'))

# Load user's custom providers
if not is_mock:
    custom_providers = os.path.join(xbmc.translatePath(ADDON.getAddonInfo("profile")), "providers")
else:
    custom_providers = '.'
if not os.path.exists(custom_providers):
    try:
        os.makedirs(custom_providers)
    except Exception as e:
        log.error("Unable to create custom providers folder: %s", repr(e))
        pass
for provider_file in glob(os.path.join(custom_providers, "*.json")):
    log.info("Importing and enabling %s" % provider_file)
    load_providers(provider_file)

# Load user's custom overrides
if not is_mock:
    custom_overrides = xbmc.translatePath(ADDON.getAddonInfo("profile"))
    if os.path.exists(custom_overrides):
        load_overrides(custom_overrides, True)
else:
    load_overrides('.')

longest = len(definitions[sorted(definitions, key=lambda p: len(definitions[p]['name']), reverse=True)[0]]['name'])
