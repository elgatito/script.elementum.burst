# -*- coding: utf-8 -*-

"""
Provider thread methods
"""

import os
import re
import json
import xbmc
import xbmcaddon
from client import Client
from quasar.provider import log, get_setting, set_setting
from providers.definitions import definitions, longest
from utils import ADDON_PATH, get_int, clean_size


def generate_payload(provider, generator, filtering, verify_name=True, verify_size=True):
    """ Payload formatter to format results the way Quasar expects them

    Args:
        provider        (str): Provider ID
        generator  (function): Generator method, can be either ``extract_torrents`` or ``extract_from_api``
        filtering (Filtering): Filtering class instance
        verify_name    (bool): Whether to double-check the results' names match the query or not
        verify_size    (bool): Whether to check the results' file sizes

    Returns:
        list: Formatted results
    """
    filtering.information(provider)
    results = []

    definition = definitions[provider]

    for name, info_hash, uri, size, seeds, peers in generator:
        size = clean_size(size)
        # uri, info_hash = clean_magnet(uri, info_hash)
        v_name = name if verify_name else filtering.title
        v_size = size if verify_size else None
        if filtering.verify(provider, v_name, v_size):
            results.append({"name": name,
                            "uri": uri,
                            "info_hash": info_hash,
                            "size": size,
                            "seeds": get_int(seeds),
                            "peers": get_int(peers),
                            "language": definition["language"] if 'language' in definition else 'en',
                            "provider": '[COLOR %s]%s[/COLOR]' % (definition['color'], definition['name']),
                            "icon": os.path.join(ADDON_PATH, 'burst', 'providers', 'icons', '%s.png' % provider),
                            })
        else:
            log.debug(filtering.reason.encode('utf-8'))

    log.debug('>>>>>> %s would send %d torrents to Quasar <<<<<<<' % (provider, len(results)))

    return results


def process(provider, generator, filtering, verify_name=True, verify_size=True):
    """ Method for processing provider results using its generator and Filtering class instance

    Args:
        provider        (str): Provider ID
        generator  (function): Generator method, can be either ``extract_torrents`` or ``extract_from_api``
        filtering (Filtering): Filtering class instance
        verify_name    (bool): Whether to double-check the results' names match the query or not
        verify_size    (bool): Whether to check the results' file sizes
    """
    log.debug("execute_process for %s with %s" % (provider, repr(generator)))
    definition = definitions[provider]

    client = Client()
    token = None
    logged_in = False
    token_auth = False

    if get_setting("use_cloudhole", bool):
        client.clearance = get_setting('clearance')
        client.user_agent = get_setting('user_agent')

    if get_setting('kodi_language', bool):
        kodi_language = xbmc.getLanguage(xbmc.ISO_639_1)
        if kodi_language:
            filtering.kodi_language = kodi_language
        language_exceptions = get_setting('language_exceptions')
        if language_exceptions.strip().lower():
            filtering.language_exceptions = re.split(r',\s?', language_exceptions)

    log.debug("[%s] Queries: %s" % (provider, filtering.queries))
    log.debug("[%s] Extras:  %s" % (provider, filtering.extras))

    for query, extra in zip(filtering.queries, filtering.extras):
        log.debug("[%s] Before keywords - Query: %s - Extra: %s" % (provider, repr(query), repr(extra)))
        query = filtering.process_keywords(provider, query)
        extra = filtering.process_keywords(provider, extra)
        log.debug("[%s] After keywords  - Query: %s - Extra: %s" % (provider, repr(query), repr(extra)))
        if not query:
            return filtering.results

        url_search = filtering.url.replace('QUERY', query)
        if extra:
            url_search = url_search.replace('EXTRA', extra)
        else:
            url_search = url_search.replace('EXTRA', '')
        url_search = url_search.replace(' ', definition['separator'])

        # MagnetDL fix...
        url_search = url_search.replace('FIRSTLETTER', query[:1])

        # Creating the payload for POST method
        payload = dict()
        for key, value in filtering.post_data.iteritems():
            if 'QUERY' in value:
                payload[key] = filtering.post_data[key].replace('QUERY', query)
            else:
                payload[key] = filtering.post_data[key]

        # Creating the payload for GET method
        data = None
        if filtering.get_data:
            data = dict()
            for key, value in filtering.get_data.iteritems():
                if 'QUERY' in value:
                    data[key] = filtering.get_data[key].replace('QUERY', query)
                else:
                    data[key] = filtering.get_data[key]

        log.debug("-   %s query: %s" % (provider, repr(query)))
        log.debug("--  %s url_search before token: %s" % (provider, repr(url_search)))
        log.debug("--- %s using POST payload: %s" % (provider, repr(payload)))
        log.debug("----%s filtering with post_data: %s" % (provider, repr(filtering.post_data)))

        # Set search's "title" in filtering to double-check results' names
        if 'filter_title' in definition and definition['filter_title']:
            filtering.filter_title = True
            filtering.title = query

        if token:
            log.info('[%s] Reusing existing token' % provider)
            url_search = url_search.replace('TOKEN', token)
        elif 'token' in definition:
            token_url = definition['base_url'] + definition['token']
            log.debug("Getting token for %s at %s" % (provider, repr(token_url)))
            client.open(token_url.encode('utf-8'))
            try:
                token_data = json.loads(client.content)
            except:
                log.error('%s: Failed to get token for %s' % (provider, repr(url_search)))
                return filtering.results
            log.debug("Token response for %s: %s" % (provider, repr(token_data)))
            if 'token' in token_data:
                token = token_data['token']
                log.debug("Got token for %s: %s" % (provider, repr(token)))
                url_search = url_search.replace('TOKEN', token)
            else:
                log.warning('%s: Unable to get token for %s' % (provider, repr(url_search)))

        if logged_in:
            log.info("[%s] Reusing previous login" % provider)
        elif token_auth:
            log.info("[%s] Reusing previous token authorization" % provider)
        elif 'private' in definition and definition['private']:
            username = get_setting('%s_username' % provider)
            password = get_setting('%s_password' % provider)
            passkey = get_setting('%s_passkey' % provider)
            if not username and not password and not passkey:
                for addon_name in ('script.magnetic.%s' % provider, 'script.magnetic.%s-mc' % provider):
                    for setting in ('username', 'password'):
                        try:
                            value = xbmcaddon.Addon(addon_name).getSetting(setting)
                            set_setting('%s_%s' % (provider, setting), value)
                            if setting == 'username':
                                username = value
                            if setting == 'password':
                                password = value
                        except:
                            pass

            if passkey:
                logged_in = True
                client.passkey = passkey
                url_search = url_search.replace('PASSKEY', passkey)

            elif 'login_object' in definition and definition['login_object']:
                logged_in = False
                login_object = definition['login_object'].replace('USERNAME', '"%s"' % username).replace('PASSWORD', '"%s"' % password)

                # TODO generic flags in definitions for those...
                if provider == 'alphareign':
                    client.open(definition['root_url'] + definition['login_path'])
                    if client.content:
                        csrf_name = re.search(r'name="csrf_name" value="(.*?)"', client.content)
                        csrf_value = re.search(r'name="csrf_value" value="(.*?)"', client.content)
                        if csrf_name and csrf_value:
                            login_object = login_object.replace("CSRF_NAME", '"%s"' % csrf_name.group(1))
                            login_object = login_object.replace("CSRF_VALUE", '"%s"' % csrf_value.group(1))
                        else:
                            logged_in = True
                if provider == 'hd-torrents':
                    client.open(definition['root_url'] + definition['login_path'])
                    if client.content:
                        csrf_token = re.search(r'name="csrfToken" value="(.*?)"', client.content)
                        if csrf_token:
                            login_object = login_object.replace('CSRF_TOKEN', '"%s"' % csrf_token.group(1))
                        else:
                            logged_in = True

                if 'token_auth' in definition:
                    # log.debug("[%s] logging in with: %s" % (provider, login_object))
                    if client.open(definition['root_url'] + definition['token_auth'], post_data=eval(login_object)):
                        try:
                            token_data = json.loads(client.content)
                        except:
                            log.error('%s: Failed to get token from %s' % (provider, definition['token_auth']))
                            return filtering.results
                        log.debug("Token response for %s: %s" % (provider, repr(token_data)))
                        if 'token' in token_data:
                            client.token = token_data['token']
                            log.debug("Auth token for %s: %s" % (provider, repr(client.token)))
                        else:
                            log.error('%s: Unable to get auth token for %s' % (provider, repr(url_search)))
                            return filtering.results
                        log.info('[%s] Token auth successful' % provider)
                        token_auth = True
                    else:
                        log.error("[%s] Token auth failed with response: %s" % (provider, repr(client.content)))
                        return filtering.results
                elif not logged_in and client.login(definition['root_url'] + definition['login_path'],
                                                    eval(login_object), definition['login_failed']):
                    log.info('[%s] Login successful' % provider)
                    logged_in = True
                elif not logged_in:
                    log.error("[%s] Login failed: %s", provider, client.status)
                    log.debug("[%s] Failed login content: %s", provider, repr(client.content))
                    return filtering.results

                if logged_in:
                    if provider == 'hd-torrents':
                        client.open(definition['root_url'] + '/torrents.php')
                        csrf_token = re.search(r'name="csrfToken" value="(.*?)"', client.content)
                        url_search = url_search.replace("CSRF_TOKEN", csrf_token.group(1))

        log.info(">  %s search URL: %s" % (definition['name'].rjust(longest), url_search))

        client.open(url_search.encode('utf-8'), post_data=payload, get_data=data)
        filtering.results.extend(
            generate_payload(provider,
                             generator(provider, client),
                             filtering,
                             verify_name,
                             verify_size))
    return filtering.results
