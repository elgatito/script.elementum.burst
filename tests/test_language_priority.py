# -*- coding: utf-8 -*-

"""
Tests of the language_priority setting in burst/utils.py; run with: python -m pytest tests
"""

import os
import sys
import types

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
sys.path.insert(0, ROOT)
sys.path.insert(1, os.path.join(ROOT, 'resources', 'site-packages'))


class _Addon(object):
    def __init__(self, id=None):
        pass

    def getAddonInfo(self, key):
        return ROOT if key == 'path' else os.path.join(ROOT, 'tests', '__pycache__', 'profile')

    def getSetting(self, key):
        return ''


for name in ('xbmc', 'xbmcaddon', 'xbmcvfs', 'xbmcgui', 'elementum', 'elementum.provider'):
    sys.modules.setdefault(name, types.ModuleType(name))
sys.modules['xbmcaddon'].Addon = _Addon
sys.modules['xbmcvfs'].translatePath = lambda path: path
sys.modules['xbmc'].translatePath = lambda path: path
sys.modules['elementum.provider'].log = types.SimpleNamespace(debug=lambda *a: None, info=lambda *a: None, error=lambda *a: None, warning=lambda *a: None)
sys.modules['elementum.provider'].get_setting = lambda key, converter=str, choices=None: converter()

from burst.utils import priority_languages  # noqa: E402


def test_kodi_language_keeps_english():
    assert priority_languages('kodi', 'sr') == ['sr', 'en']


def test_english_kodi_is_english_once():
    assert priority_languages('kodi', 'en') == ['en']


def test_chosen_languages_stay_as_chosen():
    assert priority_languages('sr', 'sr') == ['sr']
    assert priority_languages('fr,de', 'sr') == ['fr', 'de']
    assert priority_languages('kodi,fr', 'sr') == ['sr', 'en', 'fr']


def test_all_or_nothing_is_no_priority():
    assert priority_languages('all', 'sr') == []
    assert priority_languages('', 'sr') == []
