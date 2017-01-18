# -*- coding: utf-8 -*-

import os
import json
import xbmcaddon
from urlparse import urlparse

definitions = {}
with open(os.path.join(xbmcaddon.Addon().getAddonInfo("path"), 'libs', 'providers', 'definitions.json')) as defs:
    definitions = json.load(defs)

for provider in definitions:
    parsed_url = urlparse(definitions[provider]['base_url'])
    root_url = '%s://%s' % (parsed_url.scheme, parsed_url.netloc)
    definitions[provider]['root_url'] = root_url


#############
# Overrides #
#############

# TorLock
definitions['torlock']['parser']['torrent'] = "'" + definitions['torlock']['root_url'] + definitions['torlock']['parser']['torrent'][1:]

# 1337x
definitions['1337x']['root_url'] = definitions['1337x']['root_url'].replace('http://', 'https://')
definitions['1337x']['base_url'] = definitions['1337x']['base_url'].replace('http://', 'https://')
definitions['1337x']['parser']['torrent'] = "'" + definitions['1337x']['root_url'] + "%s' % " + definitions['1337x']['parser']['torrent']

# MagnetDL
definitions['magnetdl']['name'] = 'MagnetDL'
definitions['magnetdl']['base_url'] = 'http://www.magnetdl.com/FIRSTLETTER/QUERYEXTRA/'
definitions['magnetdl']['separator'] = '-'

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
definitions['idope']['parser']['torrent'] = "'magnet:?xt=%s' % " + definitions['idope']['parser']['infohash']
definitions['idope']['tv_keywords2'] = '{title} S{season:2}'

# Monova
definitions['monova']['parser']['torrent'] = definitions['monova']['parser']['torrent'] + '.replace("//monova.org", "")'

# TorrentZ
definitions['torrentz']['parser']['torrent'] = "'magnet:?xt=%s' % " + definitions['torrentz']['parser']['infohash']

# Ilcorsaronero
definitions['ilcorsaronero']['parser']['torrent'] = "'magnet:?xt=%s' % " + definitions['ilcorsaronero']['parser']['infohash']

# Ruhunt
definitions['ruhunt']['base_url'] = "http://ruhunt.org/search?q=QUERYEXTRA&i=s"

# Rutor
definitions['rutor']['tv_keywords2'] = '{title} S{season:2}'

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
definitions['rarbg']['token'] = '?get_token=get_token&app_id=script.magnetic.rarbg-mc'
definitions['rarbg']['general_query'] = '?mode=search&search_string=QUERY&format=json_extended&app_id=script.magnetic.rarbg-mc&token=TOKEN'
definitions['rarbg']['movie_query'] = definitions['rarbg']['general_query']
definitions['rarbg']['show_query'] = definitions['rarbg']['general_query']
definitions['rarbg']['season_query'] = definitions['rarbg']['general_query']
definitions['rarbg']['anime_query'] = definitions['rarbg']['general_query']
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
definitions['freshon.tv']['subpage'] = False
definitions['freshon.tv']['tv_keywords'] = '{title} S{season:2}'
definitions['freshon.tv']['tv_keywords2'] = '{title} s{season:2}e{episode:2}'
definitions['freshon.tv']['parser']['torrent'] = "'" + definitions['freshon.tv']['root_url'] + "%s' % " + definitions['freshon.tv']['parser']['torrent']

# FileList
definitions['filelist']['parser']['torrent'] = "'/%s' % " + definitions['filelist']['parser']['torrent']
definitions['filelist']['movie_query'] = '19&searchin=0&sort=0'

# T411
definitions['t411']['parser']['torrent'] = definitions['t411']['parser']['torrent'] + '.replace("//www.t411.li", "")'
definitions['t411']['is_api'] = True
definitions['t411']['base_url'] = 'https://api.t411.li'
definitions['t411']['root_url'] = definitions['t411']['base_url']
definitions['t411']['token_auth'] = '/auth'
definitions['t411']['login_object'] = "{'username': USERNAME, 'password': PASSWORD}"
definitions['t411']['download_path'] = '/torrents/download/'
definitions['t411']['general_query'] = '/torrents/search/QUERY?limit=100&cid=0'
definitions['t411']['movie_query'] = definitions['t411']['general_query']
definitions['t411']['show_query'] = '/torrents/search/QUERY?limit=100&cid=433'
definitions['t411']['season_query'] = '/torrents/search/QUERY?limit=100&cid=433'
definitions['t411']['anime_query'] = '/torrents/search/QUERY?limit=100&cid=637'
definitions['t411']['tv_keywords'] = '{title} S{season:2}'
definitions['t411']['season_keywords1'] = '{title} S{season:2}'
definitions['t411']['season_keywords2'] = '{title} Season{season}'
definitions['t411']['season_keywords3'] = '{title} Season_{season}'
definitions['t411']['api_format'] = {
    'results': 'torrents',
    'name': 'name',
    'torrent': 'id',
    'size': 'size',
    'seeds': 'seeders',
    'peers': 'leechers',
}
