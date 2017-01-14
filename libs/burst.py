# -*- coding: utf-8 -*-

import re
import json
import time
import xbmcgui
from threading import Thread
from urlparse import urlparse
from quasar.provider import extract_magnets, append_headers, get_setting, set_setting, log

from parser.ehp import Html
from provider import process
from providers.definitions import definitions
from filtering import apply_filters, Filtering
from browser import Browser, get_cloudhole_key, get_cloudhole_clearance
from utils import ADDON_ICON, notify, string, sizeof, get_icon_path, get_enabled_providers

provider_names = []
provider_results = []
available_providers = 0
request_time = time.time()
timeout = get_setting("timeout", int)


def search(payload, method="general"):
    log.debug("Searching with payload (%s): %s" % (method, repr(payload)))

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
        notify(string(32060), image=get_icon_path())
        log.error("No providers enabled")
        return []

    log.info("Burstin' with %s" % ", ".join([definitions[provider]['name'] for provider in providers]))

    if get_setting("use_cloudhole", bool):
        clearance, user_agent = get_cloudhole_clearance(get_cloudhole_key())
        set_setting('clearance', clearance)
        set_setting('user_agent', user_agent)

    p_dialog = xbmcgui.DialogProgressBG()
    p_dialog.create('Quasar [COLOR FFFF6B00]Burst[/COLOR]', string(32061))
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
        message = string(32062) % available_providers if available_providers > 1 else string(32063)
        p_dialog.update(int((total - available_providers) / total * 100), message=message)
        time.sleep(0.25)

    p_dialog.close()
    del p_dialog

    if available_providers > 0:
        message = ', '.join(provider_names)
        message = message + string(32064)
        log.warning(message)
        notify(message, ADDON_ICON)

    log.debug("all provider_results: %s" % repr(provider_results))

    filtered_results = apply_filters(provider_results)

    log.debug("all filtered_results: %s" % repr(filtered_results))

    log.info("Providers returned %d results in %s seconds" % (len(filtered_results), round(time.time() - request_time, 2)))

    return filtered_results


def got_results(provider, results):
    global provider_names
    global provider_results
    global available_providers
    definition = definitions[provider]

    max_results = get_setting('max_results', int)
    sorted_results = sorted(results, key=lambda r: (r['seeds']), reverse=True)
    if len(sorted_results) > max_results:
        sorted_results = sorted_results[:max_results]

    log.info(">> %s provider returned %d results in %.1f seconds%s" % (
            definition['name'], len(results), round(time.time() - request_time, 2),
            (", sending %d best ones" % max_results) if len(results) > max_results else ""))

    provider_results.extend(sorted_results)
    available_providers -= 1
    if definition['name'] in provider_names:
        provider_names.remove(definition['name'])


def extract_torrents(provider, browser):
    """
     Main torrent extractor
    """
    definition = definitions[provider]
    log.debug("Extracting torrents from %s using definitions: %s" % (provider, repr(definition)))

    if browser.content is None:
        raise StopIteration

    dom = Html().feed(browser.content)

    row_search = "dom." + definition['parser']['row']
    name_search = definition['parser']['name']
    torrent_search = definition['parser']['torrent']
    info_hash_search = definition['parser']['infohash']
    size_search = definition['parser']['size']
    seeds_search = definition['parser']['seeds']
    peers_search = definition['parser']['peers']

    log.debug("[%s] Parser: %s" % (provider, repr(definition['parser'])))

    from Queue import Queue
    q = Queue()
    threads = []
    needs_subpage = 'subpage' in definition and definition['subpage']

    if needs_subpage:
        from threading import Thread

        def extract_subpage(q, name, torrent, size, seeds, peers, info_hash):
            try:
                log.debug(u"[%s] Getting subpage at %s" % (provider, torrent.decode('ascii', 'ignore')))
            except Exception as e:
                import traceback
                log.error("[%s] Subpage logging failed with: %s" % (provider, repr(e)))
                map(log.debug, traceback.format_exc().split("\n"))

            # New browser instance, otherwise it's race conditions all over the place
            subbrowser = Browser()

            uri = torrent.split('|')  # Split cookies for private trackers
            subbrowser.open(uri[0])

            if 'bittorrent' in subbrowser.headers.get('content-type', ''):
                log.debug('[%s] bittorrent content-type for %s' % (provider, torrent))
                if len(uri) > 1:  # Stick back cookies if needed
                    torrent = '%s|%s' % (torrent, uri[1])
            else:
                try:
                    magnet = next(extract_magnets(subbrowser.content))
                    log.debug(u"[%s] Magnet from %s: %s" % (provider, uri[0], magnet['uri']))
                    torrent = magnet['uri']
                except:
                    try:
                        torrent = extract_from_page(provider, subbrowser.content)
                        if torrent and len(uri) > 1:  # Stick back cookies if needed
                            torrent = '%s|%s' % (torrent, uri[1])
                    except Exception as e:
                        import traceback
                        log.error("[%s] Subpage extraction for %s failed with: %s" % (provider, uri[0], repr(e)))
                        map(log.debug, traceback.format_exc().split("\n"))

            ret = (name, info_hash, torrent, size, seeds, peers)
            q.put_nowait(ret)

    if dom is None:
        raise StopIteration

    for item in eval(row_search):
        if item is None:
            continue
        name = eval(name_search)
        torrent = eval(torrent_search) if torrent_search else ""
        size = eval(size_search) if size_search else ""
        seeds = eval(seeds_search) if seeds_search else ""
        peers = eval(peers_search) if peers_search else ""
        info_hash = eval(info_hash_search) if info_hash_search else ""

        # Pass browser cookies with torrent if private
        if definition['private']:
            if browser.token:
                headers = {'Authorization': browser.token}
                log.debug("[%s] Appending headers: %s" % (provider, repr(headers)))
                torrent = append_headers(torrent, headers)
                log.debug("[%s] Torrent with headers: %s" % (provider, torrent))
            else:
                log.debug("[%s] Cookies: %s" % (provider, repr(browser.cookies())))
                parsed_url = urlparse(definition['root_url'])
                cookie_domain = '{uri.netloc}'.format(uri=parsed_url).replace('www.', '')
                cookies = []
                log.debug("[%s] cookie_domain: %s" % (provider, cookie_domain))
                for cookie in browser._cookies:
                    log.debug("[%s] cookie for domain: %s (%s=%s)" % (provider, cookie.domain, cookie.name, cookie.value))
                    if cookie_domain in cookie.domain:
                        cookies.append(cookie)
                if cookies:
                    headers = {'Cookie': ";".join(["%s=%s" % (c.name, c.value) for c in cookies])}
                    log.debug("[%s] Appending headers: %s" % (provider, repr(headers)))
                    torrent = append_headers(torrent, headers)
                    log.debug("[%s] Torrent with headers: %s" % (provider, torrent))

        if name and torrent and needs_subpage:
            if not torrent.startswith('http'):
                torrent = definition['root_url'] + torrent.decode('ascii', 'ignore')  # FIXME ignoring ascii chars will 404...
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


def extract_from_api(provider, browser):
    """
     An almost clever API parser, mostly just for YTS and RARBG
    """
    data = json.loads(browser.content)
    log.debug("[%s] JSON response from API: %s" % (provider, repr(data)))

    api_format = definitions[provider]['api_format']

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
        for result in results:  # A little too specific to YTS but who cares...
            result['name'] = result[api_format['name']]
        subresults = []
        subresults_keys = api_format['subresults'].split('.')
        for key in subresults_keys:
            for result in results:
                if key in result:
                    for torrent in result[key]:
                        torrent.update(result)
                        subresults.append(torrent)
        results = subresults
        log.debug("%s with subresults: %s" % (provider, repr(results)))

    for result in results:
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
        if 'info_hash' in api_format:
            info_hash = result[api_format['info_hash']]
        if 'quality' in api_format:
            name = "%s (%s)" % (name, result[api_format['quality']])
        if 'size' in api_format:
            size = result[api_format['size']]
            if type(size) in (long, int):
                size = sizeof(size)
        if 'seeds' in api_format:
            seeds = result[api_format['seeds']]
        if 'peers' in api_format:
            peers = result[api_format['peers']]
        yield (name, info_hash, torrent, size, seeds, peers)


def extract_from_page(provider, content):
    definition = definitions[provider]

    matches = re.findall('http(.*?).torrent["\']', content)
    if matches:
        result = 'http' + matches[0] + '.torrent'
        result = result.replace('torcache.net', 'itorrents.org')
        log.info('[%s] Matched torrent link: %s' % (provider, result))
        return result

    matches = re.findall('/download\?token=[A-Za-z0-9%]+', content)
    if matches:
        result = definition['root_url'] + matches[0]
        log.info('[%s] Matched download link with token: %s' % (provider, result))
        return result

    matches = re.findall('/telechargement/[a-z0-9-_.]+', content)  # cpasbien
    if matches:
        result = definition['root_url'] + matches[0]
        log.info('[%s] Matched some french link: %s' % (provider, result))
        return result

    matches = re.findall('/torrents/download/\?id=[a-z0-9-_.]+', content)  # t411
    if matches:
        result = definition['root_url'] + matches[0]
        log.info('[%s] Matched download link with an ID: %s' % (provider, result))
        return result

    return None


def run_provider(provider, payload, method):
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
