# -*- coding: utf-8 -*-
"""
Definitions and overrides loader
"""

import os
import sys
import json
import time
import xbmc
import xbmcaddon
import collections
from glob import glob
from urlparse import urlparse
from elementum.provider import log

start_time = time.time()
ADDON = xbmcaddon.Addon()
ADDON_PATH = ADDON.getAddonInfo("path").decode('utf-8')
ADDON_PROFILE = ADDON.getAddonInfo("profile").decode('utf-8')
if not ADDON_PATH:
    ADDON_PATH = ".."

definitions = {}
mandatory_fields = {
    'name': '',
    'predefined': False,
    'enabled': False,
    'private': False,
    'id': '',
    'languages': '',
    'charset': 'utf8',
    'response_charset': None
}


def load_providers(path, custom=False):
    """ Definitions loader for json files

    Args:
        path         (str): Path to json file to be loaded
        custom      (bool): Boolean flag to specify if this is a custom provider
    """
    if not os.path.exists(path):
        return

    try:
        with open(path) as file:
            providers = json.load(file)
        for provider in providers:
            update_definitions(provider, providers[provider], custom)
    except Exception as e:
        import traceback
        log.error("Failed importing providers from %s: %s", path, repr(e))
        map(log.error, traceback.format_exc().split("\n"))


def load_overrides(path, custom=False):
    """ Overrides loader for Python files

    Note:
        Overrides must be in an ``overrides`` dictionary.

    Args:
        path    (str): Path to Python file to be loaded
        custom (bool): Boolean flag to specify if this is a custom overrides file
    """
    try:
        if custom:
            sys.path.append(path)
            from overrides import overrides
            log.debug("Imported overrides: %s", repr(overrides))
            for provider in overrides:
                update_definitions(provider, overrides[provider])
            log.info("Successfully loaded overrides from %s", os.path.join(path, "overrides.py"))
    except Exception as e:
        import traceback
        log.error("Failed importing %soverrides: %s", "custom " if custom else "", repr(e))
        map(log.error, traceback.format_exc().split("\n"))


def update_definitions(provider, definition, custom=False):
    """ Updates global definitions with a single provider's definitions

    Args:
        provider     (str): Provider ID
        definition  (dict): Loaded provider's definitions to be merged with the global definitions
        custom      (bool): Boolean flag to specify if this is a custom provider
    """
    if 'base_url' in definition:
        parsed_url = urlparse(definition['base_url'])
        root_url = '%s://%s' % (parsed_url.scheme, parsed_url.netloc)
        definition['root_url'] = root_url

    if custom:
        definition['custom'] = True
        definition['enabled'] = True

    if provider in definitions:
        update(definitions[provider], definition)
    else:
        definitions[provider] = definition


def update(d, u):
    """ Utility method to recursively merge dictionary values of definitions

    Args:
        d (dict): Current provider definitions
        u (dict): Dictionary of definitions to be updated
    """
    for k, v in u.iteritems():
        if isinstance(v, collections.Mapping):
            r = update(d.get(k, {}), v)
            d[k] = r
        else:
            d[k] = u[k]
    return d


# Load providers
load_providers(os.path.join(ADDON_PATH, 'burst', 'providers', 'providers.json'))

# Load providers overrides
load_overrides(os.path.join(ADDON_PATH, 'burst', 'providers'))

# Load user's custom providers
custom_providers = os.path.join(xbmc.translatePath(ADDON_PROFILE), "providers")
if not os.path.exists(custom_providers):
    try:
        os.makedirs(custom_providers)
    except Exception as e:
        log.error("Unable to create custom providers folder: %s", repr(e))
        pass
for provider_file in glob(os.path.join(custom_providers, "*.json")):
    log.info("Importing and enabling %s" % provider_file)
    load_providers(provider_file, custom=True)

# Load user's custom overrides
custom_overrides = xbmc.translatePath(ADDON_PROFILE)
if os.path.exists(os.path.join(custom_overrides, 'overrides.py')):
    load_overrides(custom_overrides, custom=True)

# Load json overrides
load_providers(os.path.join(xbmc.translatePath(ADDON_PROFILE), 'overrides.json'))

# Setting mandatory fields to their default values for each provider.
for provider in definitions:
    for k, v in mandatory_fields.iteritems():
        if k not in definitions[provider]:
            definitions[provider][k] = v

# Finding the largest provider name for further use in loggers.
longest = 10
if len(definitions) > 0:
    longest = len(definitions[sorted(definitions, key=lambda p: len(definitions[p]['name']), reverse=True)[0]]['name'])

log.info("Loading definitions took %fs", time.time() - start_time)
