# -*- coding: utf-8 -*-

import os
import re
import json
import xbmcaddon
from urllib import quote
from browser import Browser
from quasar.provider import log, get_setting, set_setting
from providers.definitions import definitions, t411season, t411episode
from utils import ADDON_PATH, get_int, clean_size


def generate_payload(provider, generator, filtering, verify_name=True, verify_size=True):
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
                            "icon": os.path.join(ADDON_PATH, 'libs', 'providers', 'icons', '%s.png' % provider),
                            })
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
            use_language = None
            if ':' in keyword:
                use_language = keyword.split(':')[1]
            if use_language and filtering.info['titles']:
                try:
                    if use_language not in filtering.info['titles']:
                        use_language = language
                    if use_language in filtering.info['titles'] and filtering.info['titles'][use_language]:
                        title = filtering.info['titles'][use_language]
                        title = title.replace('.', '')  # FIXME shouldn't be here...
                        log.info("[%s] Using translated '%s' title %s" % (provider, use_language,
                                                                          repr(title)))
                        log.debug("[%s] Translated titles from Quasar: %s" % (provider,
                                                                              repr(filtering.info['titles'])))
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
                if keys[1] == "t411season":
                    season = str(t411season(filtering.info['season']))
                else:
                    season = str(filtering.info["season"] + get_int(keys[1]))
            elif ':' in keyword:
                keys = keyword.split(':')
                season = ('%%.%sd' % keys[1]) % filtering.info["season"]
            else:
                season = '%s' % filtering.info["season"]
            text = text.replace('{%s}' % keyword, season)

        if 'episode' in keyword:
            if '+' in keyword:
                keys = keyword.split('+')
                if keys[1] == "t411episode":
                    episode = str(t411episode(filtering.info['episode']))
                else:
                    episode = str(filtering.info["episode"] + get_int(keys[1]))
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

    if get_setting("use_cloudhole", bool):
        browser.clearance = get_setting('clearance')
        browser.user_agent = get_setting('user_agent')

    log.debug("[%s] Queries: %s" % (provider, filtering.queries))
    log.debug("[%s] Extras:  %s" % (provider, filtering.extras))

    for query, extra in zip(filtering.queries, filtering.extras):
        log.debug("[%s] Before keywords - Query: %s - Extra: %s" % (provider, query, extra))
        query = process_keywords(provider, query, filtering)
        extra = process_keywords(provider, extra, filtering)
        log.debug("[%s] After keywords  - Query: %s - Extra: %s" % (provider, repr(query), repr(extra)))
        if not query:
            return filtering.results

        separated_query = query.replace(' ', definition['separator']) if definition['separator'] != '%20' else query
        separated_extra = extra.replace(' ', definition['separator']) if definition['separator'] != '%20' else extra

        url_search = filtering.url.replace('QUERY', quote(separated_query).encode('utf-8'))
        if extra:
            url_search = url_search.replace('EXTRA', separated_extra.encode('utf-8'))
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
                    data[key] = filtering.get_data[key].replace('QUERY', query.encode('utf-8'))
                else:
                    data[key] = filtering.get_data[key]

        log.debug("-   %s query: %s" % (provider, repr(query)))
        log.debug("--  %s url_search before token: %s" % (provider, url_search))
        log.debug("--- %s using POST payload: %s" % (provider, repr(payload)))
        log.debug("----%s filtering with post_data: %s" % (provider, repr(filtering.post_data)))

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
            username = get_setting('%s_username' % provider)
            password = get_setting('%s_password' % provider)
            if not username and not password:
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

            if username and password:
                login_object = definition['login_object'].replace('USERNAME', '"%s"' % username).replace('PASSWORD', '"%s"' % password)

                if provider == 'alphareign':  # TODO generic flags in definitions?
                    browser.open(definition['root_url'] + definition['login_path'])
                    if browser.content:
                        csrf_name = re.search(r'name="csrf_name" value="(.*?)"', browser.content)
                        csrf_value = re.search(r'name="csrf_value" value="(.*?)"', browser.content)
                        login_object.replace("CSRF_NAME", '"%s"' % csrf_name)
                        login_object.replace("CSRF_VALUE", '"%s"' % csrf_value)

                if 'token_auth' in definition:
                    # log.debug("[%s] logging in with: %s" % (provider, login_object))
                    if browser.open(definition['root_url'] + definition['token_auth'], post_data=eval(login_object)):
                        token_data = json.loads(browser.content)
                        log.debug("Token response for %s: %s" % (provider, repr(token_data)))
                        if 'token' in token_data:
                            browser.token = token_data['token']
                            log.debug("Auth token for %s: %s" % (provider, browser.token))
                        else:
                            log.warning('%s: Unable to get auth token for %s' % (provider, url_search))
                        log.info('[%s] login successful' % provider)
                    else:
                        log.error("[%s] login failed for token authorization: %s" % (provider, repr(browser.content)))

                # log.debug("[%s] logging in with %s" % (provider, login_object))
                elif browser.login(definition['root_url'] + definition['login_path'],
                                   eval(login_object), definition['login_failed']):
                    log.info('[%s] login successful' % provider)

        log.info("> %s search URL: %s" % (provider, url_search))

        browser.open(url_search, post_data=payload, get_data=data, use_cache=False)
        filtering.results.extend(
            generate_payload(provider,
                             generator(provider, browser),
                             filtering,
                             verify_name,
                             verify_size))
    return filtering.results
