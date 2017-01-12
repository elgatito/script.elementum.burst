# -*- coding: utf-8 -*-

import os
import re
import xbmc
import xbmcgui
import xbmcaddon
from quasar.provider import get_setting
from providers.definitions import definitions

ADDON = xbmcaddon.Addon()
ADDON_ID = ADDON.getAddonInfo("id")
ADDON_ICON = ADDON.getAddonInfo("icon")
ADDON_NAME = ADDON.getAddonInfo("name")
ADDON_PATH = ADDON.getAddonInfo("path")
ADDON_VERSION = ADDON.getAddonInfo("version")
PATH_ADDONS = xbmc.translatePath("special://home/addons/")
PATH_TEMP = xbmc.translatePath("special://temp")


class Magnet:
    """
    Create Magnet object with its properties
    """

    def __init__(self, magnet):
        self.magnet = magnet + '&'
        # hash
        info_hash = re.search('urn:btih:(\w+)&', self.magnet, re.IGNORECASE)
        result = ''
        if info_hash is not None:
            result = info_hash.group(1)

        self.info_hash = result
        # name
        name = re.search('dn=(.*?)&', self.magnet)
        result = ''
        if name is not None:
            result = name.group(1).replace('+', ' ')

        self.name = result.title()
        # trackers
        self.trackers = re.findall('tr=(.*?)&', self.magnet)


def get_providers():
    results = []
    for provider in definitions:
        results.append(provider)
    return results


def get_enabled_providers():
    results = []
    for provider in definitions:
        if get_setting('use_%s' % provider, bool):
            results.append(provider)
    return results


def get_icon_path():
    """
    Get the path from add-on's icon
    :return: icon's path
    """
    return os.path.join(ADDON_PATH, 'icon.png')


def string(id_value):
    """
    Internationalisation string
    :param id_value: id value from string.po file
    :type id_value: int
    :return: the translated string
    """
    return xbmcaddon.Addon().getLocalizedString(id_value)


def get_int(text):
    """
    Convert string to integer number
    :param text: string to convert
    :type text: str
    :return: converted string in integer
    """
    return int(get_float(text))


def get_float(string):
    """
    Convert string to float number
    :param text: string to convert
    :type text: str
    :return: converted string in float
    """
    value = 0
    if isinstance(string, (float, long, int)):
        value = float(string)

    elif isinstance(string, str):
        try:
            string = clean_number(string)
            value = float(string)

        except:
            value = 0

    return value


def size_int(size_txt):
    """
    Convert string with size format to integer
    :param size_txt: string to be converted
    :type size_txt: str
    :return: converted string in integer
    """
    try:
        return int(size_txt)

    except:
        size_txt = size_txt.upper()
        size = get_float(size_txt.replace('B', '').replace('I', '').replace('K', '').replace('M', '').replace('G', ''))
        if 'K' in size_txt:
            size *= 1000

        if 'M' in size_txt:
            size *= 1000000

        if 'G' in size_txt:
            size *= 1e9

        return size


def clean_number(text):
    """
    Convert string with a number to USA decimal format
    :param text: string with the number
    :type text: str
    :return: converted number in string
    """
    comma = text.find(',')
    point = text.find('.')
    if comma > 0 and point > 0:
        if comma < point:
            text = text.replace(',', '')

        else:
            text = text.replace('.', '')
            text = text.replace(',', '.')

    return text


def clean_size(text=""):
    """
    Remove unnecessary information from string which has size information ex: 6.50GB
    :param text:
    :return: cleaned string
    """
    if text is not None:
        pos = text.rfind('B')
        if pos > 0:
            text = text[:pos] + 'B'

    return text


def sizeof(num, suffix='B'):
    for unit in ['', 'K', 'M', 'G', 'T', 'P', 'E', 'Z']:
        if abs(num) < 1024.0:
            return "%3.1f %s%s" % (num, unit, suffix)
        num /= 1024.0
    return "%.1f %s%s" % (num, 'Y', suffix)


def normalize_string(name):
    from unicodedata import normalize
    import types
    try:
        normalize_name = name.decode('unicode-escape').encode('latin-1')

    except:
        if types.StringType == type(name):
            unicode_name = unicode(name, 'utf-8', 'ignore')

        else:
            unicode_name = name

        normalize_name = normalize('NFKD', unicode_name).encode('ascii', 'ignore')

    return normalize_name


def notify(message, image=None):
    """
    Create notification dialog
    :param message: message to notify
    :type message: str
    :param image: path of the image
    :type image: str
    """
    dialog = xbmcgui.Dialog()
    dialog.notification(ADDON_NAME, message, icon=image)
    del dialog


def display_message_cache():
    """
    Create the progress dialog when the cache is used
    """
    p_dialog = xbmcgui.DialogProgressBG()
    p_dialog.create('Quasar Burst', string(32061))
    xbmc.sleep(250)
    p_dialog.update(25, string(32065))
    xbmc.sleep(250)
    p_dialog.update(50, string(32065))
    xbmc.sleep(250)
    p_dialog.update(75, string(32065))
    xbmc.sleep(250)
    p_dialog.close()
    del p_dialog


def clear_cache():
    storage_path = os.path.join(xbmc.translatePath("special://temp"), "burst")
    if os.path.isdir(storage_path):
        for f in os.listdir(storage_path):
            if re.search('.cache', f):
                os.remove(os.path.join(storage_path, f))

    cookies_path = xbmc.translatePath("special://temp")
    if os.path.isdir(cookies_path):
        for f in os.listdir(cookies_path):
            if re.search('.jar', f):
                os.remove(os.path.join(cookies_path, f))
