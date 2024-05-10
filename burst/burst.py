# -*- coding: utf-8 -*-

"""
Burst processing thread
"""

from __future__ import unicode_literals
from future.utils import PY3, iteritems

import re
import json
import time
import requests
import datetime
from threading import Thread
from elementum.provider import append_headers, get_setting, set_setting, log

if PY3:
    from queue import Queue
    from urllib.parse import urlparse
    from urllib.parse import unquote

    basestring = str
    long = int
    unicode = str
else:
    from Queue import Queue
    from urlparse import urlparse
    from urllib import unquote

from .parser.ehp import Html
from kodi_six import xbmc, xbmcgui, xbmcaddon, py2_encode

try:
    from Cryptodome.Cipher import AES
    from Cryptodome.Util.Padding import unpad
    hasCrypto = True
except:
    hasCrypto = False

from .provider import process
from .providers.definitions import definitions, longest
from .filtering import apply_filters, Filtering, cleanup_results
from .client import USER_AGENT, Client
from .utils import ADDON_ICON, notify, translation, sizeof, get_icon_path, get_enabled_providers, get_alias, size_int

provider_names = []
provider_results = []
provider_cache = {}
available_providers = 0
request_time = time.time()

use_kodi_language = get_setting('kodi_language', bool)
auto_timeout = get_setting("auto_timeout", bool)
timeout = get_setting("timeout", int)
debug_parser = get_setting("use_debug_parser", bool)
max_results = get_setting('max_results', int)
sort_by = get_setting('sort_by', int)

cookie_sync_enabled = get_setting("cookie_sync_enabled", bool)
cookie_sync_token = get_setting("cookie_sync_token", unicode)
cookie_sync_password = get_setting("cookie_sync_password", unicode)
cookie_sync_gist_id = get_setting("cookie_sync_gist_id", unicode)
cookie_sync_filename = get_setting("cookie_sync_filename", unicode)
cookie_sync_fileurl = get_setting("cookie_sync_fileurl", unicode)

special_chars = "()\"':.[]<>/\\?"
elementum_timeout = 0

elementum_addon = xbmcaddon.Addon(id='plugin.video.elementum')
if elementum_addon:
    if elementum_addon.getSetting('custom_provider_timeout_enabled') == "true":
        elementum_timeout = int(elementum_addon.getSetting('custom_provider_timeout'))
    else:
        elementum_timeout = 30
    log.info("Using timeout from Elementum: %d seconds" % (elementum_timeout))

# Make sure timeout is always less than the one from Elementum.
if auto_timeout:
    timeout = elementum_timeout - 3
elif elementum_timeout > 0 and timeout > elementum_timeout - 3:
    log.info("Redefining timeout to be less than Elementum's: %d to %d seconds" % (timeout, elementum_timeout - 3))
    timeout = elementum_timeout - 3

def search(payload, method="general"):
    """ Main search entrypoint

    Args:
        payload (dict): Search payload from Elementum.
        method   (str): Type of search, can be ``general``, ``movie``, ``season`` or ``episode``

    Returns:
        list: All filtered results in the format Elementum expects
    """
    log.debug("Searching with payload (%s): %s" % (method, repr(payload)))

    if method == 'episode' and 'anime' in payload and payload['anime']:
        method = 'anime'

    if method == 'general':
        if 'query' in payload:
            payload['title'] = payload['query']
            payload['titles'] = {
                'source': payload['query'],
                'original': payload['query']
            }
        else:
            payload = {
                'title': payload,
                'titles': {
                    'source': payload,
                    'original': payload
                },
            }

    payload['titles'] = dict((k.lower(), v) for k, v in iteritems(payload['titles']))

    # If titles[] exists in payload and there are special chars in titles[source]
    #   then we set a flag to possibly modify the search query
    payload['has_special'] = 'titles' in payload and \
                             bool(payload['titles']) and \
                             'source' in payload['titles'] and \
                             any(c in payload['titles']['source'] for c in special_chars)
    if payload['has_special']:
        log.debug("Query title contains special chars, so removing any quotes in the search query")
    if 'episode' not in payload:
        payload['episode'] = 0

    if 'proxy_url' not in payload:
        payload['proxy_url'] = ''
    if 'internal_proxy_url' not in payload:
        payload['internal_proxy_url'] = ''
    if 'elementum_url' not in payload:
        payload['elementum_url'] = ''
    if 'silent' not in payload:
        payload['silent'] = False
    if 'skip_auth' not in payload:
        payload['skip_auth'] = False

    global request_time
    global provider_cache
    global provider_names
    global provider_results
    global available_providers

    provider_cache = {}
    provider_names = []
    provider_results = []
    available_providers = 0
    request_time = time.time()

    cookie_sync()
    providers = get_enabled_providers(method)

    if len(providers) == 0:
        if not payload['silent']:
            notify(translation(32060), image=get_icon_path())
        log.error("No providers enabled")
        return []

    log.info("Burstin' with %s" % ", ".join([definitions[provider]['name'] for provider in providers]))

    if use_kodi_language:
        kodi_language = xbmc.getLanguage(xbmc.ISO_639_1)
        if not kodi_language:
            log.warning("Kodi returned empty language code...")
        elif 'titles' not in payload or not payload['titles']:
            log.info("No translations available...")
        elif payload['titles'] and kodi_language not in payload['titles']:
            log.info("No '%s' translation available..." % kodi_language)

    p_dialog = xbmcgui.DialogProgressBG()
    if not payload['silent']:
        p_dialog.create('Elementum [COLOR FFFF6B00]Burst[/COLOR]', translation(32061))

    if 'titles' in payload:
        log.debug("Translated titles from Elementum: %s" % (repr(payload['titles'])))

    providers_time = time.time()

    for provider in providers:
        available_providers += 1
        provider_names.append(definitions[provider]['name'])
        task = Thread(target=run_provider, args=(provider, payload, method, providers_time, timeout))
        task.start()

    total = float(available_providers)

    # Exit if all providers have returned results or timeout reached, check every 100ms
    while time.time() - providers_time < timeout and available_providers > 0:
        timer = time.time() - providers_time
        log.debug("Timer: %ds / %ds" % (timer, timeout))
        if timer > timeout:
            break
        message = translation(32062) % available_providers if available_providers > 1 else translation(32063)
        if not payload['silent']:
            p_dialog.update(int((total - available_providers) / total * 100), message=message)
        time.sleep(0.25)

    if not payload['silent']:
        p_dialog.close()
    del p_dialog

    if available_providers > 0:
        message = ', '.join(provider_names)
        message = message + translation(32064)
        log.warning(message)
        if not payload['silent']:
            notify(message, ADDON_ICON)

    log.debug("all provider_results of %d: %s" % (len(provider_results), repr(provider_results)))

    filtered_results = apply_filters(provider_results)

    log.debug("all filtered_results of %d: %s" % (len(filtered_results), repr(filtered_results)))

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
    definition = get_alias(definition, get_setting("%s_alias" % provider))

    # 0 "Resolution"
    # 1 "Seeds"
    # 2 "Size"
    # 3 "Balanced"

    if not sort_by or sort_by == 3 or sort_by > 3:
        # TODO: think of something interesting to balance sort results
        sorted_results = sorted(results, key=lambda r: (r['sort_balance']), reverse=True)
    elif sort_by == 0:
        sorted_results = sorted(results, key=lambda r: (r['sort_resolution']), reverse=True)
    elif sort_by == 1:
        sorted_results = sorted(results, key=lambda r: (r['seeds']), reverse=True)
    elif sort_by == 2:
        sorted_results = sorted(results, key=lambda r: (size_int(r['size'])), reverse=True)

    if len(sorted_results) > max_results:
        sorted_results = sorted_results[:max_results]

    log.info("[%s] >> %s returned %2d results in %.1f seconds%s" % (
        provider, definition['name'].rjust(longest), len(results), round(time.time() - request_time, 2),
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
    definition = get_alias(definition, get_setting("%s_alias" % provider))
    log.debug("[%s] Extracting torrents from %s using definitions: %s" % (provider, provider, repr(definition)))

    if not client.content:
        if debug_parser:
            log.debug("[%s] Parser debug | Page content is empty" % provider)

        raise StopIteration

    dom = Html().feed(client.content)

    id_search = get_search_query(definition, "id")
    key_search = get_search_query(definition, "key")
    row_search = get_search_query(definition, "row")
    name_search = get_search_query(definition, "name")
    torrent_search = get_search_query(definition, "torrent")
    info_hash_search = get_search_query(definition, "infohash")
    size_search = get_search_query(definition, "size")
    seeds_search = get_search_query(definition, "seeds")
    peers_search = get_search_query(definition, "peers")
    referer_search = get_search_query(definition, "referer")

    log.debug("[%s] Parser: %s" % (provider, repr(definition['parser'])))

    q = Queue()
    threads = []
    needs_subpage = 'subpage' in definition and definition['subpage']

    if needs_subpage:
        def extract_subpage(q, id, name, torrent, size, seeds, peers, info_hash, referer):
            try:
                log.debug("[%s] Getting subpage at %s" % (provider, repr(torrent)))
            except Exception as e:
                import traceback
                log.error("[%s] Subpage logging failed with: %s" % (provider, repr(e)))
                map(log.debug, traceback.format_exc().split("\n"))

            # New client instance, otherwise it's race conditions all over the place
            subclient = Client()
            subclient.passkey = client.passkey
            headers = {}

            if "subpage_mode" in definition:
                if definition["subpage_mode"] == "xhr":
                    headers['X-Requested-With'] = 'XMLHttpRequest'
                    headers['Content-Language'] = ''

            if referer:
                headers['Referer'] = referer

            uri = torrent.split('|')  # Split cookies for private trackers
            subclient.open(py2_encode(uri[0]), headers=headers)

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

            log.debug("[%s] Subpage torrent for %s: %s" % (provider, repr(uri[0]), torrent))
            ret = (id, name, info_hash, torrent, size, seeds, peers)

            # Cache this subpage result if another query would need to request same url.
            provider_cache[uri[0]] = torrent
            q.put_nowait(ret)

    if not dom:
        if debug_parser:
            log.debug("[%s] Parser debug | Could not parse DOM from page content" % provider)

        raise StopIteration

    if debug_parser:
        log.debug("[%s] Parser debug | Page content: %s" % (provider, client.content.replace('\r', '').replace('\n', '')))

    key = eval(key_search) if key_search else ""
    if key_search and debug_parser:
        key_str = key.__str__()
        log.debug("[%s] Parser debug | Matched '%s' iteration for query '%s': %s" % (provider, 'key', key_search, key_str.replace('\r', '').replace('\n', '')))

    items = eval(row_search)
    if debug_parser:
        log.debug("[%s] Parser debug | Matched %d items for '%s' query '%s'" % (provider, len(items), 'row', row_search))

    for item in items:
        if debug_parser:
            item_str = item.__str__()
            log.debug("[%s] Parser debug | Matched '%s' iteration for query '%s': %s" % (provider, 'row', row_search, item_str.replace('\r', '').replace('\n', '')))

        if not item:
            continue

        try:
            id = eval(id_search) if id_search else ""
            name = eval(name_search) if name_search else ""
            torrent = eval(torrent_search) if torrent_search else ""
            size = eval(size_search) if size_search else ""
            seeds = eval(seeds_search) if seeds_search else ""
            peers = eval(peers_search) if peers_search else ""
            info_hash = eval(info_hash_search) if info_hash_search else ""
            referer = eval(referer_search) if referer_search else ""

            if 'magnet:?' in torrent:
                torrent = torrent[torrent.find('magnet:?'):]

            if debug_parser:
                log.debug("[%s] Parser debug | Matched '%s' iteration for query '%s': %s" % (provider, 'id', id_search, id))
                log.debug("[%s] Parser debug | Matched '%s' iteration for query '%s': %s" % (provider, 'name', name_search, name))
                log.debug("[%s] Parser debug | Matched '%s' iteration for query '%s': %s" % (provider, 'torrent', torrent_search, torrent))
                log.debug("[%s] Parser debug | Matched '%s' iteration for query '%s': %s" % (provider, 'size', size_search, size))
                log.debug("[%s] Parser debug | Matched '%s' iteration for query '%s': %s" % (provider, 'seeds', seeds_search, seeds))
                log.debug("[%s] Parser debug | Matched '%s' iteration for query '%s': %s" % (provider, 'peers', peers_search, peers))
                if info_hash_search:
                    log.debug("[%s] Parser debug | Matched '%s' iteration for query '%s': %s" % (provider, 'info_hash', info_hash_search, info_hash))
                if referer_search:
                    log.debug("[%s] Parser debug | Matched '%s' iteration for query '%s': %s" % (provider, 'info_hash', referer_search, referer))

            # Pass client cookies with torrent if private
            if not torrent.startswith('magnet'):
                user_agent = USER_AGENT

                if not torrent.startswith('http'):
                    torrent = definition['root_url'] + py2_encode(torrent)

                if client.passkey:
                    torrent = torrent.replace('PASSKEY', client.passkey)
                elif client.token:
                    headers = {'Authorization': client.token, 'User-Agent': user_agent}
                    log.debug("[%s] Appending headers: %s" % (provider, repr(headers)))
                    torrent = append_headers(torrent, headers)
                    log.debug("[%s] Torrent with headers: %s" % (provider, repr(torrent)))
                else:
                    parsed_url = urlparse(torrent.split('|')[0])
                    cookie_domain = '{uri.netloc}'.format(uri=parsed_url)
                    cookie_domain = re.sub('www\d*\.', '', cookie_domain)
                    cookies = {}

                    # Collect cookies used in request
                    if client.request_cookies:
                        for item in client.request_cookies.split(';'):
                            item = item.strip()
                            if not item:
                                continue
                            if '=' not in item:
                                cookies[item] = None
                                continue
                            k, v = item.split('=', 1)
                            cookies[k] = v

                    # Collect session cookies for current domain
                    for cookie in client._cookies:
                        if cookie.domain in cookie_domain:
                            cookies[cookie.name] = cookie.value

                    headers = {'User-Agent': user_agent}
                    if client.request_headers:
                        headers.update(client.request_headers)

                    if client.url:
                        headers['Referer'] = client.url
                        headers['Origin'] = client.url

                    if cookies:
                        # Need to set Cookie afterwards to avoid rewriting it with session Cookies
                        headers['Cookie'] = ";".join(["%s=%s" % (k, v) for (k, v) in iteritems(cookies)])

                    torrent = append_headers(torrent, headers)

            if name and torrent and needs_subpage and not torrent.startswith('magnet'):
                if not torrent.startswith('http'):
                    torrent = definition['root_url'] + py2_encode(torrent)
                # Check if this url was previously requested, to avoid doing same job again.
                uri = torrent.split('|')
                if uri and uri[0] and uri[0] in provider_cache and provider_cache[uri[0]]:
                    yield (id, name, info_hash, provider_cache[uri[0]], size, seeds, peers)
                    continue

                t = Thread(target=extract_subpage, args=(q, id, name, torrent, size, seeds, peers, info_hash, referer))
                threads.append(t)
            else:
                yield (id, name, info_hash, torrent, size, seeds, peers)
        except Exception as e:
            log.error("[%s] Got an exception while parsing results: %s" % (provider, repr(e)))

    if needs_subpage:
        log.debug("[%s] Starting subpage threads..." % provider)
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        for i in range(q.qsize()):
            ret = q.get_nowait()
            log.debug("[%s] Queue %d got: %s" % (provider, i, repr(ret)))
            yield ret

    # Save cookies in cookie jar
    client.save_cookies()

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
    log.debug("[%s] JSON response from API: %s" % (unquote(provider), repr(data)))

    definition = definitions[provider]
    definition = get_alias(definition, get_setting("%s_alias" % provider))
    api_format = definition['api_format']

    def get_nested_value(result, key, default):
        keys = key.split('.')
        for key in keys:
            if key in result:
                result = result[key]
            else:
                result = default
        return result

    results = []
    # If 'results' is empty - then we can try to take all the data as an array of results.
    # Usable when api returns results without any other data.
    if not api_format['results']:
        results = data
    else:
        results = get_nested_value(data, api_format['results'], [])
    log.debug("[%s] results: %s" % (provider, repr(results)))

    if 'subresults' in api_format:  # A little too specific to YTS/AniLibria but who cares...
        from copy import deepcopy
        subresults = []
        for result in results:
            subresults_keys = api_format['subresults'].split('.')
            for key in subresults_keys:
                if key in result:
                    if isinstance(result[key], list):
                        for subresult in result[key]:
                            sub = deepcopy(result)
                            sub.update(subresult)
                            subresults.append(sub)
                    elif isinstance(result[key], dict):
                        sub = deepcopy(result)
                        sub.update(result[key])
                        result = sub
        results = subresults
        log.debug("[%s] with subresults: %s" % (provider, repr(results)))

    for result in results:
        if not result or not isinstance(result, dict):
            continue
        id = ''
        name = ''
        info_hash = ''
        torrent = ''
        size = ''
        seeds = ''
        peers = ''
        if 'id' in api_format:
            id = result[api_format['id']]
        if 'name' in api_format:
            name = get_nested_value(result, api_format['name'], "")
        if 'description' in api_format:
            if name:
                name += ' '
            name += get_nested_value(result, api_format['description'], "")
        if 'torrent' in api_format:
            torrent = result[api_format['torrent']]
            if 'download_path' in definition:
                torrent = definition['download_path'] + torrent
            if client.token:
                user_agent = USER_AGENT
                headers = {'Authorization': client.token, 'User-Agent': user_agent}
                log.debug("[%s] Appending headers: %s" % (provider, repr(headers)))
                torrent = append_headers(torrent, headers)
                log.debug("[%s] Torrent with headers: %s" % (provider, repr(torrent)))
        if 'info_hash' in api_format:
            info_hash = result[api_format['info_hash']]
        if 'quality' in api_format:  # Again quite specific to YTS and AniLibria
            name = "%s - %s" % (name, get_nested_value(result, api_format['quality'], ""))
        if 'size' in api_format:
            size = result[api_format['size']]
            if isinstance(size, (long, int)):
                size = sizeof(size)
            elif isinstance(size, basestring) and size.isdigit():
                size = sizeof(int(size))
        if 'seeds' in api_format:
            seeds = result[api_format['seeds']]
            if isinstance(seeds, basestring) and seeds.isdigit():
                seeds = int(seeds)
        if 'peers' in api_format:
            peers = result[api_format['peers']]
            if isinstance(peers, basestring) and peers.isdigit():
                peers = int(peers)
        yield (id, name, info_hash, torrent, size, seeds, peers)


def extract_from_page(provider, content):
    """ Sub-page extraction method

    Args:
        provider (str): Provider ID
        content  (str): Page content from Client instance

    Returns:
        str: Torrent or magnet link extracted from sub-page
    """
    definition = definitions[provider]
    definition = get_alias(definition, get_setting("%s_alias" % provider))

    try:
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

        matches = re.findall('"(/download/[A-Za-z0-9]+)"', content)
        if matches:
            result = definition['root_url'] + matches[0]
            log.debug('[%s] Matched download link: %s' % (provider, repr(result)))
            return result

        matches = re.findall('/torrents/download/\?id=[a-z0-9-_.]+', content)  # t411
        if matches:
            result = definition['root_url'] + matches[0]
            log.debug('[%s] Matched download link with an ID: %s' % (provider, repr(result)))
            return result

        matches = re.findall('\: ([A-Fa-f0-9]{40})', content)
        if matches:
            result = "magnet:?xt=urn:btih:" + matches[0]
            log.debug('[%s] Matched magnet info_hash search: %s' % (provider, repr(result)))
            return result

        matches = re.findall('/download.php\?id=([A-Za-z0-9]{40})\W', content)
        if matches:
            result = "magnet:?xt=urn:btih:" + matches[0]
            log.debug('[%s] Matched download link: %s' % (provider, repr(result)))
            return result

        matches = re.findall('(/download.php\?id=[A-Za-z0-9]+[^\s\'"]*)', content)
        if matches:
            result = definition['root_url'] + matches[0]
            log.debug('[%s] Matched download link: %s' % (provider, repr(result)))
            return result

        matches = re.findall('/get_torrent/([A-Fa-f0-9]{40})', content)
        if matches:
            result = "magnet:?xt=urn:btih:" + matches[0]
            log.debug('[%s] Matched magnet info_hash search: %s' % (provider, repr(result)))
            return result
    except:
        pass

    return None


def run_provider(provider, payload, method, start_time, timeout):
    """ Provider thread entrypoint

    Args:
        provider   (str): Provider ID
        payload   (dict): Search payload from Elementum
        method     (str): Type of search, can be ``general``, ``movie``, ``show``, ``season`` or ``anime``
        start_time (int): Time when search has been started
        timeout    (int): Time limit for searching
    """
    log.debug("[%s] Processing %s with %s method" % (provider, provider, method))

    filterInstance = Filtering()

    # collect languages, defined for this provider
    filterInstance.define_languages(provider)

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
        results = process(provider=provider, generator=extract_from_api, filtering=filterInstance, has_special=payload['has_special'], skip_auth=payload['skip_auth'], start_time=start_time, timeout=timeout)
    else:
        results = process(provider=provider, generator=extract_torrents, filtering=filterInstance, has_special=payload['has_special'], skip_auth=payload['skip_auth'], start_time=start_time, timeout=timeout)

    # Cleanup results from duplcates before limiting each provider's results.
    results = cleanup_results(results)
    got_results(provider, results)

def get_search_query(definition, key):
    if 'parser' not in definition or key not in definition['parser']:
        return ""

    if key == 'key' or key == 'table' or key == 'row':
        return "dom." + definition['parser'][key]
    return definition['parser'][key]

def cookie_sync():
    if not cookie_sync_enabled or not cookie_sync_token:
        return

    if not hasCrypto:
        log.error("Cryptodome Python module is not available for current Kodi version")
        return

    cookie_check_defaults()

    log.debug("Fetching cookies from Github")

    global cookie_sync_gist_id
    # Try to get url to a Gist's file first, if we have Gist ID
    if not cookie_sync_gist_id or not cookie_fetch_fileurl():
        # Try to get both Gist ID and Gist's file url
        if not cookie_fetch_gist_id():
            log.error("Could not fetch gist id for cookie-sync")
            return

    set_setting('cookie_sync_gist_id', cookie_sync_gist_id)
    set_setting('cookie_sync_fileurl', cookie_sync_fileurl)

    cookies = cookie_fetch_file()
    if not cookies:
        return

    try:
        log.debug("Adding %d cookies to http client" % (len(cookies)))
        client = Client()
        client._read_cookies()

        for cookie in cookies:
            client.add_cookie(cookie)

        client.save_cookies()
    except Exception as e:
        log.error("Failed adding cookies with: %s" % (repr(e)))

def cookie_check_defaults():
    global cookie_sync_filename
    if not cookie_sync_filename:
        cookie_sync_filename = "kevast-gist-default.json"

def cookie_fetch_gist_id():
    global cookie_sync_gist_id, cookie_sync_token, cookie_sync_filename, cookie_sync_fileurl

    try:
        url = "https://api.github.com/gists"
        headers = {'Authorization': 'Bearer %s' % cookie_sync_token}
        params = {'scope': 'gist'}
        resp = requests.get(url, headers=headers, params=params)
        resp_items = json.loads(resp.text)

        for item in resp_items:
            if "files" not in item or "id" not in item:
                continue
            for k, v in iteritems(item["files"]):
                if "filename" not in v or v["filename"] != cookie_sync_filename:
                    continue
                cookie_sync_gist_id = item["id"]
                cookie_sync_fileurl = v["raw_url"]

                return True
    except Exception as e:
        log.error("Gist list failed with: %s" % (repr(e)))

    return False

def cookie_fetch_fileurl():
    global cookie_sync_gist_id, cookie_sync_token, cookie_sync_filename, cookie_sync_fileurl

    try:
        url = "https://api.github.com/gists/%s" % (cookie_sync_gist_id)
        headers = {'Authorization': 'Bearer %s' % cookie_sync_token}
        resp = requests.get(url, headers=headers)
        item = json.loads(resp.text)

        if "files" not in item or "id" not in item:
            return False
        for k, v in iteritems(item["files"]):
            if "filename" not in v or v["filename"] != cookie_sync_filename:
                continue
            cookie_sync_gist_id = item["id"]
            cookie_sync_fileurl = v["raw_url"]

            return True
    except Exception as e:
        log.error("Gist get failed with: %s" % (repr(e)))

    return False

def cookie_fetch_file():
    try:
        domains_count = 0
        cookies_count = 0

        cookies = []

        resp = requests.get(cookie_sync_fileurl)
        resp_items = json.loads(resp.text)

        expires = datetime.datetime.utcnow() + datetime.timedelta(days=1000)

        for k, v in iteritems(resp_items):
            if k.startswith("__"):
                continue

            domains_count = domains_count + 1

            # Decode data if encrypted
            if cookie_sync_password:
                v = aes_decode(v)

            # Loop through and force cookies into cookie jar
            for cookie in json.loads(py2_encode(v)):
                cookie["domain"] = k

                if "expirationDate" not in cookie or not cookie["expirationDate"]:
                    datetime.datetime.utcnow() + datetime.timedelta(days=30)
                    cookie["expirationDate"] = int(expires.timestamp())
                else:
                    cookie["expirationDate"] = int(cookie["expirationDate"])
                cookie["rest"] = {'HttpOnly': cookie["httpOnly"]}

                cookies.append(cookie)
                cookies_count = cookies_count + 1

        log.debug("Cookie sync fetched for %d domains, %d cookies" % (domains_count, cookies_count))
        return cookies
    except Exception as e:
        log.error("Gist file download failed with: %s" % (repr(e)))
        import traceback
        map(log.error, traceback.format_exc().split("\n"))

    return None

def EVP_BytesToKey(password, salt, key_len, iv_len):
    """
    Derive the key and the IV from the given password and salt.
    """
    from hashlib import md5
    dtot = md5(password + salt).digest()
    d = [dtot]
    while len(dtot) < (iv_len+key_len):
        d.append(md5(d[-1] + password + salt).digest())
        dtot += d[-1]
    return dtot[:key_len], dtot[key_len:key_len+iv_len]

def aes_decode(data):
    try:
        key, iv = EVP_BytesToKey(cookie_sync_password.encode('utf-8'), b'', 16, 16)
    except:
        key, iv = EVP_BytesToKey(py2_encode(cookie_sync_password), b'', 16, 16)

    aes = AES.new(key, AES.MODE_CBC, IV=iv)
    raw = aes.decrypt(bytes.fromhex(data))
    return unpad(raw, block_size=AES.block_size)
