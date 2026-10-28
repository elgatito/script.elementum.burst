# -*- coding: utf-8 -*-

"""
Burst processing thread
"""

import re
import json
import time
import requests
import traceback
from binascii import unhexlify
from threading import BoundedSemaphore, Event, Lock, Thread
from elementum.provider import append_headers, get_setting, set_setting, log
from queue import Queue
from urllib.parse import urlparse, unquote

from .parser.ehp import Html
import xbmc
import xbmcgui

try:
    from Cryptodome.Cipher import AES
    from Cryptodome.Util.Padding import unpad
    hasCrypto = True
except:
    hasCrypto = False

from .provider import process
from .providers.definitions import definitions, longest
from .filtering import apply_filters, Filtering, cleanup_results
from .client import Client, change_agent, elementum_addon
from .utils import ADDON_ICON, notify, translation, sizeof, get_icon_path, get_enabled_providers, get_alias, size_int, domain_matches, clear_errors, get_errors

provider_names = []
provider_results = []
provider_cache = {}
available_providers = 0
request_time = time.time()
results_lock = Lock()
providers_done = Event()
parser_code = {}
# Concurrent subpage requests per provider, more only gets us rate limited
SUBPAGE_THREADS = 10

use_kodi_language = get_setting('kodi_language', bool)
auto_timeout = get_setting("auto_timeout", bool)
timeout = get_setting("timeout", int)
debug_parser = get_setting("use_debug_parser", bool)
max_results = get_setting('max_results', int)
sort_by = get_setting('sort_by', int)

cookie_sync_enabled = get_setting("cookie_sync_enabled", bool)
cookie_sync_token = get_setting("cookie_sync_token", str)
cookie_sync_password = get_setting("cookie_sync_password", str)
cookie_sync_gist_id = get_setting("cookie_sync_gist_id", str)
cookie_sync_filename = get_setting("cookie_sync_filename", str)
cookie_sync_fileurl = get_setting("cookie_sync_fileurl", str)
# Gist file content, if it came inline with the gist info, saves a request for the file itself
cookie_sync_content = None

special_chars = "()\"':.[]<>/\\?"

elementum_timeout = 30
if elementum_addon.getSetting('custom_provider_timeout_enabled') == "true":
    try:
        elementum_timeout = int(elementum_addon.getSetting('custom_provider_timeout'))
    except ValueError:
        log.warning("Invalid custom provider timeout in Elementum, using %d seconds" % elementum_timeout)
log.info("Using timeout from Elementum: %d seconds" % (elementum_timeout))

# Make sure timeout is always less than the one from Elementum.
if auto_timeout:
    timeout = elementum_timeout - 3
elif elementum_timeout > 0 and timeout > elementum_timeout - 3:
    log.info("Redefining timeout to be less than Elementum's: %d to %d seconds" % (timeout, elementum_timeout - 3))
    timeout = elementum_timeout - 3

# Time when results are not needed anymore, set again for each search()
search_deadline = time.time() + timeout

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
        if isinstance(payload, dict) and 'query' in payload:
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

    payload['titles'] = dict((k.lower(), v) for k, v in payload['titles'].items())

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
    global search_deadline
    global provider_cache
    global provider_names
    global provider_results
    global available_providers

    provider_cache = {}
    provider_names = []
    provider_results = []
    available_providers = 0
    request_time = time.time()
    providers_done.clear()
    clear_errors()

    cookie_sync(payload['silent'])
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
    # Separate progress handle, Kodi rotates it with the search progress so errors show up while searching
    error_dialog = None
    error_message = None
    if not payload['silent']:
        p_dialog.create('Elementum [COLOR FFFF6B00]Burst[/COLOR]', translation(32061))

    if 'titles' in payload:
        log.debug("Translated titles from Elementum: %s" % (repr(payload['titles'])))

    providers_time = time.time()
    search_deadline = providers_time + timeout

    # Count all providers before starting any, so an early finished one can't bring the counter to zero
    available_providers = len(providers)
    provider_names = [definitions[provider]['name'] for provider in providers]
    for provider in providers:
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
            errors = get_errors()
            if errors:
                message = ' | '.join(errors)
                if error_dialog is None:
                    error_dialog = xbmcgui.DialogProgressBG()
                    error_dialog.create('Elementum [COLOR FFFF6B00]Burst[/COLOR] errors', message)
                elif message != error_message:
                    error_dialog.update(-1, message=message)
                error_message = message
        providers_done.wait(0.25)

    if not payload['silent']:
        p_dialog.close()
    del p_dialog

    errors = get_errors()
    if error_dialog is not None:
        error_dialog.close()
    del error_dialog

    if errors and not payload['silent']:
        notify("\n".join(errors), ADDON_ICON, time=10000)

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

    with results_lock:
        provider_results.extend(sorted_results)
        available_providers -= 1
        if definition['name'] in provider_names:
            provider_names.remove(definition['name'])
        if available_providers <= 0:
            providers_done.set()


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

        return

    dom = Html().feed(client.content)

    key_search = get_search_query(definition, "key")
    row_search = get_search_query(definition, "row")
    name_search = get_search_query(definition, "name")
    description_search = get_search_query(definition, "description")
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
        subpage_slots = BoundedSemaphore(SUBPAGE_THREADS)

        def extract_subpage(q, name, torrent, size, seeds, peers, info_hash, referer):
            try:
                log.debug("[%s] Getting subpage at %s" % (provider, repr(torrent)))
            except Exception as e:
                log.error("[%s] Subpage logging failed with: %s" % (provider, repr(e)))
                log.debug(traceback.format_exc())

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
            with subpage_slots:
                # Subpages still waiting for a slot when search is over would be thrown away anyway
                if time.time() >= search_deadline:
                    return
                subclient.open(uri[0], headers=headers)

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
                    log.error("[%s] Subpage extraction for %s failed with: %s" % (provider, repr(uri[0]), repr(e)))
                    log.debug(traceback.format_exc())

            log.debug("[%s] Subpage torrent for %s: %s" % (provider, repr(uri[0]), torrent))
            ret = (name, info_hash, torrent, size, seeds, peers)

            # Cache this subpage result if another query would need to request same url.
            provider_cache[uri[0]] = torrent
            q.put_nowait(ret)

    if not dom:
        if debug_parser:
            log.debug("[%s] Parser debug | Could not parse DOM from page content" % provider)

        return

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
            name = eval(compiled(name_search)) if name_search else ""
            description = eval(compiled(description_search)) if description_search else ""
            torrent = eval(compiled(torrent_search)) if torrent_search else ""
            size = eval(compiled(size_search)) if size_search else ""
            seeds = eval(compiled(seeds_search)) if seeds_search else ""
            peers = eval(compiled(peers_search)) if peers_search else ""
            info_hash = eval(compiled(info_hash_search)) if info_hash_search else ""
            referer = eval(compiled(referer_search)) if referer_search else ""

            if 'magnet:?' in torrent:
                torrent = torrent[torrent.find('magnet:?'):]

            if debug_parser:
                log.debug("[%s] Parser debug | Matched '%s' iteration for query '%s': %s" % (provider, 'name', name_search, name))
                log.debug("[%s] Parser debug | Matched '%s' iteration for query '%s': %s" % (provider, 'description', description_search, description))
                log.debug("[%s] Parser debug | Matched '%s' iteration for query '%s': %s" % (provider, 'torrent', torrent_search, torrent))
                log.debug("[%s] Parser debug | Matched '%s' iteration for query '%s': %s" % (provider, 'size', size_search, size))
                log.debug("[%s] Parser debug | Matched '%s' iteration for query '%s': %s" % (provider, 'seeds', seeds_search, seeds))
                log.debug("[%s] Parser debug | Matched '%s' iteration for query '%s': %s" % (provider, 'peers', peers_search, peers))
                if info_hash_search:
                    log.debug("[%s] Parser debug | Matched '%s' iteration for query '%s': %s" % (provider, 'info_hash', info_hash_search, info_hash))
                if referer_search:
                    log.debug("[%s] Parser debug | Matched '%s' iteration for query '%s': %s" % (provider, 'referer', referer_search, referer))

            if description:
                name = '{} ({})'.format(name, description)

            # Pass client cookies with torrent if private
            if not torrent.startswith('magnet'):
                user_agent = client.user_agent

                if not torrent.startswith('http'):
                    torrent = definition['root_url'] + torrent

                if client.passkey:
                    torrent = torrent.replace('PASSKEY', client.passkey)
                elif client.token:
                    headers = {'Authorization': client.token, 'User-Agent': user_agent}
                    log.debug("[%s] Appending headers: %s" % (provider, repr(headers)))
                    torrent = append_headers(torrent, headers)
                    log.debug("[%s] Torrent with headers: %s" % (provider, repr(torrent)))
                else:
                    parsed_url = urlparse(torrent.split('|')[0])
                    cookie_domain = re.sub(r'^www\d*\.', '', parsed_url.hostname or '')
                    cookies = {}

                    # Collect cookies used in request
                    if client.request_cookies:
                        for pair in client.request_cookies.split(';'):
                            pair = pair.strip()
                            if not pair:
                                continue
                            if '=' not in pair:
                                cookies[pair] = None
                                continue
                            k, v = pair.split('=', 1)
                            cookies[k] = v

                    # Collect session cookies for current domain
                    for cookie in client._cookies:
                        if domain_matches(cookie_domain, cookie.domain):
                            cookies[cookie.name] = cookie.value

                    headers = {'User-Agent': user_agent}
                    if client.request_headers:
                        headers.update(client.request_headers)

                    if client.url:
                        headers['Referer'] = client.url
                        headers['Origin'] = client.url

                    if cookies:
                        # Need to set Cookie afterwards to avoid rewriting it with session Cookies
                        headers['Cookie'] = ";".join(["%s=%s" % (k, v) for (k, v) in cookies.items()])

                    torrent = append_headers(torrent, headers)

            if name and torrent and needs_subpage and not torrent.startswith('magnet'):
                if not torrent.startswith('http'):
                    torrent = definition['root_url'] + torrent
                # Check if this url was previously requested, to avoid doing same job again.
                uri = torrent.split('|')
                if uri and uri[0] and uri[0] in provider_cache and provider_cache[uri[0]]:
                    yield (name, info_hash, provider_cache[uri[0]], size, seeds, peers)
                    continue

                t = Thread(target=extract_subpage, args=(q, name, torrent, size, seeds, peers, info_hash, referer))
                threads.append(t)
            else:
                yield (name, info_hash, torrent, size, seeds, peers)
        except Exception as e:
            log.error("[%s] Got an exception while parsing results: %s" % (provider, repr(e)))

    if needs_subpage:
        log.debug("[%s] Starting subpage threads..." % provider)
        for t in threads:
            t.start()
        for t in threads:
            t.join(max(0, search_deadline - time.time()))

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
        name = ''
        info_hash = ''
        torrent = ''
        size = ''
        seeds = ''
        peers = ''

        if provider == 'torrentio':
            title = result.get('title', '').encode('unicode-escape').decode('utf-8')
            match = re.search(r"\\U0001f464\s(\d+)", title)
            seeds = match.group(1) if match else ''
            match = re.search("\\b(\\d+(?:\\.\\d+)? [MG]B)\\b", title)
            size = match.group(1) if match else ''

        if 'name' in api_format:
            name = get_nested_value(result, api_format['name'], "").replace('\n', ' ').replace('\r', '')
        if 'description' in api_format:
            if name:
                name += ' '
            name += get_nested_value(result, api_format['description'], "")
        if 'torrent' in api_format:
            torrent = result.get(api_format['torrent']) or ''
            if 'download_path' in definition and torrent:
                torrent = definition['download_path'] + torrent
            if client.token:
                headers = {'Authorization': client.token, 'User-Agent': client.user_agent}
                log.debug("[%s] Appending headers: %s" % (provider, repr(headers)))
                torrent = append_headers(torrent, headers)
                log.debug("[%s] Torrent with headers: %s" % (provider, repr(torrent)))
        if 'info_hash' in api_format:
            info_hash = result.get(api_format['info_hash']) or ''
        if 'quality' in api_format:  # Again quite specific to YTS and AniLibria
            name = "%s - %s" % (name, get_nested_value(result, api_format['quality'], ""))
        if 'size' in api_format:
            size = result.get(api_format['size'])
            if isinstance(size, int):
                size = sizeof(size)
            elif isinstance(size, str) and size.isdigit():
                size = sizeof(int(size))
        if 'seeds' in api_format:
            seeds = result.get(api_format['seeds'])
            if isinstance(seeds, str) and seeds.isdigit():
                seeds = int(seeds)
        if 'peers' in api_format:
            peers = result.get(api_format['peers'])
            if isinstance(peers, str) and peers.isdigit():
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
    definition = get_alias(definition, get_setting("%s_alias" % provider))

    try:
        matches = re.findall(r'magnet:\?[^\'"\s<>\[\]]+', content)
        if matches:
            result = matches[0]
            result = result.replace('xt.1=', 'xt=')  # libtorrent does not support xt groups
            log.debug('[%s] Matched magnet link: %s' % (provider, repr(result)))
            return result

        matches = re.findall(r'http(.*?).torrent["\']', content)
        if matches:
            result = 'http' + matches[0] + '.torrent'
            result = result.replace('torcache.net', 'itorrents.org')
            log.debug('[%s] Matched torrent link: %s' % (provider, repr(result)))
            return result

        matches = re.findall(r'/download\?token=[A-Za-z0-9%]+', content)
        if matches:
            result = definition['root_url'] + matches[0]
            log.debug('[%s] Matched download link with token: %s' % (provider, repr(result)))
            return result

        matches = re.findall(r'"(/download/[A-Za-z0-9]+)"', content)
        if matches:
            result = definition['root_url'] + matches[0]
            log.debug('[%s] Matched download link: %s' % (provider, repr(result)))
            return result

        matches = re.findall(r'/torrents/download/\?id=[a-z0-9-_.]+', content)  # t411
        if matches:
            result = definition['root_url'] + matches[0]
            log.debug('[%s] Matched download link with an ID: %s' % (provider, repr(result)))
            return result

        matches = re.findall(r'\: ([A-Fa-f0-9]{40})', content)
        if matches:
            result = "magnet:?xt=urn:btih:" + matches[0]
            log.debug('[%s] Matched magnet info_hash search: %s' % (provider, repr(result)))
            return result

        matches = re.findall(r'/download.php\?id=([A-Fa-f0-9]{40})\W', content)
        if matches:
            result = "magnet:?xt=urn:btih:" + matches[0]
            log.debug('[%s] Matched magnet info_hash search: %s' % (provider, repr(result)))
            return result

        matches = re.findall(r'/engine/download.php\?id=[A-Za-z0-9]+[^\s\'"]*', content)  # animaunt
        if matches:
            result = definition['root_url'] + matches[0]
            result += "|Referer=" + result  # we need to add Referer header to download .torrent
            log.debug('[%s] Matched download link: %s' % (provider, repr(result)))
            return result

        matches = re.findall(r'(/download.php\?id=[A-Za-z0-9]+[^\s\'"]*)', content)
        if matches:
            result = definition['root_url'] + matches[0]
            log.debug('[%s] Matched download link: %s' % (provider, repr(result)))
            return result

        matches = re.findall(r'/get_torrents?/([A-Fa-f0-9]{40})', content)
        if matches:
            result = "magnet:?xt=urn:btih:" + matches[0]
            log.debug('[%s] Matched magnet info_hash search: %s' % (provider, repr(result)))
            return result

        matches = re.findall(r'/hash/([A-Fa-f0-9]{40})', content)  # bt4g
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
    results = []
    try:
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
            results = process(provider=provider, generator=extract_from_api, filtering=filterInstance, has_special=payload['has_special'], skip_auth=payload['skip_auth'], start_time=start_time, timeout=timeout, is_silent=payload['silent'])
        else:
            results = process(provider=provider, generator=extract_torrents, filtering=filterInstance, has_special=payload['has_special'], skip_auth=payload['skip_auth'], start_time=start_time, timeout=timeout, is_silent=payload['silent'])

        # Cleanup results from duplcates before limiting each provider's results.
        results = cleanup_results(results)
    except Exception as e:
        log.error("[%s] Provider failed with: %s" % (provider, repr(e)))
        log.debug(traceback.format_exc())
    finally:
        # Always report back, otherwise search() waits for the full timeout
        got_results(provider, results)

def compiled(expression):
    """ Compiles parser expression once, eval() of a string compiles it again on every call """
    code = parser_code.get(expression)
    if code is None:
        code = parser_code[expression] = compile(expression, '<parser>', 'eval')
    return code

def get_search_query(definition, key):
    if 'parser' not in definition or key not in definition['parser']:
        return ""

    if key == 'key' or key == 'table' or key == 'row':
        return "dom." + definition['parser'][key]
    return definition['parser'][key]

def cookie_sync(is_silent):
    if not cookie_sync_enabled or not cookie_sync_token:
        return

    if not hasCrypto:
        log.error("Cryptodome Python module is not available for current Kodi version")
        return

    cookie_check_defaults()

    log.debug("Fetching cookies from Github")

    p_dialog = xbmcgui.DialogProgressBG()
    if not is_silent:
        p_dialog.create('Elementum [COLOR FFFF6B00]Burst[/COLOR]', translation(32166))

    # Try to get url to a Gist's file first, if we have Gist ID
    if not cookie_sync_gist_id or not cookie_fetch_fileurl():
        # Try to get both Gist ID and Gist's file url
        if not cookie_fetch_gist_id():
            err = "Could not fetch gist id for cookie-sync"
            log.error(err)

            if not is_silent:
                p_dialog.close()
                notify(translation(32167) % (err), image=get_icon_path())
            del p_dialog

            return

    set_setting_if_changed('cookie_sync_gist_id', cookie_sync_gist_id)
    set_setting_if_changed('cookie_sync_fileurl', cookie_sync_fileurl)

    userAgent, cookies = cookie_fetch_file()
    if userAgent:
        set_setting_if_changed('cookie_sync_useragent', userAgent)
        log.debug("Persisted user-agent for cookie-sync: %s" % (repr(userAgent)))
        change_agent(userAgent)
    if not cookies:
        if not is_silent:
            p_dialog.close()
        del p_dialog
        return

    err = None
    try:
        log.debug("Adding %d cookies to http client" % (len(cookies)))
        client = Client()
        client._read_cookies()

        for cookie in cookies:
            client.add_cookie(cookie)

        client.save_cookies()
    except Exception as e:
        log.error("Failed adding cookies with: %s" % (repr(e)))
        err = e

    if not is_silent:
        p_dialog.close()
        if err:
            notify(translation(32167) % (err), image=get_icon_path())
    del p_dialog

def set_setting_if_changed(key, value):
    # Every set_setting() makes Kodi write the settings file
    if get_setting(key, str) != value:
        set_setting(key, value)

def cookie_check_defaults():
    global cookie_sync_filename
    if not cookie_sync_filename:
        cookie_sync_filename = "kevast-gist-default.json"

def cookie_fetch_gist_id():
    global cookie_sync_gist_id, cookie_sync_fileurl, cookie_sync_content

    try:
        url = "https://api.github.com/gists"
        headers = {'Authorization': 'Bearer %s' % cookie_sync_token}
        # Gists list is paginated, the first page alone misses the file for users with many gists
        for page in range(1, 11):
            resp = requests.get(url, headers=headers, params={'per_page': 100, 'page': page}, timeout=10)
            resp_items = json.loads(resp.text)
            if not isinstance(resp_items, list) or not resp_items:
                break

            for item in resp_items:
                if "files" not in item or "id" not in item:
                    continue
                for k, v in item["files"].items():
                    if "filename" not in v or v["filename"] != cookie_sync_filename:
                        continue
                    cookie_sync_gist_id = item["id"]
                    cookie_sync_fileurl = v["raw_url"]
                    cookie_sync_content = None  # Gists list does not include files content

                    return True
    except Exception as e:
        log.error("Gist list failed with: %s" % (repr(e)))

    return False

def cookie_fetch_fileurl():
    global cookie_sync_gist_id, cookie_sync_fileurl, cookie_sync_content

    try:
        url = "https://api.github.com/gists/%s" % (cookie_sync_gist_id)
        headers = {'Authorization': 'Bearer %s' % cookie_sync_token}
        resp = requests.get(url, headers=headers, timeout=10)
        item = json.loads(resp.text)

        if "files" not in item or "id" not in item:
            return False
        for k, v in item["files"].items():
            if "filename" not in v or v["filename"] != cookie_sync_filename:
                continue
            cookie_sync_gist_id = item["id"]
            cookie_sync_fileurl = v["raw_url"]
            cookie_sync_content = v["content"] if v.get("content") and not v.get("truncated") else None

            return True
    except Exception as e:
        log.error("Gist get failed with: %s" % (repr(e)))

    return False

def cookie_fetch_file():
    try:
        domains_count = 0
        cookies_count = 0

        cookies = []

        if cookie_sync_content:
            resp_items = json.loads(cookie_sync_content)
        else:
            resp = requests.get(cookie_sync_fileurl, timeout=10)
            resp_items = json.loads(resp.text)

        expires = int(time.time()) + 1000 * 86400

        # Persisted user-agent can be stored as "__userAgent" or "userAgent", it's not a domain with cookies
        userAgent = resp_items.get("__userAgent") or resp_items.get("userAgent")
        if userAgent and cookie_sync_password:
            userAgent = aes_decode(userAgent).decode('utf-8')

        for k, v in resp_items.items():
            if k.startswith("__") or k == "userAgent":
                continue

            domains_count = domains_count + 1

            # Decode data if encrypted
            if cookie_sync_password:
                v = aes_decode(v)

            # Loop through and force cookies into cookie jar
            try:
                for cookie in json.loads(v):
                    cookie["domain"] = k

                    if "expirationDate" not in cookie or not cookie["expirationDate"]:
                        cookie["expirationDate"] = expires
                    else:
                        cookie["expirationDate"] = int(cookie["expirationDate"])
                    cookie["rest"] = {'HttpOnly': cookie.get("httpOnly", False)}

                    cookies.append(cookie)
                    cookies_count = cookies_count + 1
            except Exception as e:
                log.error("Failed parsing cookies for %s with: %s" % (k, repr(e)))
                log.error(traceback.format_exc())
        log.debug("Cookie sync fetched for %d domains, %d cookies" % (domains_count, cookies_count))
        return userAgent, cookies
    except Exception as e:
        log.error("Gist file download failed with: %s" % (repr(e)))
        log.error(traceback.format_exc())

    return None, None

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
    key, iv = EVP_BytesToKey(cookie_sync_password.encode('utf-8'), b'', 16, 16)

    aes = AES.new(key, AES.MODE_CBC, IV=iv)
    raw = aes.decrypt(unhexlify(data))
    return unpad(raw, block_size=AES.block_size)
