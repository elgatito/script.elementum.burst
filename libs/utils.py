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
    return os.path.join(ADDON_PATH, 'icon.png')


def string(id_value):
    return xbmcaddon.Addon().getLocalizedString(id_value)


def get_int(string):
    if not string:
        return 0
    try:
        return int(string)
    except:
        try:
            return int(get_float(string))
        except:
            pass
    return int(filter(type(string).isdigit, string))


def get_float(string):
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
    return float(filter(type(string).isdigit, string))


def size_int(size_txt):
    try:
        return int(size_txt)
    except:
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


def clean_number(text):
    comma = text.find(',')
    point = text.find('.')
    if comma > 0 and point > 0:
        if comma < point:
            text = text.replace(',', '')
        else:
            text = text.replace('.', '')
            text = text.replace(',', '.')
    elif comma > 0:
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
