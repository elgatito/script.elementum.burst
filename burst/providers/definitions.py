# -*- coding: utf-8 -*-
"""
Overrides for provider definitions
"""
import os
import json
import xbmc
import xbmcaddon
from glob import glob
from urlparse import urlparse
from quasar.provider import log
ADDON = xbmcaddon.Addon()

definitions = {}
if "%s" % type(xbmcaddon) != "<class 'sphinx.ext.autodoc._MockModule'>":
    with open(os.path.join(ADDON.getAddonInfo("path"), 'burst', 'providers', 'definitions.json')) as defs:
        definitions = json.load(defs)
else:
    with open(os.path.join('..', 'burst', 'providers', 'definitions.json')) as defs:
        definitions = json.load(defs)

for provider in definitions:
    parsed_url = urlparse(definitions[provider]['base_url'])
    root_url = '%s://%s' % (parsed_url.scheme, parsed_url.netloc)
    definitions[provider]['root_url'] = root_url
    if definitions[provider]['season_keywords']:
        definitions[provider]['season_keywords'] = definitions[provider]['season_keywords'].replace('Season_{season}', 'season {season:2}')
    if definitions[provider]['season_keywords2']:
        definitions[provider]['season_keywords2'] = definitions[provider]['season_keywords2'].replace('Season{season}', 's{season:2}')

# Load custom providers
if "%s" % type(xbmcaddon) != "<class 'sphinx.ext.autodoc._MockModule'>":
    custom_providers = os.path.join(xbmc.translatePath(ADDON.getAddonInfo("profile")), "providers")
else:
    custom_providers = '.'
if not os.path.exists(custom_providers):
    try:
        os.makedirs(custom_providers)
    except Exception as e:
        log.error("Unable to create custom providers folder: %s", repr(e))
        pass
for provider_file in glob(os.path.join(custom_providers, "*.json")):
    log.info("Importing and enabling %s" % provider_file)
    try:
        with open(os.path.join(custom_providers, provider_file)) as provider_def:
            custom_definitions = json.load(provider_def)
            for provider in custom_definitions:
                custom_definitions[provider]['custom'] = True
                parsed_url = urlparse(custom_definitions[provider]['base_url'])
                root_url = '%s://%s' % (parsed_url.scheme, parsed_url.netloc)
                custom_definitions[provider]['root_url'] = root_url
            definitions.update(custom_definitions)
    except Exception as e:
        import traceback
        log.error("Failed importing custom provider from %s: %s", provider_def, repr(e))
        map(log.error, traceback.format_exc().split("\n"))

# Load custom overrides
if "%s" % type(xbmcaddon) != "<class 'sphinx.ext.autodoc._MockModule'>":
    overrides = os.path.join(xbmc.translatePath(ADDON.getAddonInfo("profile")), "overrides.py")
else:
    overrides = '.'
if os.path.exists(overrides):
    try:
        import sys
        sys.path.append(os.path.dirname(overrides))
        from overrides import overrides
        for provider_overrides in overrides:
            definitions[provider_overrides].update(overrides[provider_overrides])
    except Exception as e:
        import traceback
        log.error("Failed importing custom overrides: %s", repr(e))
        map(log.error, traceback.format_exc().split("\n"))


#############
# Overrides #
#############

# TorLock
definitions['torlock']['parser']['torrent'] = "'" + definitions['torlock']['root_url'] + definitions['torlock']['parser']['torrent'][1:]
definitions['torlock']['season_keywords'] = '{title} s{season:2}'
definitions['torlock']['season_keywords2'] = None
definitions['torlock']['filter_title'] = True

# 1337x
definitions['1337x']['root_url'] = definitions['1337x']['root_url'].replace('http://', 'https://')
definitions['1337x']['base_url'] = definitions['1337x']['base_url'].replace('http://', 'https://')
definitions['1337x']['parser']['torrent'] = "'" + definitions['1337x']['root_url'] + "%s' % " + definitions['1337x']['parser']['torrent']
definitions['1337x']['season_keywords'] = '{title} s{season:2}'
definitions['1337x']['season_keywords2'] = None

# MagnetDL
definitions['magnetdl']['name'] = 'MagnetDL'
definitions['magnetdl']['base_url'] = 'http://www.magnetdl.com/FIRSTLETTER/QUERYEXTRA/'
definitions['magnetdl']['separator'] = '-'
definitions['magnetdl']['season_keywords'] = '{title} s{season:2}'
definitions['magnetdl']['season_keywords2'] = None

# Cpasbien
definitions['cpasbien']['language'] = 'fr'

# Nextorrent
definitions['nextorrent']['general_keywords'] = '{title:fr}'
definitions['nextorrent']['movie_keywords'] = '{title:fr} {year}'

# Torrent9
definitions['torrent9']['subpage'] = False
definitions['torrent9']['parser']['torrent'] = "'" + definitions['torrent9']['root_url'] + "%s' % (" + definitions['torrent9']['parser']['torrent'] + ")"
definitions['torrent9']['general_keywords'] = '{title:fr}'
definitions['torrent9']['movie_keywords'] = '{title:fr} {year}'

# YourBitTorrent
definitions['yourbittorrent']['parser']['torrent'] = "'" + definitions['yourbittorrent']['root_url'] + definitions['yourbittorrent']['parser']['torrent'][1:]

# TorrentFunk
definitions['torrentfunk']['parser']['torrent'] = "'" + definitions['torrentfunk']['root_url'] + definitions['torrentfunk']['parser']['torrent'][1:]

# idope
definitions['idope']['parser']['torrent'] = "'magnet:?xt=urn:btih:%s' % " + definitions['idope']['parser']['infohash']
definitions['idope']['tv_keywords'] = '{title} s{season:2}'
definitions['idope']['tv_keywords2'] = '{title} s{season:2}e{episode:2}'

# Monova
definitions['monova']['parser']['torrent'] = definitions['monova']['parser']['torrent'] + '.replace("//monova.org", "")'

# TorrentZ
definitions['torrentz']['parser']['torrent'] = "'magnet:?xt=urn:btih:%s' % " + definitions['torrentz']['parser']['infohash']
definitions['torrentz']['filter_title'] = True

# Ilcorsaronero
definitions['ilcorsaronero']['parser']['torrent'] = "'magnet:?xt=urn:btih:%s' % " + definitions['ilcorsaronero']['parser']['infohash']

# Ruhunt
definitions['ruhunt']['base_url'] = "http://ruhunt.org/search?q=QUERYEXTRA&i=s"

# Rutor
definitions['rutor']['tv_keywords'] = '{title} s{season:2}'
definitions['rutor']['tv_keywords2'] = '{title} s{season:2}e{episode:2}'

# YTS
definitions['yts']['is_api'] = True
definitions['yts']['separator'] = '%20'
definitions['yts']['base_url'] = 'https://yts.ag/api/v2/list_movies.json'
definitions['yts']['general_query'] = '?query_term=QUERY&sort_by=seeds&order_by=desc'
definitions['yts']['movie_query'] = definitions['yts']['general_query']
definitions['yts']['show_query'] = definitions['yts']['general_query']
definitions['yts']['season_query'] = definitions['yts']['general_query']
definitions['yts']['anime_query'] = definitions['yts']['general_query']
definitions['yts']['movie_keywords'] = '{title}'
definitions['yts']['api_format'] = {
    'results': 'data.movies',
    'name': 'title_long',
    'subresults': 'torrents',
    'torrent': 'url',
    'quality': 'quality',
    'info_hash': 'hash',
    'seeds': 'seeds',
    'peers': 'peers',
    'size': 'size',
}

# RARBG
definitions['rarbg']['is_api'] = True
definitions['rarbg']['base_url'] = 'https://torrentapi.org/pubapi_v2.php'
definitions['rarbg']['token'] = '?get_token=get_token&app_id=script.quasar.burst'
definitions['rarbg']['general_query'] = '?mode=search&search_string=QUERY&format=json_extended&app_id=script.quasar.burst&token=TOKEN'
definitions['rarbg']['movie_query'] = definitions['rarbg']['general_query']
definitions['rarbg']['show_query'] = definitions['rarbg']['general_query']
definitions['rarbg']['season_query'] = definitions['rarbg']['general_query']
definitions['rarbg']['anime_query'] = definitions['rarbg']['general_query']
definitions['rarbg']['season_keywords'] = '{title} s{season:2}'
definitions['rarbg']['api_format'] = {
    'results': 'torrent_results',
    'torrent': 'download',
    'name': 'title',
    'seeds': 'seeders',
    'peers': 'leechers',
    'size': 'size',
}


#
# Private trackers
#

# TorrentLeech
definitions['torrentleech']['subpage'] = False

# AlphaReign
definitions['alphareign']['login_object'] = "{'username': USERNAME, 'password': PASSWORD, 'csrf_name': CSRF_NAME, 'csrf_value': CSRF_VALUE}"

# freshon.tv
definitions['freshon.tv']['spoof'] = 'Deluge 1.3.12.0'
definitions['freshon.tv']['subpage'] = False
definitions['freshon.tv']['tv_keywords'] = '{title} S{season:2}'
definitions['freshon.tv']['tv_keywords2'] = None
definitions['freshon.tv']['season_keywords'] = '{title} S{season:2}'
definitions['freshon.tv']['season_keywords2'] = None
definitions['freshon.tv']['parser']['torrent'] = "'" + definitions['freshon.tv']['root_url'] + "%s' % " + definitions['freshon.tv']['parser']['torrent']

# FileList
definitions['filelist']['parser']['torrent'] = "'/%s' % " + definitions['filelist']['parser']['torrent']
definitions['filelist']['movie_query'] = '19&searchin=0&sort=0'

# XtremeZone
definitions['myxzorg']['root_url'] = definitions['myxzorg']['root_url'].replace('http://', 'https://')
definitions['myxzorg']['base_url'] = definitions['myxzorg']['base_url'].replace('http://', 'https://')
definitions['myxzorg']['subpage'] = False
definitions['myxzorg']['parser']['peers'] = "item(tag='td', order=9)"
definitions['myxzorg']['parser']['seeds'] = "item(tag='td', order=7)"
definitions['myxzorg']['parser']['torrent'] = "item(tag='a', attribute='href', order=5)"
definitions['myxzorg']['parser']['torrent'] = "'" + definitions['myxzorg']['root_url'] + "/%s' % " + \
                                              definitions['myxzorg']['parser']['torrent'] + \
                                              ".replace('details.php', 'dwn.php')"


# T411
def t411season(season):
    real_s = season + 967
    if season == 25:
        real_s = 994
    if 25 < season < 28:
        real_s = season + 966
    return real_s


def t411episode(episode):
    real_ep = 936
    if 8 < episode < 31:
        real_ep = episode + 937
    if 30 < episode < 61:
        real_ep = episode + 1057
    return real_ep


definitions['t411']['is_api'] = True
definitions['t411']['filter_title'] = True
definitions['t411']['base_url'] = 'https://api.t411.li'
definitions['t411']['root_url'] = definitions['t411']['base_url']
definitions['t411']['token_auth'] = '/auth'
definitions['t411']['login_object'] = "{'username': USERNAME, 'password': PASSWORD}"
definitions['t411']['download_path'] = '/torrents/download/'
definitions['t411']['general_query'] = '/torrents/search/QUERY?limit=100&cid=0'
definitions['t411']['movie_query'] = '/torrents/search/QUERY?limit=100&cid=631'
definitions['t411']['show_query'] = '/torrents/search/QUERY?limit=100&cid=433&EXTRA'
definitions['t411']['season_query'] = '/torrents/search/QUERY?limit=100&cid=433&EXTRA'
definitions['t411']['anime_query'] = '/torrents/search/QUERY?limit=100&cid=637&EXTRA'
definitions['t411']['tv_extra'] = "term[45][]={season+t411season}&term[46][]={episode+t411episode}"
definitions['t411']['season_extra'] = "term[45][]={season+t411season}&term[46][]=936"
definitions['t411']['api_format'] = {
    'results': 'torrents',
    'name': 'name',
    'torrent': 'id',
    'size': 'size',
    'seeds': 'seeders',
    'peers': 'leechers',
}

# HD Torrents
definitions['hd-torrents'] = {
    "anime_extra": "",
    "anime_keywords": "{title} {episode}",
    "anime_query": "EXTRA",
    "base_url": "https://hd-torrents.org/torrents.php?csrfToken=CSRF_TOKEN&search=QUERYEXTRA&active=1&order=seeds&by=DESC",
    "color": "FFCFCFCF",
    "general_extra": "",
    "general_keywords": "{title}",
    "general_query": "",
    "language": None,
    "login_failed": "Recover",
    "login_object": "{'uid': USERNAME, 'pwd': PASSWORD, 'csrfToken': CSRF_TOKEN}",
    "login_path": "/login.php",
    "movie_extra": "",
    "movie_keywords": "{title} {year}",
    "movie_query": "",
    "name": "HD Torrents",
    "parser": {
        "infohash": "",
        "name": "item(tag='a', order=2)",
        "peers": "item(tag='td', order=11)",
        "row": "find_once('table', ('class', 'mainblockcontenttt')).find_all('tr', start=3)",
        "seeds": "item(tag='td', order=10)",
        "size": "item(tag='td', order=8)",
        "torrent": "'https://hd-torrents.org/%s' % item(tag='a', attribute='href', order=5)"
    },
    "private": True,
    "root_url": "https://hd-torrents.org",
    "season_extra": "",
    "season_extra2": "",
    "season_keywords": "{title} Season {season:2}",
    "season_keywords2": "{title} S{season:2}",
    "season_query": "",
    "separator": "+",
    "show_query": "",
    "subpage": False,
    "tv_extra": "",
    "tv_extra2": "",
    "tv_keywords": "{title} s{season:2}e{episode:2}",
    "tv_keywords2": ""
}
