# -*- coding: utf-8 -*-

import re
import string
import hashlib
from urllib import unquote
from parser.ehp import normalize_string
from parser.HTMLParser import HTMLParser
from quasar.provider import log, get_setting
from providers.definitions import definitions, t411season, t411episode
from utils import Magnet, get_int, get_float, clean_number, size_int


class Filtering:
    """
    Filtering class

    Attributes:
        filters (dict): Dictionary of filters to be used depending on settings
        quality_allow (list): List of qualities to allow in search results
        quality_deny  (list): List of qualities to deny in search results
        require_keywords (list): List of keywords to require in search results
        min_size (float): Minimum required size
        max_size (float): Maximum possible size
        filter_title (bool): Whether or not this provider needs titles to be double-checked,
            typically used for providers that return too many results from their search
            engine when no results are found (eg. TorLock and TorrentZ)
        queries (list): List of queries to be filtered
        extras (list): List of extras to be filtered
        info (dict): Payload from Quasar
        kodi_language (str): Language code from Kodi if kodi_language setting is enabled
        url (str): URL of this filtering request
        get_data (dict): GET data for client request
        post_data (dict): POST data for client request
        title (str): Result title to be used when matching with ``filter_title`` enabled
        reason (str): Rejection reason when result does not match
        results (list): Filtered, accepted results
    """
    def __init__(self):
        self.filters = {
            'filter_480p': ['480p'],
            'filter_720p': ['720p'],
            'filter_1080p': ['1080p'],
            'filter_2k': ['_2k_', '1440p'],
            'filter_4k': ['_4k_', '2160p'],
            'filter_brrip': ['brrip', 'bdrip', 'bluray'],
            'filter_webdl': ['webdl', 'webrip'],
            'filter_hdrip': ['hdrip'],
            'filter_hdtv': ['hdtv'],
            'filter_dvd': ['_dvd_', 'dvdrip'],
            'filter_dvdscr': ['dvdscr'],
            'filter_screener': ['screener', '_scr_'],
            'filter_3d': ['_3d_'],
            'filter_telesync': ['telesync', '_ts_', '_tc_'],
            'filter_cam': ['_cam_', 'hdcam'],
            'filter_trailer': ['trailer']
        }

        qualities_allow = []
        qualities_deny = []
        require = []
        for quality in self.filters:
            if get_setting(quality, bool):
                qualities_allow.extend(self.filters[quality])
            else:
                qualities_deny.extend(self.filters[quality])

        if get_setting('additional_filters', bool):
            accept = get_setting('accept').strip()
            if accept:
                accept = re.split(r',\s?', accept)
                qualities_allow.extend(accept)

            block = get_setting('block')
            if block:
                block = re.split(r',\s?', block)
                qualities_deny.extend(block)

            require = get_setting('require')
            if require:
                require = re.split(r',\s?', require)

        self.quality_allow = qualities_allow
        self.quality_deny = qualities_deny
        self.require_keywords = require

        self.min_size = get_float(get_setting('min_size'))
        self.max_size = get_float(get_setting('max_size'))
        self.check_sizes()

        self.filter_title = False

        self.queries = []
        self.extras = []

        self.info = dict(title="", titles=[])
        self.kodi_language = ''
        self.get_data = {}
        self.post_data = {}
        self.url = ''
        self.title = ''
        self.reason = ''
        self.results = []

    def use_general(self, provider, payload):
        """ Setup method to define general search parameters

        Args:
            provider (str): Provider ID
            payload (dict): Quasar search payload
        """
        definition = definitions[provider]
        general_query = definition['general_query'] if definition['general_query'] else ''
        log.debug("General URL: %s%s" % (definition['base_url'], general_query))
        self.info = payload
        self.url = "%s%s" % (definition['base_url'], general_query)
        if definition['general_keywords']:
            self.queries = [definition['general_keywords']]
            self.extras = [definition['general_extra']]

    def use_movie(self, provider, payload):
        """ Setup method to define movie search parameters

        Args:
            provider (str): Provider ID
            payload (dict): Quasar search payload
        """
        definition = definitions[provider]
        movie_query = definition['movie_query'] if definition['movie_query'] else ''
        log.debug("Movies URL: %s%s" % (definition['base_url'], movie_query))
        if get_setting('separate_sizes', bool):
            self.min_size = get_float(get_setting('min_size_movies'))
            self.max_size = get_float(get_setting('max_size_movies'))
            self.check_sizes()
        self.info = payload
        self.url = "%s%s" % (definition['base_url'], movie_query)
        if definition['movie_keywords']:
            self.queries = ["%s" % definition['movie_keywords']]
            self.extras = ["%s" % definition['movie_extra']]

    def use_episode(self, provider, payload):
        """ Setup method to define episode search parameters

        Args:
            provider (str): Provider ID
            payload (dict): Quasar search payload
        """
        definition = definitions[provider]
        show_query = definition['show_query'] if definition['show_query'] else ''
        log.debug("Episode URL: %s%s" % (definition['base_url'], show_query))
        if get_setting('separate_sizes', bool):
            self.min_size = get_float(get_setting('min_size_episodes'))
            self.max_size = get_float(get_setting('max_size_episodes'))
            self.check_sizes()
        self.info = payload
        self.url = "%s%s" % (definition['base_url'], show_query)
        if definition['tv_keywords']:
            self.queries = ["%s" % definition['tv_keywords']]
            self.extras = ["%s" % definition['tv_extra'] if definition['tv_extra'] else '']
            # TODO this sucks, tv_keywords should be a list from the start..
            if definition['tv_keywords2']:
                self.queries.append(definition['tv_keywords2'])
                self.extras.append(definition['tv_extra2'] if definition['tv_extra2'] else '')

    def use_season(self, provider, info):
        """ Setup method to define season search parameters

        Args:
            provider (str): Provider ID
            payload (dict): Quasar search payload
        """
        definition = definitions[provider]
        season_query = definition['season_query'] if definition['season_query'] else ''
        log.debug("Season URL: %s%s" % (definition['base_url'], season_query))
        if get_setting('separate_sizes', bool):
            self.min_size = get_float(get_setting('min_size_seasons'))
            self.max_size = get_float(get_setting('max_size_seasons'))
            self.check_sizes()
        self.info = info
        self.url = "%s%s" % (definition['base_url'], season_query)
        if definition['season_keywords']:
            self.queries = ["%s" % definition['season_keywords']]
            self.extras = ["%s" % definition['season_extra'] if definition['season_extra'] else '']
            if definition['season_keywords2']:
                self.queries.append("%s" % definition['season_keywords2'])
                self.extras.append("%s" % definition['season_extra2'] if definition['season_extra2'] else '')

    def use_anime(self, provider, info):
        """ Setup method to define anime search parameters

        Args:
            provider (str): Provider ID
            payload (dict): Quasar search payload
        """
        definition = definitions[provider]
        anime_query = definition['anime_query'] if definition['anime_query'] else ''
        log.debug("Anime URL: %s%s" % (definition['base_url'], anime_query))
        if get_setting('separate_sizes', bool):
            self.min_size = get_float(get_setting('min_size_episodes'))
            self.max_size = get_float(get_setting('max_size_episodes'))
            self.check_sizes()
        self.info = info
        self.url = "%s%s" % (definition['base_url'], anime_query)
        if self.info['absolute_number']:
            self.info['episode'] = self.info['absolute_number']
        if definition['anime_keywords']:
            self.queries = ["%s" % definition['anime_keywords']]
            self.extras = ["%s" % definition['anime_extra'] if definition['anime_extra'] else '']

    def information(self, provider):
        """ Debugging method to print keywords and file sizes
        """
        log.debug('[%s] Accepted keywords: %s' % (provider, self.quality_allow))
        log.debug('[%s] Blocked keywords: %s' % (provider, self.quality_deny))
        log.debug('[%s] Minimum size: %s' % (provider, str(self.min_size) + ' GB'))
        log.debug('[%s] Maximum size: %s' % (provider, str(self.max_size) + ' GB'))

    def check_sizes(self):
        """ Internal method to trigger comparison of file sizes
        """
        if self.min_size > self.max_size:
            log.warning("Minimum size above maximum, using max size minus 1 GB")
            self.min_size = self.max_size - 1

    def read_keywords(self, keywords):
        """ Create list from keywords where the values are marked between curly brackets, ie. {title}

        Args:
            keywords (str): String with all the keywords, ie. '{title} {year} movie'

        Returns:
            list: List of keywords, ie. ['{title}', '{year}']
        """
        results = []
        if keywords:
            for value in re.findall('{(.*?)}', keywords):
                results.append(value)
        return results

    def process_keywords(self, provider, text):
        """ Processes the query payload from a provider's keyword definitions

        Args:
            provider (str): Provider ID
            text     (str): Keyword placeholders from definitions, ie. {title}

        Returns:
            str: Processed query keywords
        """
        keywords = self.read_keywords(text)

        for keyword in keywords:
            keyword = keyword.lower()
            if 'title' in keyword:
                title = self.info["title"]
                language = definitions[provider]['language']
                use_language = None
                if ':' in keyword:
                    use_language = keyword.split(':')[1]
                if (use_language or self.kodi_language) and 'titles' in self.info:
                    try:
                        if self.kodi_language and self.kodi_language in self.info['titles']:
                            use_language = self.kodi_language
                        if use_language not in self.info['titles']:
                            use_language = language
                        if use_language in self.info['titles'] and self.info['titles'][use_language]:
                            title = self.info['titles'][use_language]
                            title = self.normalize_name(title)
                            log.info("[%s] Using translated '%s' title %s" % (provider, use_language,
                                                                              repr(title)))
                            log.debug("[%s] Translated titles from Quasar: %s" % (provider,
                                                                                  repr(self.info['titles'])))
                    except Exception as e:
                        import traceback
                        log.error("%s failed with: %s" % (provider, repr(e)))
                        map(log.debug, traceback.format_exc().split("\n"))
                text = text.replace('{%s}' % keyword, title)

            if 'year' in keyword:
                text = text.replace('{%s}' % keyword, str(self.info["year"]))

            if 'season' in keyword:
                if '+' in keyword:
                    keys = keyword.split('+')
                    if keys[1] == "t411season":
                        season = str(t411season(self.info['season']))
                    else:
                        season = str(self.info["season"] + get_int(keys[1]))
                elif ':' in keyword:
                    keys = keyword.split(':')
                    season = ('%%.%sd' % keys[1]) % self.info["season"]
                else:
                    season = '%s' % self.info["season"]
                text = text.replace('{%s}' % keyword, season)

            if 'episode' in keyword:
                if '+' in keyword:
                    keys = keyword.split('+')
                    if keys[1] == "t411episode":
                        episode = str(t411episode(self.info['episode']))
                    else:
                        episode = str(self.info["episode"] + get_int(keys[1]))
                elif ':' in keyword:
                    keys = keyword.split(':')
                    episode = ('%%.%sd' % keys[1]) % self.info["episode"]
                else:
                    episode = '%s' % self.info["episode"]
                text = text.replace('{%s}' % keyword, episode)

        return text

    def verify(self, provider, name, size):
        """ Main filtering method to match torrent names and quality/size filters

        Args:
            provider (str): Provider ID
            name     (str): Torrent name
            size     (str): Arbitrary torrent size to be parsed

        Returns:
            bool: ``True`` if torrent name passed filtering, ``False`` otherwise.
        """
        if not name:
            self.reason = '[%s] %s' % (provider, '*** Empty name ***')
            return False

        name = self.exception(name)
        name = self.normalize_name(name)
        if self.filter_title and self.title:
            self.title = self.normalize_name(self.title)

        self.reason = "[%s] %70s ***" % (provider, name.decode('utf-8'))

        if self.filter_title:
            if not all(map(lambda match: match in name, re.split(r'\s', self.title))):
                self.reason += " Name mismatch"
                return False

        if self.require_keywords:
            for required in self.require_keywords:
                if not self.included(name, keys=[required]):
                    self.reason += " Missing required keywords"
                    return False

        if not self.included(name, keys=self.quality_allow):
            self.reason += " Missing any required keyword"
            return False

        if self.included(name, keys=self.quality_deny):
            self.reason += " Blocked by keyword"
            return False

        if size and not self.in_size_range(size):
            self.reason += " Size out of range"
            return False

        return True

    def in_size_range(self, size):
        """ Compares size ranges

        Args:
            size (str): File size string, ie. ``1.21 GB``

        Returns:
            bool: ``True`` if file size is within desired range, ``False`` otherwise
        """
        res = False
        value = size_int(clean_number(size))
        min_size = self.min_size * 1e9
        max_size = self.max_size * 1e9
        if min_size <= value <= max_size:
            res = True
        return res

    def normalize_name(self, value):
        """ Method to normalize strings

        Replaces punctuation with spaces, unquotes and unescapes HTML characters.

        Args:
            value (str): File name or directory string to convert

        Returns:
            str: Converted file name or directory string
        """
        # First normalization
        value = normalize_string(value)
        value = unquote(value)
        value = self.unescape(value)
        # Last normalization, because some unicode char could appear from the previous steps
        value = normalize_string(value)
        value = value.lower()

        for p in string.punctuation:
            value = value.replace(p, ' ')

        value = ' '.join(value.split())

        return value

    def included(self, value, keys, strict=False):
        """ Check if the keys are present in the string

        Args:
            value   (str): Name of the torrent to check
            keys   (list): List of strings that must be included in ``value``
            strict (bool): Boolean flag to accept or not partial results

        Returns:
            bool: True if any (or all if ``strict``) keys are included, False otherwise.
        """
        value = ' ' + value + ' '
        if '*' in keys:
            res = True
        else:
            res1 = []
            for key in keys:
                res2 = []
                for item in re.split(r'\s', key):
                    item = item.replace('_', ' ')
                    if strict:
                        item = ' ' + item + ' '
                    if item.upper() in value.upper():
                        res2.append(True)
                    else:
                        res2.append(False)
                res1.append(all(res2))
            res = any(res1)
        return res

    def unescape(self, name):
        """ Unescapes all HTML entities from a string using
            HTMLParser().unescape()

        Args:
            name (str): String to convert

        Returns:
            str: Converted string
        """
        name = name.replace('<![CDATA[', '').replace(']]', '')
        name = HTMLParser().unescape(name.lower())

        return name

    def exception(self, title=None):
        """ Change the title to the standard name in torrent sites

        Args:
            title (str): Title to check

        Returns:
            str: Standard title
        """
        if title:
            title = title.lower()
            title = title.replace('csi crime scene investigation', 'CSI')
            title = title.replace('law and order special victims unit', 'law and order svu')
            title = title.replace('law order special victims unit', 'law and order svu')
            title = title.replace('S H I E L D', 'SHIELD')

        return title


def apply_filters(results_list):
    """ Applies final result de-duplicating, hashing and sorting

    Args:
        results_list (list): Formatted results in any order

    Returns:
        list: Filtered and sorted results
    """
    results_list = cleanup_results(results_list)
    log.debug("Filtered results: %s" % repr(results_list))

    return results_list


def cleanup_results(results_list):
    """ Remove duplicate results, hash results without an info_hash, and sort by seeders

    Args:
        results_list (list): Results to clean-up

    Returns:
        list: De-duplicated, hashed and sorted results
    """
    if len(results_list) == 0:
        return []

    hashes = []
    filtered_list = []
    for result in results_list:
        if not result['seeds']:
            continue

        if not result['uri']:
            if not result['name']:
                continue
            try:
                log.warning('[%s] No URI for %s' % (result['provider'][16:-8], repr(result['name'])))
            except Exception as e:
                import traceback
                log.warning("%s logging failed with: %s" % (result['provider'], repr(e)))
                map(log.debug, traceback.format_exc().split("\n"))
            continue

        hash_ = result['info_hash'].upper()

        if not hash_:
            if result['uri'] and result['uri'].startswith('magnet'):
                hash_ = Magnet(result['uri']).info_hash.upper()
            else:
                hash_ = hashlib.md5(result['uri']).hexdigest()

        try:
            log.debug("[%s] Hash for %s: %s" % (result['provider'][16:-8], repr(result['name']), hash_))
        except Exception as e:
            import traceback
            log.warning("%s logging failed with: %s" % (result['provider'], repr(e)))
            map(log.debug, traceback.format_exc().split("\n"))

        if not any(existing == hash_ for existing in hashes):
            filtered_list.append(result)
            hashes.append(hash_)

    return sorted(filtered_list, key=lambda r: (get_int(r['seeds'])), reverse=True)
