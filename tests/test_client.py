# -*- coding: utf-8 -*-

"""
Tests of proxy selection and browser-like headers in burst/client.py; run with: python -m pytest tests
"""

import os
import sys
import types

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
sys.path.insert(0, ROOT)
sys.path.insert(1, os.path.join(ROOT, 'resources', 'site-packages'))

# Kodi modules, with Elementum internal proxy and Burst's own proxy both enabled
SETTINGS = {'use_elementum_proxy': True, 'proxy_enabled': True, 'proxy_use_type': 2, 'cookie_sync_enabled': False}


class _Addon(object):
    def __init__(self, id=None):
        pass

    def getAddonInfo(self, key):
        return ROOT if key == 'path' else os.path.join(ROOT, 'tests', '__pycache__', 'profile')

    def getSetting(self, key):
        return 'true' if key == 'internal_proxy_enabled' else ''


def _get_setting(key, converter=str, choices=None):
    return SETTINGS.get(key, converter())


for name in ('xbmc', 'xbmcaddon', 'xbmcvfs', 'xbmcgui', 'elementum', 'elementum.provider'):
    sys.modules.setdefault(name, types.ModuleType(name))
sys.modules['xbmcaddon'].Addon = _Addon
sys.modules['xbmcvfs'].translatePath = lambda path: path
sys.modules['xbmc'].translatePath = lambda path: path
sys.modules['elementum.provider'].log = types.SimpleNamespace(debug=lambda *a: None, info=lambda *a: None, error=lambda *a: None, warning=lambda *a: None)
sys.modules['elementum.provider'].get_setting = _get_setting

from burst.client import Client  # noqa: E402


def _headers(client, url, **kwargs):
    sent = {}

    def send(prepped, **kw):
        sent.update(prepped.headers)
        raise RuntimeError('not sending')

    client.session.send = send
    client._read_cookies = lambda url='': None
    client.open(url, **kwargs)
    return sent


def test_internal_proxy_wins_over_burst_proxy():
    client = Client(info={'proxy_url': '', 'internal_proxy_url': 'http://10.0.0.1:65222'})
    assert client.session.proxies == {'http': 'http://10.0.0.1:65222', 'https': 'http://10.0.0.1:65222'}


def test_empty_internal_proxy_url_keeps_default():
    client = Client(info={'proxy_url': '', 'internal_proxy_url': ''})
    assert client.session.proxies['https'] == 'http://127.0.0.1:65222'


def test_navigation_headers():
    headers = _headers(Client(), 'https://site.org/search?q=1')
    assert headers['Sec-Fetch-Mode'] == 'navigate'
    assert 'Origin' not in headers
    assert 'Content-Language' not in headers
    assert 'Cache-Control' not in headers
    assert headers['Priority'] == 'u=0, i'


def test_firefox_accept():
    client = Client()
    client.user_agent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:157.0) Gecko/20100101 Firefox/157.0'
    assert _headers(client, 'https://site.org/')['Accept'] == 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'


def test_post_origin_has_no_path():
    headers = _headers(Client(), 'https://site.org/login.php', post_data={'a': 'b'})
    assert headers['Origin'] == 'https://site.org'


def test_xhr_headers():
    headers = _headers(Client(), 'https://site.org/details', headers={'X-Requested-With': 'XMLHttpRequest'})
    assert headers['Sec-Fetch-Mode'] == 'cors'
    assert 'Sec-Fetch-User' not in headers
    assert 'Upgrade-Insecure-Requests' not in headers


def test_api_headers():
    headers = _headers(Client(is_api=True), 'https://api.site.org/v1')
    assert 'Sec-Fetch-Mode' not in headers
    assert 'Referer' not in headers


if __name__ == '__main__':
    for name, test in list(globals().items()):
        if name.startswith('test_'):
            test()
            print('ok', name)
