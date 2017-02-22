# -*- coding: utf-8 -*-
"""
Overrides for provider definitions
"""
import os
import collections
import json
import xbmc
import xbmcaddon
from glob import glob
from urlparse import urlparse
from quasar.provider import log
from shared import definitions
ADDON = xbmcaddon.Addon()


def update(d, u):
    for k, v in u.iteritems():
        if isinstance(v, collections.Mapping):
            r = update(d.get(k, {}), v)
            d[k] = r
        else:
            d[k] = u[k]
    return d


def load_providers_json(json_path):
    try:
        with open(json_path) as file:
            custom_providers = json.load(file)

        for provider in custom_providers:
            update_definition(provider, custom_providers[provider])
    except Exception as e:
        import traceback
        log.error("Failed importing custom provider from %s: %s", json_path, repr(e))
        map(log.error, traceback.format_exc().split("\n"))


def load_providers_py(py_path):
    if os.path.exists(py_path):
        try:
            import sys
            sys.path.append(os.path.dirname(py_path))
            from overrides import overrides
            for provider in overrides:
                update_definition(provider, overrides[provider])
        except Exception as e:
            import traceback
            log.error("Failed importing custom overrides: %s", repr(e))
            map(log.error, traceback.format_exc().split("\n"))


def update_definition(provider, container):
    if 'base_url' in container:
        parsed_url = urlparse(container['base_url'])
        root_url = '%s://%s' % (parsed_url.scheme, parsed_url.netloc)
        container['root_url'] = root_url

    if 'season_keywords' in container and container['season_keywords']:
        container['season_keywords'] = container['season_keywords'].replace('Season_{season}', 'season {season:2}')
    if 'season_keywords2' in container and container['season_keywords2']:
        container['season_keywords2'] = container['season_keywords2'].replace('Season{season}', 's{season:2}')

    if provider in definitions:
        update(definitions[provider], container)
    else:
        definitions[provider] = container


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
    load_providers_json(os.path.join(ADDON.getAddonInfo("path"), 'burst', 'providers', 'definitions.json'))
else:
    load_providers_json(os.path.join('..', 'burst', 'providers', 'definitions.json'))

# Load built-in providers
if not is_mock:
    load_providers_json(os.path.join(ADDON.getAddonInfo("path"), 'burst', 'providers', 'providers.json'))
else:
    load_providers_json(os.path.join('..', 'burst', 'providers', 'providers.json'))

# Load overrides providers
if not is_mock:
    load_providers_py(os.path.join(ADDON.getAddonInfo("path"), 'burst', 'providers', 'overrides.py'))
else:
    load_providers_py(os.path.join('..', 'burst', 'providers', 'overrides.py'))

# Load user custom providers
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
    load_providers_json(provider_file)

# Load custom overrides
if not is_mock:
    load_providers_py(os.path.join(xbmc.translatePath(ADDON.getAddonInfo("profile")), "overrides.py"))
else:
    load_providers_py('.')

longest = len(definitions[sorted(definitions, key=lambda p: len(definitions[p]['name']), reverse=True)[0]]['name'])
