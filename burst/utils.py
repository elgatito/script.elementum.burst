# -*- coding: utf-8 -*-

"""
Burst utilities
"""

import os
import re
import xbmc
import xbmcaddon
import xbmcgui
from urlparse import urlparse

from elementum.provider import get_setting
from providers.definitions import definitions

ADDON = xbmcaddon.Addon()
ADDON_ID = ADDON.getAddonInfo("id")
ADDON_NAME = ADDON.getAddonInfo("name")
ADDON_PATH = ADDON.getAddonInfo("path").decode('utf-8')
ADDON_ICON = ADDON.getAddonInfo("icon").decode('utf-8')
ADDON_PROFILE = ADDON.getAddonInfo("profile")
ADDON_VERSION = ADDON.getAddonInfo("version")
PATH_ADDONS = xbmc.translatePath("special://home/addons/")
PATH_TEMP = xbmc.translatePath("special://temp")
if not ADDON_PATH:
    ADDON_PATH = '..'


class Magnet:
    """ Magnet link parsing class

    Args:
        magnet (str): A magnet link string

    Attributes:
        info_hash (str): Info-hash from the magnet link
        name      (str): Name of torrent
        trackers (list): List of trackers in magnet link
    """

    def __init__(self, magnet):
        self.magnet = magnet + '&'
        info_hash = re.search('urn:btih:(\w+)&', self.magnet, re.IGNORECASE)
        self.info_hash = None
        if info_hash:
            self.info_hash = info_hash.group(1)

        name = re.search('dn=(.*?)&', self.magnet)
        self.name = None
        if name:
            self.name = name.group(1).replace('+', ' ').title()

        self.trackers = re.findall('tr=(.*?)&', self.magnet)


def get_domain(url):
    """
        Get domain from url
    :param url: url
    :type url: str or unicode
    :return: domain
    :rtype: str
    """
    if "//" not in url:
        url = "http://" + url

    parsed_uri = urlparse(url)
    domain = '{uri.netloc}'.format(uri=parsed_uri)
    return domain


def get_protocol(url):
    """
        Get protocol from url
    :param url: url
    :type url: str or unicode
    :return: protocol
    :rtype: str or None
    """
    if "https://" in url:
        return "https"

    elif "http://" in url:
        return "http"

    return None


def get_alias(definition, alias):
    """
        Read the URL alias to replace it
    :param definition: definitions for the provider
    :type definition: dict
    :param alias: new URL
    :type alias: str
    :return: new definition
    :rtype: dict
    """
    definition["alias"] = ""

    if alias:
        old_domain = ""
        for k in ["root_url", "base_url"]:
            domain = get_domain(definition[k])
            if domain:
                old_domain = domain
                break

        new_domain = get_domain(alias)
        protocol = get_protocol(alias)
        if old_domain and new_domain:
            definition["alias"] = new_domain
            definition["old_domain"] = old_domain
            # Substitute all ocurrences of old domain name and replace with new one
            for k in definition:
                if isinstance(definition[k], basestring):
                    definition[k] = definition[k].replace(old_domain, new_domain)
                    if protocol:
                        definition[k] = definition[k].replace("http://", protocol + "://")
                        definition[k] = definition[k].replace("https://", protocol + "://")

            for k in definition["parser"]:
                if isinstance(definition["parser"][k], basestring):
                    definition["parser"][k] = definition["parser"][k].replace(old_domain, new_domain)
                    if protocol:
                        definition["parser"][k] = definition["parser"][k].replace("http://", protocol + "://")
                        definition["parser"][k] = definition["parser"][k].replace("https://", protocol + "://")

    return definition


def get_providers():
    """
        Utility method to get all provider IDs available in the definitions
    :return: All available provider IDs
    :rtype: list
    """
    results = []
    for provider in definitions:
        results.append(provider)
    return results


def get_enabled_providers(method):
    """
        Utility method to get all enabled provider IDs
    :param method:
    :type method: str
    :return: All available enabled provider IDs
    :rtype: list
    """
    results = []
    type_number = "2"
    if method == "general":
        type_number = "0"
    elif method == "movie":
        type_number = "1"
    for provider in definitions:
        if get_setting('use_%s' % provider, bool):
            contains = get_setting('%s_contains' % provider, choices=('All', 'Movies', 'Shows'))
            if not contains or contains == "0":
                results.append(provider)
            elif contains == type_number:
                results.append(provider)
        if 'custom' in definitions[provider] and definitions[provider]['custom']:
            results.append(provider)
    return results


def get_icon_path():
    """
        Utility method to Burst's icon path
    :return: path
    :rtype: str
    """
    return os.path.join(ADDON_PATH, 'icon.png')


def translation(id_value):
    """
    Utility method to get translations
    :param id_value: Code of translation to get
    :type id_value: int
    :return: Translated string
    :rtype: str
    """
    return ADDON.getLocalizedString(id_value)


def get_int(text):
    """
        Convert string to integer number
    :param text: string to convert
    :type text: str or unicode
    :return: converted string in integer
    ;:rtype: int
    """
    return int(get_float(text))


def get_float(string):
    """
        Convert string to float number
    :param string: string to convert
    :type string: str or unicode
    :return: converted string in float
    :rtype: float
    """
    value = 0
    if isinstance(string, (float, long, int)):
        value = float(string)

    elif isinstance(string, str) or isinstance(string, unicode):
        # noinspection PEP8, PyBroadException
        try:
            string = clean_number(string)
            match = re.search('([0-9]*\.[0-9]+|[0-9]+)', string)
            if match:
                value = float(match.group(0))

        except Exception as e:
            repr(e)
            value = 0

    return value


def size_int(string):
    """
        Convert string with size format to integer
    :param string: string to be converted
    :type string: unicode
    :return: converted string in integer
    :rtype: int
    """
    try:
        return int(string)

    except Exception as e:
        repr(e)
        string = string.upper()
        number = string.replace(u'B', u'').replace(u'I', u'').replace(u'K', u'').replace(u'M', u''). \
            replace(u'G', '').replace(u'T', '')
        size = get_float(number)
        if u'K' in string:
            size *= 1000

        if u'M' in string:
            size *= 1000000

        if u'G' in string:
            size *= 1e9

        if u'T' in string:
            size *= 1e12

        return size


def clean_number(string):
    """
        Convert string with a number to USA decimal format
    :param string: string with the number
    :type string: unicode
    :return: converted number in string
    :rtype: unicode
    """
    comma = string.find(u',')
    point = string.find(u'.')
    if comma > 0 and point > 0:
        if comma < point:
            string = string.replace(u',', u'')

        else:
            string = string.replace(u'.', u'')
            string = string.replace(u',', u'.')

    return string


def clean_size(string):
    """
        Utility method to remove unnecessary information from a file size string, eg. '6.5 GBytes' -> '6.5 GB'
    :param string: File size string to clean up
    :type string: unicode
    :return: Cleaned up file size
    :rtype: unicode
    """
    if string:
        pos = string.rfind(u'B')
        if pos > 0:
            string = string[:pos] + u'B'

    return string


def sizeof(num, suffix='B'):
    """
        Utility method to convert a file size in bytes to a human-readable format
    :param num: Number of bytes
    :type num: int
    :param suffix: Suffix for 'bytes'
    :type suffix: unicode
    :return: The formatted file size as a string, eg. ``1.21 GB``
    :rtype: unicode
    """
    for unit in [u'', u'K', u'M', u'G', u'T', u'P', u'E', u'Z']:
        if abs(num) < 1024.0:
            return u"%3.1f %s%s" % (num, unit, suffix)

        num /= 1024.0

    return u"%.1f %s%s" % (num, u'Y', suffix)


def notify(message, image=None):
    """
        Create notification dialog
    :param message: message to notify
    :type message: str or unicode
    :param image: path of the image
    :type image: str
    """
    dialog = xbmcgui.Dialog()
    dialog.notification(ADDON_NAME, message, icon=image)
    del dialog


def clear_cache():
    """
        Clears cookies from Burst's cache
    """
    cookies_path = os.path.join(xbmc.translatePath("special://temp"), "burst")
    if os.path.isdir(cookies_path):
        for f in os.listdir(cookies_path):
            if re.search('.jar', f):
                os.remove(os.path.join(cookies_path, f))


def encode_dict(dict_in):
    """
        Encodes dict values to UTF-8
    :param dict_in: Input dictionary with unicode values
    :type dict_in: dict
    :return:  Output dictionary with UTF-8 encoded values
    :rtype: dict
    """
    dict_out = {}
    for k, v in dict_in.iteritems():
        if isinstance(v, unicode):
            v = v.encode('utf8')

        elif isinstance(v, str):
            v.decode('utf8')

        dict_out[k] = v

    return dict_out
