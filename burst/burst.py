# -*- coding: utf-8 -*-

"""
Burst processing thread
"""

import re
import json
import time
import xbmc
import xbmcgui
from Queue import Queue
from threading import Thread
from urlparse import urlparse
from quasar.provider import append_headers, get_setting, set_setting, log

from parser.ehp import Html
from provider import process
from providers.definitions import definitions, longest
from filtering import apply_filters, Filtering
from client import USER_AGENT, Client, get_cloudhole_key, get_cloudhole_clearance
from utils import ADDON_ICON, notify, translation, sizeof, get_icon_path, get_enabled_providers

provider_names = []
provider_results = []
available_providers = 0
request_time = time.time()
timeout = get_setting("timeout", int)


def search(payload, method="general"):
    """ Main search entrypoint

    Args:
        payload (dict): Search payload from Quasar.
        method   (str): Type of search, can be ``general``, ``movie``, ``show``, ``season`` or ``anime``

    Returns:
        list: All filtered results in the format Quasar expects
    """
    log.debug("Searching with payload (%s): %s" % (method, repr(payload)))

    if method == 'general':
        payload = {
            'title': payload
        }

    global request_time
    global provider_names
    global provider_results
    global available_providers

    provider_names = []
    provider_results = []
    available_providers = 0
    request_time = time.time()

    providers = get_enabled_providers()

    if len(providers) == 0:
        notify(translation(32060), image=get_icon_path())
        log.error("No providers enabled")
        return []

    log.info("Burstin' with %s" % ", ".join([definitions[provider]['name'] for provider in providers]))

    if get_setting("use_cloudhole", bool):
        clearance, user_agent = get_cloudhole_clearance(get_cloudhole_key())
        set_setting('clearance', clearance)
        set_setting('user_agent', user_agent)

    if get_setting('kodi_language', bool):
        kodi_language = xbmc.getLanguage(xbmc.ISO_639_1)
        if not kodi_language:
            log.warning("Kodi returned empty language code...")
        elif 'titles' not in payload or not payload['titles']:
            log.info("No translations available...")
        elif payload['titles'] and kodi_language not in payload['titles']:
            log.info("No '%s' translation available..." % kodi_language)

    p_dialog = xbmcgui.DialogProgressBG()
    p_dialog.create('Quasar [COLOR FFFF6B00]Burst[/COLOR]', translation(32061))
    for provider in providers:
        available_providers += 1
        provider_names.append(definitions[provider]['name'])
        task = Thread(target=run_provider, args=(provider, payload, method))
        task.start()

    providers_time = time.time()
    total = float(available_providers)

    # Exit if all providers have returned results or timeout reached, check every 100ms
    while time.time() - providers_time < timeout and available_providers > 0:
        timer = time.time() - providers_time
        log.debug("Timer: %ds / %ds" % (timer, timeout))
        if timer > timeout:
            break
        message = translation(32062) % available_providers if available_providers > 1 else translation(32063)
        p_dialog.update(int((total - available_providers) / total * 100), message=message)
        time.sleep(0.25)

    p_dialog.close()
    del p_dialog

    if available_providers > 0:
        message = u', '.join(provider_names)
        message = message + translation(32064)
        log.warning(message.encode('utf-8'))
        notify(message, ADDON_ICON)

    log.debug("all provider_results: %s" % repr(provider_results))

    filtered_results = apply_filters(provider_results)

    log.debug("all filtered_results: %s" % repr(filtered_results))

    log.info("Providers returned %d results in %s seconds" % (len(filtered_results), round(time.time() - request_time, 2)))

    return filtered_results


def got_results(provider, results):
    """ Results callback once a provider found all its results, or not

    Args:
        provider (str): The provider ID
        results (list): The list of results
    """
    global provider_names
    global provider_results
    global available_providers
    definition = definitions[provider]

    max_results = get_setting('max_results', int)
    sorted_results = sorted(results, key=lambda r: (r['seeds']), reverse=True)
    if len(sorted_results) > max_results:
        sorted_results = sorted_results[:max_results]

    log.info(">> %s returned %2d results in %.1f seconds%s" % (
            definition['name'].rjust(longest), len(results), round(time.time() - request_time, 2),
            (", sending %d best ones" % max_results) if len(results) > max_results else ""))

    provider_results.extend(sorted_results)
    available_providers -= 1
    if definition['name'] in provider_names:
        provider_names.remove(definition['name'])


def extract_torrents(provider, client):
    """ Main torrent extraction generator for non-API based providers

    Args:
        provider  (str): Provider ID
        client (Client): Client class instance

    Yields:
        tuple: A torrent result
    """
    definition = definitions[provider]
    log.debug("Extracting torrents from %s using definitions: %s" % (provider, repr(definition)))

    if not client.content:
        raise StopIteration

    dom = Html().feed(client.content)

    row_search = "dom." + definition['parser']['row']
    name_search = definition['parser']['name']
    torrent_search = definition['parser']['torrent']
    info_hash_search = definition['parser']['infohash']
    size_search = definition['parser']['size']
    seeds_search = definition['parser']['seeds']
    peers_search = definition['parser']['peers']

    log.debug("[%s] Parser: %s" % (provider, repr(definition['parser'])))

    q = Queue()
    threads = []
    needs_subpage = 'subpage' in definition and definition['subpage']

    if needs_subpage:
        def extract_subpage(q, name, torrent, size, seeds, peers, info_hash):
            try:
                log.debug("[%s] Getting subpage at %s" % (provider, repr(torrent)))
            except Exception as e:
                import traceback
                log.error("[%s] Subpage logging failed with: %s" % (provider, repr(e)))
                map(log.debug, traceback.format_exc().split("\n"))

            # New client instance, otherwise it's race conditions all over the place
            subclient = Client()
            subclient.passkey = client.passkey

            if get_setting("use_cloudhole", bool):
                subclient.clearance = get_setting('clearance')
                subclient.user_agent = get_setting('user_agent')

            uri = torrent.split('|')  # Split cookies for private trackers
            subclient.open(uri[0].encode('utf-8'))

            if 'bittorrent' in subclient.headers.get('content-type', ''):
                log.debug('[%s] bittorrent content-type for %s' % (provider, repr(torrent)))
                if len(uri) > 1:  # Stick back cookies if needed
                    torrent = '%s|%s' % (torrent, uri[1])
            else:
                try:
                    torrent = extract_from_page(provider, subclient.content)
                    if torrent and not torrent.startswith('magnet') and len(uri) > 1:  # Stick back cookies if needed
                        torrent = '%s|%s' % (torrent, uri[1])
                except Exception as e:
                    import traceback
                    log.error("[%s] Subpage extraction for %s failed with: %s" % (provider, repr(uri[0]), repr(e)))
                    map(log.debug, traceback.format_exc().split("\n"))

            ret = (name, info_hash, torrent, size, seeds, peers)
            q.put_nowait(ret)

    if not dom:
        raise StopIteration

    for item in eval(row_search):
        if not item:
            continue
        name = eval(name_search)
        torrent = eval(torrent_search) if torrent_search else ""
        size = eval(size_search) if size_search else ""
        seeds = eval(seeds_search) if seeds_search else ""
        peers = eval(peers_search) if peers_search else ""
        info_hash = eval(info_hash_search) if info_hash_search else ""

        # Pass client cookies with torrent if private
        if (definition['private'] or get_setting("use_cloudhole", bool)) and not torrent.startswith('magnet'):
            user_agent = USER_AGENT
            if get_setting("use_cloudhole", bool):
                user_agent = get_setting("user_agent")

            if client.passkey:
                torrent = torrent.replace('PASSKEY', client.passkey)
            elif client.token:
                headers = {'Authorization': client.token, 'User-Agent': user_agent}
                log.debug("[%s] Appending headers: %s" % (provider, repr(headers)))
                torrent = append_headers(torrent, headers)
                log.debug("[%s] Torrent with headers: %s" % (provider, repr(torrent)))
            else:
                log.debug("[%s] Cookies: %s" % (provider, repr(client.cookies())))
                parsed_url = urlparse(definition['root_url'])
                cookie_domain = '{uri.netloc}'.format(uri=parsed_url).replace('www.', '')
                cookies = []
                log.debug("[%s] cookie_domain: %s" % (provider, cookie_domain))
                for cookie in client._cookies:
                    log.debug("[%s] cookie for domain: %s (%s=%s)" % (provider, cookie.domain, cookie.name, cookie.value))
                    if cookie_domain in cookie.domain:
                        cookies.append(cookie)
                if cookies:
                    headers = {'Cookie': ";".join(["%s=%s" % (c.name, c.value) for c in cookies]), 'User-Agent': user_agent}
                    log.debug("[%s] Appending headers: %s" % (provider, repr(headers)))
                    torrent = append_headers(torrent, headers)
                    log.debug("[%s] Torrent with headers: %s" % (provider, repr(torrent)))

        if name and torrent and needs_subpage:
            if not torrent.startswith('http'):
                torrent = definition['root_url'] + torrent.encode('utf-8')
            t = Thread(target=extract_subpage, args=(q, name, torrent, size, seeds, peers, info_hash))
            threads.append(t)
        else:
            yield (name, info_hash, torrent, size, seeds, peers)

    if needs_subpage:
        log.debug("[%s] Starting subpage threads..." % provider)
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        log.debug("[%s] Threads returned: %s" % (provider, repr(threads)))

        for i in range(q.qsize()):
            ret = q.get_nowait()
            log.debug("[%s] Queue %d got: %s" % (provider, i, repr(ret)))
            yield ret


def extract_from_api(provider, client):
    """ Main API parsing generator for API-based providers

    An almost clever API parser, mostly just for YTS, RARBG and T411

    Args:
        provider  (str): Provider ID
        client (Client): Client class instance

    Yields:
        tuple: A torrent result
    """
    try:
        data = json.loads(client.content)
    except:
        data = []
    log.debug("[%s] JSON response from API: %s" % (provider, repr(data)))

    definition = definitions[provider]
    api_format = definition['api_format']

    results = []
    result_keys = api_format['results'].split('.')
    log.debug("%s result_keys: %s" % (provider, repr(result_keys)))
    for key in result_keys:
        if key in data:
            data = data[key]
        else:
            data = []
        # log.debug("%s nested results: %s" % (provider, repr(data)))
    results = data
    log.debug("%s results: %s" % (provider, repr(results)))

    if 'subresults' in api_format:
        from copy import deepcopy
        for result in results:  # A little too specific to YTS but who cares...
            result['name'] = result[api_format['name']]
        subresults = []
        subresults_keys = api_format['subresults'].split('.')
        for key in subresults_keys:
            for result in results:
                if key in result:
                    for subresult in result[key]:
                        sub = deepcopy(result)
                        sub.update(subresult)
                        subresults.append(sub)
        results = subresults
        log.debug("%s with subresults: %s" % (provider, repr(results)))

    for result in results:
        if not result or not isinstance(result, dict):
            continue
        name = ''
        info_hash = ''
        torrent = ''
        size = ''
        seeds = ''
        peers = ''
        if 'name' in api_format:
            name = result[api_format['name']]
        if 'torrent' in api_format:
            torrent = result[api_format['torrent']]
            if 'download_path' in definition:
                torrent = definition['base_url'] + definition['download_path'] + torrent
            if client.token:
                user_agent = USER_AGENT
                if get_setting("use_cloudhole", bool):
                    user_agent = get_setting("user_agent")
                headers = {'Authorization': client.token, 'User-Agent': user_agent}
                log.debug("[%s] Appending headers: %s" % (provider, repr(headers)))
                torrent = append_headers(torrent, headers)
                log.debug("[%s] Torrent with headers: %s" % (provider, repr(torrent)))
        if 'info_hash' in api_format:
            info_hash = result[api_format['info_hash']]
        if 'quality' in api_format:  # Again quite specific to YTS...
            name = "%s - %s" % (name, result[api_format['quality']])
        if 'size' in api_format:
            size = result[api_format['size']]
            if type(size) in (long, int):
                size = sizeof(size)
            elif type(size) in (str, unicode) and size.isdigit():
                size = sizeof(int(size))
        if 'seeds' in api_format:
            seeds = result[api_format['seeds']]
            if type(seeds) in (str, unicode) and seeds.isdigit():
                seeds = int(seeds)
        if 'peers' in api_format:
            peers = result[api_format['peers']]
            if type(peers) in (str, unicode) and peers.isdigit():
                peers = int(peers)
        yield (name, info_hash, torrent, size, seeds, peers)


def extract_from_page(provider, content):
    """ Sub-page extraction method

    Args:
        provider (str): Provider ID
        content  (str): Page content from Client instance

    Returns:
        str: Torrent or magnet link extracted from sub-page
    """
    definition = definitions[provider]

    matches = re.findall(r'magnet:\?[^\'"\s<>\[\]]+', content)
    if matches:
        result = matches[0]
        log.debug('[%s] Matched magnet link: %s' % (provider, repr(result)))
        return result

    matches = re.findall('http(.*?).torrent["\']', content)
    if matches:
        result = 'http' + matches[0] + '.torrent'
        result = result.replace('torcache.net', 'itorrents.org')
        log.debug('[%s] Matched torrent link: %s' % (provider, repr(result)))
        return result

    matches = re.findall('/download\?token=[A-Za-z0-9%]+', content)
    if matches:
        result = definition['root_url'] + matches[0]
        log.debug('[%s] Matched download link with token: %s' % (provider, repr(result)))
        return result

    matches = re.findall('/telechargement/[a-z0-9-_.]+', content)  # cpasbien
    if matches:
        result = definition['root_url'] + matches[0]
        log.debug('[%s] Matched some french link: %s' % (provider, repr(result)))
        return result

    matches = re.findall('/torrents/download/\?id=[a-z0-9-_.]+', content)  # t411
    if matches:
        result = definition['root_url'] + matches[0]
        log.debug('[%s] Matched download link with an ID: %s' % (provider, repr(result)))
        return result

    return None


def run_provider(provider, payload, method):
    """ Provider thread entrypoint

    Args:
        provider (str): Provider ID
        payload (dict): Search payload from Quasar
        method   (str): Type of search, can be ``general``, ``movie``, ``show``, ``season`` or ``anime``
    """
    log.debug("Processing %s with %s method" % (provider, method))

    filterInstance = Filtering()

    if method == 'movie':
        filterInstance.use_movie(provider, payload)
    elif method == 'season':
        filterInstance.use_season(provider, payload)
    elif method == 'episode':
        filterInstance.use_episode(provider, payload)
    elif method == 'anime':
        filterInstance.use_anime(provider, payload)
    else:
        filterInstance.use_general(provider, payload)

    if 'is_api' in definitions[provider]:
        results = process(provider=provider, generator=extract_from_api, filtering=filterInstance)
    else:
        results = process(provider=provider, generator=extract_torrents, filtering=filterInstance)

    got_results(provider, results)
