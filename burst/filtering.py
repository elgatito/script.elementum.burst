# -*- coding: utf-8 -*-

"""
Burst filtering class and methods
"""

import hashlib
import re

from elementum.provider import get_setting, log
from normalize import normalize_string, safe_name
from providers.definitions import definitions
from utils import Magnet, clean_number, get_alias, get_float, get_int, size_int

try:
    from collections import OrderedDict

except Exception as e:
    log.debug("using: %s" % repr(e))
    from ordereddict import OrderedDict


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
        info (dict): Payload from Elementum
        kodi_language (str): Language code from Kodi if kodi_language setting is enabled
        language_exceptions (list): List of providers for which not to apply 'kodi_language' setting
        url (str): URL of this filtering request
        get_data (dict): GET data for client request
        post_data (dict): POST data for client request
        title (str): Result title to be used when matching with 'filter_title' enabled
        reason (str): Rejection reason when result does not match
        results (list): Filtered, accepted results
    """

    def __init__(self):
        resolutions = OrderedDict()
        resolutions['filter_240p'] = [u'240р', u'_tvrip_', u'satrip', u'vhsrip']
        resolutions['filter_480p'] = [u'480р', u'xvid', u'dvd', u'dvdrip', u'hdtv']
        resolutions['filter_720p'] = [u'720р', u'hdrip', u'bluray', u'blu_ray', u'brrip', u'bdrip', u'hdtv']
        resolutions['filter_1080p'] = [u'1080р', u'fullhd', u'_fhd_']
        resolutions['filter_2k'] = [u'_2k_', u'1440p']
        resolutions['filter_4k'] = [u'_4k_', u'2160р']
        self.resolutions = resolutions

        self.release_types = {
            'filter_brrip': [u'brrip', u'bdrip', u'bluray'],
            'filter_webdl': [u'webdl', u'webrip', u'web_dl', u'dlrip', u'_yts_'],
            'filter_hdrip': [u'hdrip'],
            'filter_hdtv': [u'hdtv'],
            'filter_dvd': [u'_dvd_', u'dvdrip'],
            'filter_dvdscr': [u'dvdscr'],
            'filter_screener': [u'screener', u'_scr_'],
            'filter_3d': [u'_3d_'],
            'filter_telesync': [u'telesync', u'_ts_', u'_tc_'],
            'filter_cam': [u'_cam_', u'hdcam'],
            'filter_tvrip': [u'_tvrip_', u'satrip'],
            'filter_vhsrip': [u'vhsrip'],
            'filter_trailer': [u'trailer', u'трейлер'],
            'filter_workprint': [u'workprint']
        }

        require = list()
        resolutions_allow = list()
        releases_allow = list()
        releases_deny = list()

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

        if get_setting('use_filter', bool):
            for release_type in self.release_types:
                if get_setting(release_type, bool):
                    releases_allow.extend(self.release_types[release_type])

                else:
                    releases_deny.extend(self.release_types[release_type])

        else:
            releases_allow = [u'*']

        self.releases_allow = releases_allow
        self.releases_deny = releases_deny

        if get_setting('additional_filters', bool):
            accept = get_setting('accept').strip().lower()
            if accept:
                accept = re.split(r',\s?', accept)
                releases_allow.extend(accept)

            block = get_setting('block').strip().lower()
            if block:
                block = re.split(r',\s?', block)
                releases_deny.extend(block)

            require = get_setting('require').strip().lower()
            if require:
                require = re.split(r',\s?', require)

        self.require_keywords = require
        self.min_size = get_float(get_setting('min_size'))
        self.max_size = get_float(get_setting('max_size'))
        self.check_sizes()
        self.filter_title = False
        self.queries = list()
        self.extras = list()

        self.info = dict(title="", titles=dict())
        self.kodi_language = ''
        self.language_exceptions = list()
        self.get_data = dict()
        self.post_data = dict()
        self.url = u''
        self.title = u''
        self.reason = u''
        self.results = list()

    def use_general(self, provider, payload):
        """ 
            Setup method to define general search parameters
        :param provider: Provider ID
        :type provider: str
        :param payload: Elementum search payload
        :type payload: dict
        """
        definition = definitions[provider]
        definition = get_alias(definition, get_setting("%s_alias" % provider))
        if get_setting("use_public_dns", bool) and "public_dns_alias" in definition:
            definition = get_alias(definition, definition["public_dns_alias"])

        general_query = definition['general_query'] if definition['general_query'] else ''
        log.debug(u'General URL: %s%s' % (definition['base_url'], general_query))
        self.info = payload
        self.url = u'%s%s' % (definition['base_url'], general_query)
        if definition['general_keywords']:
            self.queries = [definition['general_keywords']]
            self.extras = [definition['general_extra']]

    def use_movie(self, provider, payload):
        """ 
            Setup method to define movie search parameters
        :param provider: Provider ID
        :type provider: str
        :param payload: Elementum search payload
        :type payload: dict
        """
        definition = definitions[provider]
        definition = get_alias(definition, get_setting("%s_alias" % provider))
        if get_setting("use_public_dns", bool) and "public_dns_alias" in definition:
            definition = get_alias(definition, definition["public_dns_alias"])

        movie_query = definition['movie_query'] if definition['movie_query'] else ''
        log.debug(u'Movies URL: %s%s' % (definition['base_url'], movie_query))
        if get_setting('separate_sizes', bool):
            self.min_size = get_float(get_setting('min_size_movies'))
            self.max_size = get_float(get_setting('max_size_movies'))
            self.check_sizes()

        self.info = payload
        self.url = u'%s%s' % (definition['base_url'], movie_query)
        if definition['movie_keywords']:
            self.queries = [u'%s' % definition['movie_keywords']]
            self.extras = [u'%s' % definition['movie_extra']]

    def use_episode(self, provider, payload):
        """ 
            Setup method to define episode search parameters
        :param provider: Provider ID
        :type provider: str
        :param payload: Elementum search payload
        :type payload: dict
        """
        definition = definitions[provider]
        definition = get_alias(definition, get_setting("%s_alias" % provider))
        if get_setting("use_public_dns", bool) and "public_dns_alias" in definition:
            definition = get_alias(definition, definition["public_dns_alias"])

        show_query = definition['show_query'] if definition['show_query'] else ''
        log.debug(u'Episode URL: %s%s' % (definition['base_url'], show_query))
        if get_setting('separate_sizes', bool):
            self.min_size = get_float(get_setting('min_size_episodes'))
            self.max_size = get_float(get_setting('max_size_episodes'))
            self.check_sizes()

        self.info = payload
        self.url = u"%s%s" % (definition['base_url'], show_query)
        if definition['tv_keywords']:
            self.queries = [u'%s' % definition['tv_keywords']]
            self.extras = [u'%s' % definition['tv_extra'] if definition['tv_extra'] else '']
            # TODO this sucks, tv_keywords should be a list from the start..
            if definition['tv_keywords2']:
                self.queries.append(definition['tv_keywords2'])
                self.extras.append(definition['tv_extra2'] if definition['tv_extra2'] else '')

    def use_season(self, provider, payload):
        """ 
            Setup method to define season search parameters
        :param provider: Provider ID
        :type provider: str
        :param payload: Elementum search payload
        :type payload: dict
        """
        definition = definitions[provider]
        definition = get_alias(definition, get_setting("%s_alias" % provider))
        if get_setting("use_public_dns", bool) and "public_dns_alias" in definition:
            definition = get_alias(definition, definition["public_dns_alias"])

        season_query = definition['season_query'] if definition['season_query'] else ''
        log.debug(u'Season URL: %s%s' % (definition['base_url'], season_query))
        if get_setting('separate_sizes', bool):
            self.min_size = get_float(get_setting('min_size_seasons'))
            self.max_size = get_float(get_setting('max_size_seasons'))
            self.check_sizes()

        self.info = payload
        self.url = u"%s%s" % (definition['base_url'], season_query)

        if definition['season_keywords']:
            self.queries = [u'%s' % definition['season_keywords']]
            self.extras = [u'%s' % definition['season_extra'] if definition['season_extra'] else '']
            if definition['season_keywords2']:
                self.queries.append(u'%s' % definition['season_keywords2'])
                self.extras.append(u'%s' % definition['season_extra2'] if definition['season_extra2'] else '')

    def use_anime(self, provider, payload):
        """ 
            Setup method to define anime search parameters
        :param provider: Provider ID
        :type provider: str
        :param payload: Elementum search payload
        :type payload: dict
        """
        definition = definitions[provider]
        definition = get_alias(definition, get_setting("%s_alias" % provider))
        if get_setting("use_public_dns", bool) and "public_dns_alias" in definition:
            definition = get_alias(definition, definition["public_dns_alias"])

        anime_query = definition['anime_query'] if definition['anime_query'] else ''
        log.debug(u'Anime URL: %s%s' % (definition['base_url'], anime_query))
        if get_setting('separate_sizes', bool):
            self.min_size = get_float(get_setting('min_size_episodes'))
            self.max_size = get_float(get_setting('max_size_episodes'))
            self.check_sizes()

        self.info = payload
        self.url = u'%s%s' % (definition['base_url'], anime_query)
        if self.info['absolute_number']:
            self.info['episode'] = self.info['absolute_number']

        if definition['anime_keywords']:
            self.queries = [u'%s' % definition['anime_keywords']]
            self.extras = [u'%s' % definition['anime_extra'] if definition['anime_extra'] else '']

    def information(self, provider):
        """ 
            Debugging method to print keywords and file sizes
        """
        log.debug(u'[%s] Accepted resolutions: %s' % (provider, self.resolutions_allow))
        log.debug(u'[%s] Accepted release types: %s' % (provider, self.releases_allow))
        log.debug(u'[%s] Blocked release types: %s' % (provider, self.releases_deny))
        log.debug(u'[%s] Minimum size: %s' % (provider, str(self.min_size) + u' GB'))
        log.debug(u'[%s] Maximum size: %s' % (provider, str(self.max_size) + u' GB'))

    def check_sizes(self):
        """ 
            Internal method to make sure size range settings are valid
        """
        if self.min_size > self.max_size:
            log.warning("Minimum size above maximum, using max size minus 1 GB")
            self.min_size = self.max_size - 1

    @staticmethod
    def read_keywords(keywords):
        """
            Create list from keywords where the values are marked between curly brackets, ie. {title}
        :param keywords: String with all the keywords, ie. '{title} {year} movie'
        :type keywords: unicode
        :return: List of keywords, ie. ['{title}', '{year}']
        :rtype: list
        """

        results = list()
        if keywords:
            for value in re.findall('{(.*?)}', keywords):
                results.append(value)

        return results

    def process_keywords(self, provider, text, replacing=False):
        """
            Processes the query payload from a provider's keyword definitions
        :param provider: Provider ID
        :type provider: str
        :param text: Keyword placeholders from definitions, ie. {title}
        :type text: unicode
        :param replacing: Whether is ' is replaced
        :type replacing: bool
        :return: Processed query keywords
        :rtype: unicode
        """
        keywords = self.read_keywords(text)

        for keyword in keywords:
            keyword = keyword.lower()
            if u'title' in keyword:
                title = safe_name(self.info["title"], replacing=replacing)
                language = definitions[provider]['language']
                use_language = None
                if u':' in keyword:
                    use_language = keyword.split(':')[1].lower()
                
                if provider not in self.language_exceptions and \
                        (use_language or self.kodi_language) and \
                        'titles' in self.info and self.info['titles']:
                    try:
                        if self.kodi_language and self.kodi_language in self.info['titles']:
                            use_language = self.kodi_language

                        if use_language not in self.info['titles']:
                            use_language = language
                            if 'original' in self.info['titles']:
                                title = normalize_string(self.info['titles']['original'])

                        if use_language in self.info['titles'] and self.info['titles'][use_language]:
                            title = self.info['titles'][use_language]
                            title = normalize_string(title, replacing=replacing)
                            log.info("[%s] Using translated '%s' title %s" % (provider, use_language,
                                                                              repr(title)))
                            log.debug(
                                "[%s] Translated titles from Elementum: %s" % (provider, repr(self.info['titles'])))

                    except Exception as ex:
                        import traceback
                        log.error("%s failed with: %s" % (provider, repr(ex)))
                        map(log.debug, traceback.format_exc().split("\n"))

                text = text.replace('{%s}' % keyword, title)

            if u'year' in keyword:
                text = text.replace('{%s}' % keyword, str(self.info["year"]))

            if u'season' in keyword:
                if '+' in keyword:
                    keys = keyword.split('+')
                    season = str(self.info["season"] + get_int(keys[1]))
                
                elif ':' in keyword:
                    keys = keyword.split(':')
                    season = ('%%.%sd' % keys[1]) % self.info["season"]
                
                else:
                    season = '%s' % self.info["season"]
                
                text = text.replace('{%s}' % keyword, season)

            if u'episode' in keyword:
                if u'+' in keyword:
                    keys = keyword.split('+')
                    episode = str(self.info["episode"] + get_int(keys[1]))
                
                elif u':' in keyword:
                    keys = keyword.split(':')
                    episode = ('%%.%sd' % keys[1]) % self.info["episode"]
                
                else:
                    episode = '%s' % self.info["episode"]
                
                text = text.replace('{%s}' % keyword, episode)

        return text

    def verify(self, provider, name, size):
        """
            Main filtering method to match torrent names, resolutions, release types and size filters
        :param provider: Provider ID
        :type provider: str
        :param name: Torrent name
        :type name: str
        :param size: Arbitrary torrent size to be parsed
        :type size: str
        :return: 'True' if torrent name passed filtering, 'False' otherwise.
        :rtype: bool
        """
        if not name:
            self.reason = u'[%s] %s' % (provider, u'*** Empty name ***')
            return False

        name = normalize_string(name)
        if self.filter_title and self.title:
            self.title = normalize_string(self.title)

        self.reason = "[%s] %70s ***" % (provider, name)
        if self.filter_resolutions:
            resolution = self.determine_resolution(name)
            if resolution not in self.resolutions_allow:
                self.reason += u" Resolution not allowed"
                return False

        if self.filter_title:
            if not all(map(lambda match: match in name, re.split(r'\s', self.title))):
                self.reason += u" Name mismatch"
                return False

        if self.require_keywords:
            for required in self.require_keywords:
                if not self.included(name, keys=[required]):
                    self.reason += u" Missing required keyword"
                    return False

        if not self.included(name, keys=self.releases_allow):
            self.reason += u" Missing release type keyword"
            return False

        if self.included(name, keys=self.releases_deny):
            self.reason += u" Blocked by release type keyword"
            return False

        if size and not self.in_size_range(size):
            self.reason += u" Size out of range"
            return False

        return True

    def in_size_range(self, size):
        """
            Compares size ranges
        :param size: File size string, ie. '1.21 GB'
        :type size: str or unicode
        :return: 'True' if file size is within desired range, 'False' otherwise
        :rtype: bool
        """
        res = False
        value = size_int(clean_number(size))
        min_size = self.min_size * 1e9
        max_size = self.max_size * 1e9
        if min_size <= value <= max_size:
            res = True

        return res

    def determine_resolution(self, name):
        """
            Determine torrent resolution from defined filters. Defaults to 'filter_480p'.
        :param name:  Name of the torrent to determine the resolution for
        :type name: unicode
        :return:  The filter key of the determined resolution, see self.resolutions
        :rtype: str
        """

        res = 'filter_480p'  # Default to 480p
        for resolution in self.resolutions:
            if self.included(name, keys=self.resolutions[resolution], strict=True):
                res = resolution

        return res

    @staticmethod
    def included(value, keys, strict=False):
        """
            Check if the keys are present in the string
        :param value:  Name of the torrent to check
        :type value: unicode
        :param keys: List of strings that must be included in 'value'
        :type keys: list
        :param strict: Boolean flag to accept or not partial results
        :type strict: bool
        :return: True if any (or all if 'strict') keys are included, False otherwise.
        :rtype: bool
        """

        value = u' ' + value.lower() + u' '
        if u'*' in keys:
            res = True

        else:
            res1 = list()
            for key in keys:
                res2 = list()
                for item in re.split(r'\s', key):
                    item = item.replace(u'_', u' ')
                    if strict:
                        item = u' ' + item + u' '

                    if item in value:
                        res2.append(True)

                    else:
                        res2.append(False)

                res1.append(all(res2))

            res = any(res1)

        return res


def apply_filters(results_list):
    """
        Applies final result de-duplicating, hashing and sorting
    :param results_list: Formatted results in any order
    :type results_list: list
    :return: Filtered and sorted results
    :rtype: list
    """
    results_list = cleanup_results(results_list)
    log.debug("Filtered results: %s" % repr(results_list))

    return results_list


def cleanup_results(results_list):
    """
        Remove duplicate results, hash results without an info_hash, and sort by seeders
    :param results_list: Results to clean-up
    :type results_list: list
    :return: De-duplicated, hashed and sorted results
    :rtype: list
    """
    if len(results_list) == 0:
        return list()

    hashes = list()
    filtered_list = list()
    allow_noseeds = get_setting('allow_noseeds', bool)
    for result in results_list:
        if not result['seeds'] and not allow_noseeds:
            continue

        if not result['uri']:
            if not result['name']:
                continue

            try:
                log.warning('[%s] No URI for %s' % (result['provider'][16:-8], repr(result['name'])))

            except Exception as ex:
                import traceback
                log.warning("%s logging failed with: %s" % (result['provider'], repr(ex)))
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

        except Exception as ex:
            import traceback
            log.warning("%s logging failed with: %s" % (result['provider'], repr(ex)))
            map(log.debug, traceback.format_exc().split("\n"))

        if not any(existing == hash_ for existing in hashes):
            filtered_list.append(result)
            hashes.append(hash_)

    return sorted(filtered_list, key=lambda r: (get_int(r['seeds'])), reverse=True)
