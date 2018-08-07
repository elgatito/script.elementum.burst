# -*- coding: utf-8 -*-

"""
Burst utilities
"""

import os
import re
import xbmc
import xbmcgui
import xbmcaddon
from elementum.provider import get_setting
from providers.definitions import definitions
from urlparse import urlparse

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
    if "//" not in url:
        url = "http://" + url

    parsed_uri = urlparse(url)
    domain = '{uri.netloc}'.format(uri=parsed_uri)
    return domain


def get_protocol(url):
    if "https://" in url:
        return "https"
    elif "http://" in url:
        return "http"

    return None


def get_alias(definition, alias):
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
    """ Utility method to get all provider IDs available in the definitions

    Returns:
        list: All available provider IDs
    """
    results = []
    for provider in definitions:
        results.append(provider)
    return results


def get_enabled_providers(method):
    """ Utility method to get all enabled provider IDs

    Returns:
        list: All available enabled provider IDs
    """
    results = []
    type = "2"
    if method == "general":
        type = "0"
    elif method == "movie":
        type = "1"
    for provider in definitions:
        if 'enabled' in definitions[provider] and not definitions[provider]['enabled']:
            continue

        if get_setting('use_%s' % provider, bool):
            contains = get_setting('%s_contains' % provider, choices=('All', 'Movies', 'Shows'))
            if not contains or contains == "0":
                results.append(provider)
            elif contains == type:
                results.append(provider)
        if 'custom' in definitions[provider] and definitions[provider]['custom']:
            results.append(provider)
    return results


def get_icon_path():
    """ Utility method to Burst's icon path

    Returns:
        str: Path to Burst's icon
    """
    return os.path.join(ADDON_PATH, 'icon.png')


def translation(id_value):
    """ Utility method to get translations

    Args:
        id_value (int): Code of translation to get

    Returns:
        str: Translated string
    """
    return ADDON.getLocalizedString(id_value)


def get_int(string):
    """ Utility method to convert a number contained in a string to an integer

    Args:
        string (str): Number contained in a string

    Returns:
        int: The number as an integer, or 0
    """
    if not string:
        return 0
    try:
        return int(string)
    except:
        try:
            return int(get_float(string))
        except:
            pass
    try:
        return int(filter(type(string).isdigit, string))
    except:
        return 0


def get_float(string):
    """ Utility method to convert a number contained in a string to a float

    Args:
        string (str): Number contained in a string

    Returns:
        float: The number as a float, or 0.0
    """
    if not string:
        return float(0)
    try:
        return float(string)
    except:
        try:
            cleaned = clean_number(string)
            floated = re.findall(r'[\d.]+', cleaned)[0]
            return float(floated)
        except:
            pass
    try:
        string = string[:clean_number(string).find('.')]
        return float(filter(type(string).isdigit, string))
    except:
        pass
    try:
        return float(filter(type(string).isdigit, string))
    except:
        return float(0)


def size_int(size_txt):
    """ Utility method to convert a file size contained in a string to an integer of bytes

    Args:
        string (str): File size with suffix contained in a string, eg. ``1.21 GB``

    Returns:
        float: The number of bytes as a float, or 0.0
    """
    try:
        return float(size_txt)
    except:
        try:
            size_txt = size_txt.upper()
            size = get_float(size_txt)
            if 'K' in size_txt:
                size *= 1e3
            if 'M' in size_txt:
                size *= 1e6
            if 'G' in size_txt:
                size *= 1e9
            if 'T' in size_txt:
                size *= 1e12
            return size
        except:
            pass
    return 0


def clean_number(string):
    """ Utility method to clean up a number contained in a string to dot decimal format

    Args:
        string (str): Number contained in a string

    Returns:
        str: The formatted number as a string
    """
    comma = string.find(',')
    point = string.find('.')
    if comma > 0 and point > 0:
        if comma < point:
            string = string.replace(',', '')
        else:
            string = string.replace('.', '')
            string = string.replace(',', '.')
    elif comma > 0:
        string = string.replace(',', '.')
    return string


def clean_size(string):
    """ Utility method to remove unnecessary information from a file size string, eg. '6.5 GBytes' -> '6.5 GB'

    Args:
        string (str): File size string to clean up

    Returns:
        str: Cleaned up file size
    """
    if string:
        pos = string.rfind('B')
        if pos > 0:
            string = string[:pos] + 'B'
    return string


def sizeof(num, suffix='B'):
    """ Utility method to convert a file size in bytes to a human-readable format

    Args:
        num    (int): Number of bytes
        suffix (str): Suffix for 'bytes'

    Returns:
        str: The formatted file size as a string, eg. ``1.21 GB``
    """
    for unit in ['', 'K', 'M', 'G', 'T', 'P', 'E', 'Z']:
        if abs(num) < 1024.0:
            return "%3.1f %s%s" % (num, unit, suffix)
        num /= 1024.0
    return "%.1f %s%s" % (num, 'Y', suffix)


def notify(message, image=None):
    """ Creates a notification dialog

    Args:
        message (str): The message to show in the dialog
        image   (str): Path to an icon for this dialog
    """
    dialog = xbmcgui.Dialog()
    dialog.notification(ADDON_NAME, message, icon=image, sound=False)
    del dialog


def clear_cache():
    """ Clears cookies from Burst's cache
    """
    cookies_path = os.path.join(xbmc.translatePath("special://temp"), "burst")
    if os.path.isdir(cookies_path):
        for f in os.listdir(cookies_path):
            if re.search('.jar', f):
                os.remove(os.path.join(cookies_path, f))


def encode_dict(dict_in, charset='utf8'):
    """ Encodes dict values to UTF-8

    Args:
        dict_in (dict): Input dictionary with unicode values

    Returns:
        dict: Output dictionary with UTF-8 encoded values
    """
    try:
        dict_out = {}
        for k, v in dict_in.iteritems():
            if isinstance(v, unicode):
                v = v.encode('utf8')
            elif isinstance(v, str):
                v = v.decode('utf8')

            if charset != 'utf8':
                v = v.decode('utf8').encode(charset)

            dict_out[k] = v
        return dict_out
    except:
        return dict_in
