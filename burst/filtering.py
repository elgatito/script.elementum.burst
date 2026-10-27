# -*- coding: utf-8 -*-

"""
Burst filtering class and methods
"""

from __future__ import unicode_literals
from future.utils import PY3

import re
import hashlib
import traceback
from elementum.provider import log, get_setting
from .normalize import normalize_string, remove_accents
from .providers.definitions import definitions
from .utils import Magnet, get_int, get_float, clean_number, size_int, get_alias, use_opennic_dns
from collections import OrderedDict
if PY3:
    unicode = str

from kodi_six.utils import py2_encode

use_require_resolution = get_setting('require_resolution', bool)
use_additional_filters = get_setting('additional_filters', bool)
use_require_keywords = get_setting('require_keywords', bool)
use_require_release_type = get_setting('require_release_type', bool)
use_require_size = get_setting('require_size', bool)
use_accept = get_setting('accept', unicode).strip().lower()
use_block = get_setting('block', unicode).strip().lower()
use_require = get_setting('require', unicode).strip().lower()
use_min_size = get_setting('min_size')
use_max_size = get_setting('max_size')
use_filter_quotes = get_setting("filter_quotes", bool)
use_allow_noseeds = get_setting('allow_noseeds', bool)
overwrite_anime_original_title = get_setting('overwrite_anime_original_title', choices=('original', 'jp', 'en'))
keys_rx = {}

class Filtering:
    """
    Filtering class

    Attributes:
        resolutions (OrderedDict): Ordered dictionary of resolution filters to be used depending on settings
        resolutions_allow  (list): List of resolutions to allow in search results
        release_types  (dict): Dictionary of release types to be used depending on settings
        releases_allow (list): List of release types to allow in search results
        releases_deny  (list): List of release types to deny in search results
        require_keywords (list): List of keywords to require in search results
        min_size (float): Minimum required size
        max_size (float): Maximum possible size
        filter_title (bool): Whether or not this provider needs titles to be double-checked,
            typically used for providers that return too many results from their search
            engine when no results are found (ie. TorLock and TorrentZ)
        queries (list): List of queries to be filtered
        extras (list): List of extras to be filtered
        queries_priorities (list): Priorities of the queries
        info (dict): Payload from Elementum
        kodi_language (str): Language code from Kodi if kodi_language setting is enabled
        language_exceptions (list): List of providers for which not to apply ``kodi_language`` setting
        url (str): URL of this filtering request
        get_data (dict): GET data for client request
        post_data (dict): POST data for client request
        title (str): Result title to be used when matching with ``filter_title`` enabled
        reason (str): Rejection reason when result does not match
        results (list): Filtered, accepted results
    """
    def __init__(self):
        resolutions = OrderedDict()
        resolutions['filter_240p'] = ['240[pр]', r'vhs\-?rip']
        resolutions['filter_480p'] = ['480[pр]', r'xvid|dvd|dvdrip|hdtv|web\-(dl)?rip|iptv|sat\-?rip|tv\-?rip']
        resolutions['filter_720p'] = ['720[pр]|1280x720', r'hd720p?|hd\-?rip|b[rd]rip']
        resolutions['filter_1080p'] = ['1080[piр]|1920x1080', r'hd1080p?|fullhd|fhd|blu\W*ray|bd\W*remux']
        resolutions['filter_2k'] = ['1440[pр]', '2k']
        resolutions['filter_4k'] = ['4k|2160[pр]|uhd', '4k|hd4k']
        resolutions['filter_music'] = [r'mp3|flac|alac|ost|sound\-?track']
        self.resolutions = resolutions

        self.release_types = {
            'filter_brrip': [r'brrip|bd\-?rip|blu\-?ray|bd\-?remux'],
            'filter_webdl': [r'web_?\-?dl|web\-?rip|dl\-?rip|yts'],
            'filter_hdrip': [r'hd\-?rip'],
            'filter_hdtv': [r'hd\-?tv'],
            'filter_dvd': [r'dvd|dvd\-?rip|vcd\-?rip'],
            'filter_dvdscr': [r'dvd\-?scr'],
            'filter_screener': ['screener|scr'],
            'filter_3d': ['3d'],
            'filter_telesync': ['telesync|ts|telecine|tc|hdts'],
            'filter_cam': [r'cam|cam\-?rip|hd\-?cam'],
            'filter_tvrip': [r'tv\-?rip|sat\-?rip|dvb'],
            'filter_iptvrip': [r'iptv\-?rip'],
            'filter_vhsrip': [r'vhs\-?rip'],
            'filter_trailer': ['trailer|трейлер|тизер'],
            'filter_workprint': ['workprint'],
            'filter_line': ['line']
        }

        require = []
        resolutions_allow = []
        releases_allow = []
        releases_deny = []

        for resolution in self.resolutions:
            if get_setting(resolution, bool):
                resolutions_allow.append(resolution)
                # Add enabled resolutions to allowed release types to match
                # previous versions' behavior with certain providers
                # with no release types in torrent names, ie. YTS
                releases_allow.extend(self.resolutions[resolution])
        self.resolutions_allow = resolutions_allow

        # Skip resolution filtering if we're allowing all of them anyway
        self.filter_resolutions = True
        if len(self.resolutions_allow) == len(self.resolutions):
            self.filter_resolutions = False

        for release_type in self.release_types:
            if get_setting(release_type, bool):
                releases_allow.extend(self.release_types[release_type])
            else:
                releases_deny.extend(self.release_types[release_type])

        if use_additional_filters:
            accept = use_accept
            if accept:
                accept = re.split(r',\s?', accept)
                releases_allow.extend(accept)

            block = use_block
            if block:
                block = re.split(r',\s?', block)
                releases_deny.extend(block)

            require = use_require
            if require:
                require = re.split(r',\s?', require)

        self.releases_allow = releases_allow
        self.releases_deny = releases_deny

        self.require_keywords = require

        self.min_size = get_float(use_min_size)
        self.max_size = get_float(use_max_size)
        self.check_sizes()

        self.filter_title = False

        self.queries = []
        self.extras = []
        self.queries_priorities = []

        self.info = dict(title="", proxy_url="", internal_proxy_url="", elementum_url="", titles=[])
        self.kodi_language = ''
        self.language_exceptions = []
        self.provider_languages = []
        self.get_data = {}
        self.post_data = {}
        self.url = ''
        self.title = ''
        self.reason = ''
        self.results = []

    def _setup(self, provider, payload, query_key, sizes=None):
        """ Common setup for search methods: resolves domain aliases, size limits and search URL

        Args:
            provider  (str): Provider ID
            payload  (dict): Elementum search payload
            query_key (str): Definition key with the URL query suffix, ie. ``movie_query``
            sizes     (str): Suffix of ``min_size_*``/``max_size_*`` settings to use with ``separate_sizes``

        Returns:
            dict: Provider definition with aliases applied
        """
        # Domain name preferred order:
        # root_url -> base_url (see update_definitions()) -> opennic_dns_alias OR tor_dns_alias -> user defined alias
        definition = definitions[provider]
        if use_opennic_dns() and "opennic_dns_alias" in definition:
            definition = get_alias(definition, definition["opennic_dns_alias"])
        if get_setting("use_tor_dns", bool) and "tor_dns_alias" in definition:
            definition = get_alias(definition, definition["tor_dns_alias"])
        definition = get_alias(definition, get_setting("%s_alias" % provider))

        query = definition.get(query_key) or ''
        log.debug("[%s] %s URL: %s%s" % (provider, query_key, definition['base_url'], query))
        if sizes and get_setting('separate_sizes', bool):
            self.min_size = get_float(get_setting('min_size_%s' % sizes))
            self.max_size = get_float(get_setting('max_size_%s' % sizes))
            self.check_sizes()
        self.info = payload
        self.url = u"%s%s" % (definition['base_url'], query)
        return definition

    def use_general(self, provider, payload):
        """ Setup method to define general search parameters """
        self.collect_queries('general', self._setup(provider, payload, 'general_query'))

    def use_movie(self, provider, payload):
        """ Setup method to define movie search parameters """
        self.collect_queries('movie', self._setup(provider, payload, 'movie_query', 'movies'))

    def use_episode(self, provider, payload):
        """ Setup method to define episode search parameters """
        self.collect_queries('tv', self._setup(provider, payload, 'show_query', 'episodes'))

    def use_season(self, provider, payload):
        """ Setup method to define season search parameters """
        self.collect_queries('season', self._setup(provider, payload, 'season_query', 'seasons'))

    def use_anime(self, provider, payload):
        """ Setup method to define anime search parameters """
        definition = self._setup(provider, payload, 'anime_query', 'episodes')
        # Overwrite anime's original title if needed
        global overwrite_anime_original_title
        if 'titles' in self.info and self.info['titles']:
            if overwrite_anime_original_title == 'jp' or overwrite_anime_original_title == '1':
                if 'jp' in self.info['titles'] and self.info['titles']['jp']:
                    self.info['titles']['original'] = self.info['titles']['jp']
                else:
                    overwrite_anime_original_title = 'en'  # fallback to English if Romaji is not available
            if overwrite_anime_original_title == 'en' or overwrite_anime_original_title == '2':
                if 'en' in self.info['titles'] and self.info['titles']['en']:
                    self.info['titles']['original'] = self.info['titles']['en']

        self.collect_queries('anime', definition)

    def split_title_per_languages(self, text, item_type):
        """ Split {title:lang1:lang2:...} into separate queries {title:lang1}, {title:lang2} and so on
        """
        result = []
        modified = False

        keywords = self.read_keywords(text)

        for keyword in keywords:
            keyword = keyword.lower()
            if 'title' in keyword and ':' in keyword:
                # For general queries we should not process language settings.
                if item_type == 'general':
                    result.append(text.replace("{%s}" % keyword, "{title}"))
                    return result

                langs = keyword.lower().split(':')[1:]
                modified = True
                for lang in langs:
                    result.append(text.replace("{%s}" % keyword, "{title:%s}" % lang))
                result.append(text.replace("{%s}" % keyword, "{title}"))  # {title} used for kodi_language or provider_language, if they are set

        if not modified:
            return [text]
        else:
            return result

    def different_years(self):
        """ Checks whether there are different years defined in release dates

        Returns:
            str: Dictionary of country/year.
        """
        if 'year' not in self.info or 'years' not in self.info:
            return {}

        self.info['years']['default'] = self.info['year']

        res = {}
        seen = set()
        for key in self.info['years']:
            if self.info['years'][key] in seen:
                continue
            seen.add(self.info['years'][key])
            res[key] = self.info['years'][key]

        return res

    def split_title_per_year(self, queries, years):
        res = []
        for item in queries:
            if "{year}" in item:
                for key in years:
                    query = item.replace("{year}", "{year:%s}" % (key))
                    res.append(query)
            else:
                res.append(item)

        return res

    def collect_queries(self, item_type, definition):
        different_years = self.different_years()

        # Collecting keywords
        priority = 1
        for item in ['', '2', '3', '4']:
            key = item_type + '_keywords' + item
            extra = item_type + '_extra' + item
            if key in definition and definition[key]:
                qlist = self.split_title_per_languages(definition[key], item_type)
                if len(different_years) > 1:
                    qlist = self.split_title_per_year(qlist, different_years)
                self.queries.extend(qlist)
                eitem = definition[extra] if extra in definition and definition[extra] else ''
                for _ in qlist:
                    self.extras.append(eitem)
                    self.queries_priorities.append(priority)

        # Collecting fallback keywords, they will come in play if having no results at all
        for item in ['', '2', '3', '4']:
            key = item_type + '_keywords_fallback' + item
            extra = item_type + '_extra_fallback' + item
            if key in definition and definition[key]:
                qlist = self.split_title_per_languages(definition[key], item_type)
                if len(different_years) > 1:
                    qlist = self.split_title_per_year(qlist, different_years)
                self.queries.extend(qlist)
                eitem = definition[extra] if extra in definition and definition[extra] else ''
                for _ in qlist:
                    priority += 1
                    self.extras.append(eitem)
                    self.queries_priorities.append(priority)

    def information(self, provider):
        """ Debugging method to print keywords and file sizes
        """
        log.debug('[%s] Accepted resolutions: %s' % (provider, self.resolutions_allow))
        log.debug('[%s] Accepted release types: %s' % (provider, self.releases_allow))
        log.debug('[%s] Blocked release types: %s' % (provider, self.releases_deny))
        log.debug('[%s] Minimum size: %s' % (provider, str(self.min_size) + ' GB'))
        log.debug('[%s] Maximum size: %s' % (provider, str(self.max_size) + ' GB'))

    def check_sizes(self):
        """ Internal method to make sure size range settings are valid
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

    def process_keywords(self, provider, text, definition):
        """ Processes the query payload from a provider's keyword definitions

        Args:
            provider (str): Provider ID
            text     (str): Keyword placeholders from definitions, ie. {title}

        Returns:
            str: Processed query keywords
        """
        keywords = self.read_keywords(text)
        replacing = use_filter_quotes

        for keyword in keywords:
            keyword = keyword.lower()
            if 'title' in keyword:
                title = self.info['title']
                provider_language = definitions[provider]['language']
                use_language = None
                if ':' in keyword:
                    use_language = keyword.split(':')[1].lower()
                if (use_language or self.kodi_language or provider_language) and 'titles' in self.info and self.info['titles']:
                    try:
                        # kodi_language used only for bare {title} and only if tracker not in language_exceptions
                        if not use_language and self.kodi_language and self.kodi_language in self.info['titles'] and provider not in self.language_exceptions:
                            log.info("[%s] Using kodi_language '%s' title" % (provider, self.kodi_language))
                            use_language = self.kodi_language
                        # otherwise use provider_language for {title}
                        if not use_language and provider_language and provider_language in self.info['titles']:
                            log.info("[%s] Using provider_language '%s' title" % (provider, provider_language))
                            use_language = provider_language
                        if use_language not in self.info['titles'] or not self.info['titles'][use_language]:
                            log.info("[%s] Falling back to 'original' title in absence of '%s' language title" % (provider, use_language))
                            use_language = "original"

                        if use_language in self.info['titles'] and self.info['titles'][use_language]:
                            title = self.info['titles'][use_language]
                            title = normalize_string(title)
                            # For all non-original titles, that are not base languages of a tracker OR english language, try to remove accents from the title.
                            if use_language != 'original' and (self.convert_language(use_language) not in self.provider_languages or self.convert_language(use_language) == 'en'):
                                title = remove_accents(title)
                            # Remove characters, filled in 'remove_special_characters' field definition.
                            if 'remove_special_characters' in definition and definition['remove_special_characters']:
                                for char in definition['remove_special_characters']:
                                    title = title.replace(char, "")
                                title = " ".join(title.split())

                            log.info("[%s] Using translated '%s' title %s" % (provider, use_language,
                                                                              repr(title)))
                        else:
                            log.debug("[%s] Skipping the query '%s' due to missing '%s' language title" % (provider, text, use_language))
                            # If title for specific language cannot be read - cancel this query
                            return ""
                    except Exception as e:
                        log.error("%s failed with: %s" % (provider, repr(e)))
                        log.debug(traceback.format_exc())
                else:
                    log.debug("[%s] Not using any translation" % provider)
                text = text.replace('{%s}' % keyword, title)

            if 'year' in keyword:
                if ':' not in keyword:
                    text = text.replace('{%s}' % keyword, str(self.info["year"]))
                else:
                    use_language = keyword.split(':')[1].lower()
                    if use_language in self.info['years'] and self.info['years'][use_language]:
                        text = text.replace('{%s}' % keyword, str(self.info['years'][use_language]))

            if 'show_tmdb_id' in keyword:
                if 'show_tmdb_id' not in self.info:
                    self.info['show_tmdb_id'] = ''

                text = text.replace('{%s}' % keyword, str(self.info["show_tmdb_id"]))

            if 'tmdb_id' in keyword:
                if 'tmdb_id' not in self.info:
                    self.info['tmdb_id'] = ''

                text = text.replace('{%s}' % keyword, str(self.info["tmdb_id"]))

            if 'tvdb_id' in keyword:
                if 'tvdb_id' not in self.info:
                    self.info['tvdb_id'] = ''

                text = text.replace('{%s}' % keyword, str(self.info["tvdb_id"]))

            if 'imdb_id' in keyword:
                if 'imdb_id' not in self.info:
                    self.info['imdb_id'] = ''

                text = text.replace('{%s}' % keyword, str(self.info["imdb_id"]))

            if 'season' in keyword:
                if '+' in keyword:
                    keys = keyword.split('+')
                    season = str(self.info["season"] + get_int(keys[1]))
                elif ':' in keyword:
                    keys = keyword.split(':')
                    season = ('%%.%sd' % keys[1]) % self.info["season"]
                else:
                    season = '%s' % self.info["season"]
                text = text.replace('{%s}' % keyword, season)

            if 'episode' in keyword and 'absolute' not in keyword:
                if '+' in keyword:
                    keys = keyword.split('+')
                    episode = str(self.info["episode"] + get_int(keys[1]))
                elif ':' in keyword:
                    keys = keyword.split(':')
                    episode = ('%%.%sd' % keys[1]) % self.info["episode"]
                else:
                    episode = '%s' % self.info["episode"]
                text = text.replace('{%s}' % keyword, episode)

            if 'absolute_episode' in keyword:
                if 'absolute_number' not in self.info or not self.info['absolute_number']:
                    log.debug("Skipping query '%s' due to missing absolute_number" % text)
                    return ""
                if '+' in keyword:
                    keys = keyword.split('+')
                    episode = str(self.info["absolute_number"] + get_int(keys[1]))
                elif ':' in keyword:
                    keys = keyword.split(':')
                    episode = ('%%.%sd' % keys[1]) % self.info["absolute_number"]
                else:
                    episode = '%s' % self.info["absolute_number"]
                text = text.replace('{%s}' % keyword, episode)

        if replacing:
            text = text.replace(u"'", '')

        return text

    def verify(self, provider, name, size):
        """ Main filtering method to match torrent names, resolutions, release types and size filters

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

        name = normalize_string(name)

        self.reason = "[%s] %70s ***" % (provider, name)

        if self.filter_resolutions and use_require_resolution:
            resolution = self.determine_resolution(name)[0]
            if resolution not in self.resolutions_allow:
                self.reason += " Resolution not allowed ({0})".format(resolution)
                return False

        if self.filter_title:
            if not all(map(lambda match: match in name, re.split(r'\s', self.title))):
                self.reason += " Name mismatch"
                return False

        if self.require_keywords and use_require_keywords:
            for required in self.require_keywords:
                if not self.included_rx(name, keys=[required]):
                    self.reason += " Missing required keyword"
                    return False

        if not self.included_rx(name, keys=self.releases_allow) and use_require_release_type:
            self.reason += " Missing release type keyword"
            return False

        if self.included_rx(name, keys=self.releases_deny) and use_require_release_type:
            self.reason += " Blocked by release type keyword"
            return False

        if size and not self.in_size_range(size) and use_require_size:
            self.reason += " Size out of range ({0})".format(size)
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

    def determine_resolution(self, name):
        """ Determine torrent resolution from defined filters. Defaults to ``filter_480p``.

        Args:
            name (str): Name of the torrent to determine the resolution for

        Returns:
            str: The filter key of the determined resolution, see self.resolutions
        """
        idx = 0
        count = -1
        res = 'filter_480p'  # Default to 480p
        for resolution in self.resolutions:
            count += 1
            if self.included_rx(name, keys=self.resolutions[resolution]):
                idx = count
                res = resolution
        return res, idx

    def included_rx(self, value, keys):
        """ Check if the keys are matched in the string

        Args:
            value   (str): Name of the torrent to check
            keys   (list): List of regex that must be found in ``value``

        Returns:
            bool: True if any of keys is included, False otherwise.
        """
        if not keys:
            return False
        # One combined regex for all keys, compiled once for each list of keys
        cache_key = tuple(keys)
        rx = keys_rx.get(cache_key)
        if rx is None:
            rx = keys_rx[cache_key] = re.compile(r'\W+(' + '|'.join('(?:%s)' % key for key in keys) + r')\W+')
        return bool(rx.search(' ' + value.lower() + ' '))

    def add_provider_language(self, language):
        if language not in self.provider_languages:
            self.provider_languages.append(language)

    def convert_language(self, language):
        if language == 'ru' or language == 'ua' or language == 'by':
            return 'cr'
        else:
            return language

    def define_languages(self, provider):
        definition = definitions[provider]
        if 'language' in definition and definition['language']:
            self.add_provider_language(self.convert_language(definition['language']))
        if 'languages' in definition and definition['languages']:
            for lang in definition['languages'].split(","):
                self.add_provider_language(self.convert_language(lang))

def apply_filters(results_list):
    """ Applies final result de-duplicating, hashing and sorting

    Args:
        results_list (list): Formatted results in any order

    Returns:
        list: Filtered and sorted results
    """
    results_list = cleanup_results(results_list)

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

    hashes = set()
    filtered_list = []
    for result in results_list:
        if not result['seeds'] and not use_allow_noseeds:
            log.debug('[%s] Skipping due to no seeds: %s' % (result['provider'][16:-8], repr(result['name'])))
            continue

        if not result['uri']:
            log.debug('[%s] Skipping due to empty uri: %s' % (result['provider'][16:-8], repr(result)))
            continue

        hash_ = (result['info_hash'] or '').upper()

        if not hash_:
            try:
                if result['uri'] and result['uri'].startswith('magnet'):
                    hash_ = Magnet(result['uri']).info_hash.upper()
                else:
                    hash_ = py2_encode(result['uri'].split("|")[0])
                    try:
                        hash_ = hash_.encode()
                    except:
                        pass
                    hash_ = hashlib.md5(hash_).hexdigest()
            except:
                pass

        # Make sure all are upper-case and provider-scoped
        hash_ = result['provider'] + hash_.upper()

        if hash_ not in hashes:
            filtered_list.append(result)
            hashes.add(hash_)
        else:
            log.debug('[%s] Skipping due to repeating hash: %s' % (result['provider'][16:-8], repr(result)))

    return sorted(filtered_list, key=lambda r: (get_int(r['seeds'])), reverse=True)
