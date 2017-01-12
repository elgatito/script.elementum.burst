# -*- coding: utf-8 -*-

import re
import hashlib
from urllib import unquote
from quasar.provider import log, get_setting
from parser.HTMLParser import HTMLParser
from providers.definitions import definitions
from utils import Magnet, get_int, get_float, normalize_string


class Filtering:
    def __init__(self):
        self.filters = {
            'filter_480p': ['480p'],
            'filter_720p': ['720p'],
            'filter_1080p': ['1080p'],
            'filter_2k': ['2k', '1440p'],
            'filter_4k': ['4k', '2160p'],
            'filter_brrip': ['brrip', 'bdrip', 'bluray'],
            'filter_webdl': ['webdl', 'webrip'],
            'filter_hdrip': ['hdrip'],
            'filter_hdtv': ['hdtv'],
            'filter_dvd': ['_dvd_', 'dvdrip'],
            'filter_dvdscr': ['dvdscr'],
            'filter_screener': ['screener', 'scr'],
            'filter_3d': ['3d'],
            'filter_telesync': ['telesync', '_ts_', '_tc_'],
            'filter_cam': ['cam', 'hdcam'],
            'filter_trailer': ['trailer']
        }
        qualities_allow = []
        qualities_deny = []
        for quality in self.filters:
            if get_setting(quality, bool):
                qualities_allow.extend(self.filters[quality])
            else:
                qualities_deny.extend(self.filters[quality])
        self.quality_allow = qualities_allow
        self.quality_deny = qualities_deny

        self.min_size = get_float(get_setting('min_size'))
        self.max_size = get_float(get_setting('max_size'))
        self.filter_title = False  # TODO ???

        self.queries = ['{title}']
        self.extras = ['']

        self.info = dict(title="", titles=[])
        self.get_data = None
        self.post_data = {}
        self.reason = ''
        self.title = ''
        self.results = []
        self.url = ''

    def use_general(self, provider, payload):
        definition = definitions[provider]
        general_query = definition['general_query'] if definition['general_query'] else ''
        log.debug("General URL: %s%s" % (definition['base_url'], general_query))
        self.info = payload
        self.url = "%s%s" % (definition['base_url'], general_query)
        if definition['general_keywords']:
            self.queries = [definition['general_keywords']]
            self.extras = [definition['general_extra']]

    def use_movie(self, provider, payload):
        definition = definitions[provider]
        movie_query = definition['movie_query'] if definition['movie_query'] else ''
        log.debug("Movies URL: %s%s" % (definition['base_url'], movie_query))
        self.info = payload
        self.url = "%s%s" % (definition['base_url'], movie_query)
        if definition['movie_keywords']:
            self.queries = ["%s" % definition['movie_keywords']]
            self.extras = ["%s" % definition['movie_extra']]
        else:
            self.queries = ['{title} {year}', '{title}']
            self.extras = ['', '']

    def use_episode(self, provider, payload):
        definition = definitions[provider]
        show_query = definition['show_query'] if definition['show_query'] else ''
        log.debug("Episode URL: %s%s" % (definition['base_url'], show_query))
        self.info = payload
        self.url = "%s%s" % (definition['base_url'], show_query)
        if definition['tv_keywords']:
            self.queries = ["%s" % definition['tv_keywords']]
            self.extras = ["%s" % definition['tv_extra'] if definition['tv_extra'] else '']
            # TODO this sucks, tv_keywords should be a list from the start..
            if definition['tv_keywords2']:
                self.queries.append(definition['tv_keywords2'])
                self.queries.append(definition['tv_extra2'] if definition['tv_extra2'] else '')
        else:
            self.queries = ['{title} s{season:2}e{episode:2}']
            self.extras = ['']

    def use_season(self, provider, info):
        definition = definitions[provider]
        season_query = definition['season_query'] if definition['season_query'] else ''
        log.debug("Season URL: %s%s" % (definition['base_url'], season_query))
        self.info = info
        self.url = "%s%s" % (definition['base_url'], season_query)
        if definition['season_keywords1']:
            self.queries = ["%s" % definition['season_keywords1']]
            self.extras = ['']
            if definition['season_keywords2']:
                self.queries.append("%s" % definition['season_keywords2'])
                self.queries.append('')
            if definition['season_keywords3']:
                self.queries.append("%s" % definition['season_keywords3'])
                self.queries.append('')
        # TODO See, told you it sucked
        else:
            self.queries = ['{title} Season_{season}', '{title} Season{season}', '{title} S{season:2}']
            self.extras = ['', '', '']

    def use_anime(self, provider, info):
        definition = definitions[provider]
        anime_query = definition['anime_query'] if definition['anime_query'] else ''
        log.debug("Anime URL: %s%s" % (definition['base_url'], anime_query))
        self.info = info
        self.url = "%s%s" % (definition['base_url'], anime_query)
        if definition['anime_keywords']:
            self.queries = ["%s" % definition['anime_keywords']]
            self.extras = ["%s" % definition['anime_extra'] if definition['anime_extra'] else '']
        else:
            self.queries = ['{title} {episode}']
            self.extras = ['']

    def information(self, provider):
        log.debug('[%s] Accepted keywords: %s' % (provider, self.quality_allow))
        log.debug('[%s] Blocked keywords: %s' % (provider, self.quality_deny))
        log.debug('[%s] Minimum size: %s' % (provider, str(self.min_size) + ' GB'))
        log.debug('[%s] Maximum size: %s' % (provider, str(self.max_size) + ' GB'))

    def verify(self, provider, name, size):
        """
        Check the name matches with the title and the filtering keywords, and the size with filtering size values
        :param name: name of the torrent
        :type name: str
        :param size: size of the torrent
        :type size: str
        :return: True is complied with the filtering.  False, otherwise.
        """
        if name is None or name is '':
            self.reason = '[%s] %s' % (provider, '*** Empty name ***')
            return False

        name = self.exception(name)
        name = self.safe_name(name)
        self.title = self.safe_name(self.title) if self.filter_title else name
        normalized_title = normalize_string(self.title)  # because sometimes there are missing accents in the results

        self.reason = "[%s] %70s ***" % (provider, name.decode('utf-8'))

        list_to_verify = [self.title, normalized_title] if self.title != normalized_title else [self.title]
        if self.included(name, list_to_verify, True):
            result = True
            if name is not None:
                if not self.included(name, self.quality_allow):
                    self.reason += " Missing required tag"
                    result = False
                elif self.included(name, self.quality_deny):
                    self.reason += " Blocked by tag"
                    result = False

            if size is not None and size is not '':
                if not self.size_clearance(size):
                    result = False
                    self.reason += " Size out of range"

        else:
            result = False
            self.reason += " Name mismatch"

        return result

    def size_clearance(self, size):
        """
        Convert string with size format to number ex: 1kb = 1000
        :param size: string with the size format
        :type size: str
        :return: converter value in integer
        """
        max_size1 = 100 if self.max_size == 10 else self.max_size
        res = False
        value = get_float(size)
        value *= 0.001 if 'M' in size else 1
        if self.min_size <= value <= max_size1:
            res = True

        return res

    def safe_name(self, value):
        """
        Make the name directory and filename safe
        :param value: string to convert
        :type value: str
        :return: converted string
        """
        # First normalization
        value = normalize_string(value)
        value = unquote(value)
        value = self.uncode_name(value)
        # Last normalization, because some unicode char could appear from the previous steps
        value = normalize_string(value)
        value = value.lower()
        keys = {'"': ' ', '*': ' ', '/': ' ', ':': ' ', '<': ' ', '>': ' ', '?': ' ', '|': ' ', '_': ' ',
                "'": '', 'Of': 'of', 'De': 'de', '.': ' ', ')': ' ', '(': ' ', '[': ' ', ']': ' ', '-': ' '}
        for key in keys.keys():
            value = value.replace(key, keys[key])

        value = ' '.join(value.split())

        return value

    @staticmethod
    def included(value, keys, strict=False):
        """
        Check if the keys are present in the string
        :param value: string to test
        :type value: str
        :param keys: values to check
        :type keys: list
        :param strict: if it accepts partial results
        :type strict: bool
        :return: True is any key is included. False, otherwise.
        """
        value = ' ' + value + ' '
        if '*' in keys:
            res = True

        else:
            res1 = []
            for key in keys:
                res2 = []
                for item in re.split('\s', key):
                    item = item.replace('?', ' ').replace('_', ' ')
                    if strict:
                        item = ' ' + item + ' '

                    if item.upper() in value.upper():
                        res2.append(True)

                    else:
                        res2.append(False)

                res1.append(all(res2))
            res = any(res1)

        return res

    @staticmethod
    def uncode_name(name):
        """
        Convert all the &# codes to char, remove extra-space and normalize
        :param name: string to convert
        :type name: str
        :return: converted string
        """
        name = name.replace('<![CDATA[', '').replace(']]', '')
        name = HTMLParser().unescape(name.lower())

        return name

    @staticmethod
    def exception(title=None):
        """
        Change the title to the standard name in the torrent sites
        :param title: title to check
        :type title: str
        :return: the new title
        """
        if title:
            title = title.lower()
            title = title.replace('csi crime scene investigation', 'CSI')
            title = title.replace('law and order special victims unit', 'law and order svu')
            title = title.replace('law order special victims unit', 'law and order svu')
            title = title.replace('S H I E L D', 'SHIELD')

        return title


def apply_filters(results_list):
    """
    Filter the results
    :param results_list: values to filter
    :type results_list: list
    :return: list of filtered results
    """
    results_list = cleanup_results(results_list)
    log.debug("Filtered results: %s" % repr(results_list))
    # results_list = sort_by_quality(results_list)
    # log.info("Sorted results: %s" % repr(results_list))

    return results_list


def cleanup_results(results_list):
    """
    Remove dupes and sort by seeds
    :param results_list: values to filter
    :type results_list: list
    :return: list of cleaned results
    """
    if len(results_list) == 0:
        return []

    hashes = []
    filtered_list = []
    for result in results_list:
        if not result['uri']:
            if not result['name']:
                continue
            log.warning('[%s] No URI for %s' % (result['provider'][16:-8], result['name'].decode('ascii', 'ignore')))
            continue

        hash_ = result['info_hash'].upper()

        if not hash_:
            if result['uri'] and result['uri'].startswith('magnet'):
                hash_ = Magnet(result['uri']).info_hash.upper()
            else:
                hash_ = hashlib.md5(result['uri']).hexdigest()

        try:
            log.debug("[%s] Hash for %s: %s" % (result['provider'][16:-8], result['name'].decode('ascii', 'ignore'), hash_))
        except Exception as e:
            import traceback
            log.error("%s failed with: %s" % (result['provider'], repr(e)))
            map(log.debug, traceback.format_exc().split("\n"))

        if not any(existing == hash_ for existing in hashes):
            filtered_list.append(result)
            hashes.append(hash_)

    return sorted(filtered_list, key=lambda r: (get_int(r['seeds'])), reverse=True)


def check_quality(text=""):
    """
    Get the quality values from string
    :param text: string with the name of the file
    :type text: str
    :return:
    """
    text = text.lower()
    quality = "480p"

    if "480p" in text:
        quality = "480p"

    if "720p" in text:
        quality = "720p"

    if "1080p" in text:
        quality = "1080p"

    if "3d" in text:
        quality = "1080p"

    if "4k" in text:
        quality = "2160p"

    return quality


def sort_by_quality(results_list):
    """
    Apply sorting based on seeds and quality
    :param results_list: list of values to be sorted
    :type results_list: list
    :return: list of sorted results
    """
    log.info("Applying quality sorting")
    for result in results_list:
        # hd streams
        quality = check_quality(result['name'])
        if "1080p" in quality:
            result['quality'] = 3
            result['hd'] = 1

        elif "720p" in quality:
            result['quality'] = 2
            result['hd'] = 1

        else:
            result['quality'] = 1
            result['hd'] = 0

    return sorted(results_list, key=lambda r: (r["seeds"], r['hd'], r['quality'], r["peers"]), reverse=True)
