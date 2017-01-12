# -*- coding: utf-8 -*-

import os
import re
import json
import xbmcaddon
from browser import Browser
from quasar.provider import log, get_setting, set_setting
from providers.definitions import definitions
from utils import ADDON_PATH, get_int, clean_size, normalize_string


def generate_payload(provider, generator, filtering, verify_name=True, verify_size=True):
    filtering.information(provider)
    results = []

    definition = definitions[provider]

    for name, info_hash, uri, size, seeds, peers in generator:
        size = clean_size(size)
        # uri, info_hash = clean_magnet(uri, info_hash)
        v_name = name if verify_name else filtering.title
        v_size = size if verify_size else None
        log.debug("name: %s \n info_hash: %s\n magnet: %s\n size: %s\n seeds: %s\n peers: %s" % (
                  name, info_hash, uri, size, seeds, peers))
        if filtering.verify(provider, v_name, v_size):
            results.append({"name": name,
                            "uri": uri,
                            "info_hash": info_hash,
                            "size": size,
                            "seeds": get_int(seeds),
                            "peers": get_int(peers),
                            "language": definition["language"] if 'language' in definition else 'en',
                            "provider": '[COLOR %s]%s[/COLOR]' % (definition['color'], definition['name']),
                            "icon": os.path.join(ADDON_PATH, 'libs', 'providers', 'icons', '%s.png' % provider),
                            })  # return the torrent
        else:
            log.debug(filtering.reason.encode('ascii', 'ignore'))

    log.debug('>>>>>> %s would send %d torrents to Quasar <<<<<<<' % (provider, len(results)))

    return results


def read_keywords(keywords):
    """
    Create list from string where the values are marked between curly brackets {example}
    :param keywords: string with the information
    :type keywords: str
    :return: list with collected keywords
    """
    results = []
    if keywords:
        for value in re.findall('{(.*?)}', keywords):
            results.append(value)
    return results


def process_keywords(provider, text, filtering):
    """
    Process the keywords in the query
    :param text: string to process
    :type text: str
    :return: str
    """
    keywords = read_keywords(text)

    for keyword in keywords:
        keyword = keyword.lower()
        if 'title' in keyword:
            title = filtering.info["title"]
            language = definitions[provider]['language']
            if language and filtering.info['titles']:
                try:
                    if language in filtering.info['titles']:
                        title = filtering.safe_name(filtering.info['titles'][language])
                        log.info("[%s] Using translated title '%s'" % (provider, title))
                        log.debug("[%s] Translated titles from Quasar: %s" % (provider, repr(filtering.info['titles'])))
                except Exception as e:
                    import traceback
                    log.error("%s failed with: %s" % (provider, repr(e)))
                    map(log.debug, traceback.format_exc().split("\n"))

            text = text.replace('{%s}' % keyword, title)

        if 'year' in keyword:
            text = text.replace('{%s}' % keyword, str(filtering.info["year"]))

        if 'season' in keyword:
            if '+' in keyword:
                keys = keyword.split('+')
                season = '%d%s' % (filtering.info["season"], keys[1])

            elif ':' in keyword:
                keys = keyword.split(':')
                season = ('%%.%sd' % keys[1]) % filtering.info["season"]

            else:
                season = '%s' % filtering.info["season"]

            text = text.replace('{%s}' % keyword, season)

        if 'episode' in keyword:
            if '+' in keyword:
                keys = keyword.split('+')
                episode = '%d%s' % (filtering.info["episode"], keys[1])

            elif ':' in keyword:
                keys = keyword.split(':')
                episode = ('%%.%sd' % keys[1]) % filtering.info["episode"]

            else:
                episode = '%s' % filtering.info["episode"]
            text = text.replace('{%s}' % keyword, episode)

    return text


def process(provider, generator, filtering, verify_name=True, verify_size=True):
    log.debug("execute_process for %s with %s" % (provider, repr(generator)))
    definition = definitions[provider]

    browser = Browser()

    # get the cloudhole key
    if get_setting("use_cloudhole", bool):
        browser.clearance = xbmcaddon.Addon('script.quasar.burst').getSetting('clearance')
        browser.user_agent = xbmcaddon.Addon('script.quasar.burst').getSetting('user_agent')

    log.debug("%s queries: %s" % (provider, filtering.queries))
    log.debug("%s extra: %s" % (provider, filtering.extras))

    # start the process
    for query, extra in zip(filtering.queries, filtering.extras):
        log.debug("[%s] - query: %s - extra: %s" % (provider, query, extra))
        query = process_keywords(provider, query, filtering)
        extra = process_keywords(provider, extra, filtering)
        log.debug("[%s] - query: %s - extra: %s" % (provider, query, extra))
        if query:
            url_search = filtering.url.replace('QUERY', query.replace(' ', definition['separator']))
            url_search = normalize_string(url_search)
            if extra:
                url_search = url_search.replace('EXTRA', extra.replace(' ', definition['separator']))
            else:
                url_search = url_search.replace('EXTRA', '')

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
            if filtering.get_data is not None:
                data = dict()
                for key, value in filtering.get_data.iteritems():
                    if 'QUERY' in value:
                        data[key] = filtering.get_data[key].replace('QUERY', query)

                    else:
                        data[key] = filtering.get_data[key]

            log.debug(">>  %s query: %s" % (provider, query))
            log.debug(">>> %s url_search before token: %s" % (provider, url_search))
            log.debug("%s filtering with post_data: %s" % (provider, repr(filtering.post_data)))
            log.debug("%s using payload: %s" % (provider, repr(payload)))

            # to do filtering by name.. TODO what?
            filtering.title = query

            if 'token' in definition:
                token_url = definition['base_url'] + definition['token']
                log.debug("Getting token for %s at %s" % (provider, token_url))
                browser.open(token_url)
                token_data = json.loads(browser.content)
                log.debug("Token response for %s: %s" % (provider, repr(token_data)))
                if 'token' in token_data:
                    token = token_data['token']
                    log.debug("Got token for %s: %s" % (provider, token))
                    url_search = url_search.replace('TOKEN', token)
                else:
                    log.warning('%s: Unable to get token for %s' % (provider, url_search))

            if 'private' in definition and definition['private']:
                # TODO All the conditional private provider settings for user/pass...
                username = get_setting('%s_username' % provider)
                password = get_setting('%s_password' % provider)
                try:
                    if not username:
                        username = xbmcaddon.Addon('script.magnetic.%s' % provider).getSetting('username')
                        set_setting('%s_username' % provider, username)
                except:
                    pass
                try:
                    if not username:
                        username = xbmcaddon.Addon('script.magnetic.%s-mc' % provider).getSetting('username')
                        set_setting('%s_username' % provider, username)
                except:
                    pass
                try:
                    if not password:
                        password = xbmcaddon.Addon('script.magnetic.%s' % provider).getSetting('password')
                        set_setting('%s_password' % provider, password)
                except:
                    pass
                try:
                    if not password:
                        password = xbmcaddon.Addon('script.magnetic.%s-mc' % provider).getSetting('password')
                        set_setting('%s_password' % provider, password)
                except:
                    pass

                if username and password:
                    login_object = definition['login_object'].replace('USERNAME', '"%s"' % username).replace('PASSWORD', '"%s"' % password)

                    if provider == 'alphareign':  # TODO generic flags in definitions?
                        browser.open(definition['root_url'])
                        if browser.content:
                            csrf_name = re.search('name="csrf_name" value="(.*?)"', browser.content)
                            csrf_value = re.search('name="csrf_value" value="(.*?)"', browser.content)
                            login_object.replace("CSRF_NAME", '"%s"' % csrf_name)
                            login_object.replace("CSRF_VALUE", '"%s"' % csrf_value)

                    # log.debug("Logging in with %s" % login_object)
                    if browser.login(definition['root_url'] + definition['login_path'],
                                     eval(login_object), definition['login_failed']):
                        log.info('[%s] Login successful' % provider)

            log.info("> %s search URL: %s" % (provider, url_search))

            # requesting the QUERY and adding info
            browser.open(url_search, post_data=payload, get_data=data, use_cache=False)
            filtering.results.extend(
                generate_payload(provider,
                                 generator(provider, browser),
                                 filtering,
                                 verify_name,
                                 verify_size))
    return filtering.results
