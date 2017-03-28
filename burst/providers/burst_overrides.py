# -*- coding: utf-8 -*-
"""
Default Burst overrides

.. data:: overrides

    Default overrides dictionary
"""

from definitions import definitions


def source():
    """ See source

    Note:
        This just a dummy method for documentation
    """
    return repr(overrides)


overrides = {
    #
    # Public trackers
    #

    # TorLock
    'torlock': {
        'parser': {
            'torrent': "'" + definitions['torlock']['root_url'] + definitions['torlock']['parser']['torrent'][1:]
        },
        'season_keywords': '{title} s{season:2}',
        'season_keywords2': None,
        'filter_title': True
    },

    # 1337x
    '1337x': {
        'root_url': definitions['1337x']['root_url'].replace('http://', 'https://'),
        'base_url': definitions['1337x']['base_url'].replace('http://', 'https://'),
        'season_keywords': '{title} s{season:2}',
        'season_keywords2': None,
        'parser': {}
    },

    # MagnetDL
    'magnetdl': {
        'name': 'MagnetDL',
        'base_url': 'http://www.magnetdl.com/FIRSTLETTER/QUERYEXTRA/',
        'separator': '-',
        'season_keywords': '{title} s{season:2}',
        'season_keywords2': None

    },

    # Cpasbien
    'cpasbien': {
        'language': 'fr'
    },

    # Nextorrent
    'nextorrent': {
        'general_keywords': '{title:fr}',
        'movie_keywords': '{title:fr} {year}'
    },

    # Torrent9
    'torrent9': {
        'subpage': False,
        'parser': {
            'torrent': "'" + definitions['torrent9']['root_url'] + "%s' % (" + definitions['torrent9']['parser']['torrent'] + ")"
        },
        'general_keywords': '{title:fr}',
        'movie_keywords': '{title:fr} {year}'
    },

    # YourBitTorrent
    'yourbittorrent': {
        'parser': {
            'torrent': "'" + definitions['yourbittorrent']['root_url'] + definitions['yourbittorrent']['parser']['torrent'][1:]
        }
    },

    # TorrentFunk
    'torrentfunk': {
        'parser': {
            'torrent': "'" + definitions['torrentfunk']['root_url'] + definitions['torrentfunk']['parser']['torrent'][1:]
        }
    },

    # idope
    'idope': {
        'parser': {
            'torrent': "'magnet:?xt=urn:btih:%s' % " + definitions['idope']['parser']['infohash']
        },
        'tv_keywords': '{title} s{season:2}',
        'tv_keywords2': '{title} s{season:2}e{episode:2}'
    },

    # Monova
    'monova': {
        'parser': {
            'torrent': definitions['monova']['parser']['torrent'] + '.replace("//monova.org", "")'
        }
    },

    # TorrentZ
    'torrentz': {
        'parser': {
            'torrent': "'magnet:?xt=urn:btih:%s' % " + definitions['torrentz']['parser']['infohash']
        },
        'filter_title': True
    },

    # Ilcorsaronero
    'ilcorsaronero': {
        'parser': {
            'torrent': "'magnet:?xt=urn:btih:%s' % " + definitions['ilcorsaronero']['parser']['infohash']
        }
    },

    # Ruhunt
    'ruhunt': {
        'base_url': "http://ruhunt.org/search?q=QUERYEXTRA&i=s",
        'season_keywords': u"{title} \"Сезон {season}\"",
        'season_keywords2': "{title} [S{season:2}]",
        'tv_keywords': "{title} s{season:2}e{episode:2}",
        'tv_keywords2': u"{title} \"Сезон {season}\""
    },

    # Rutor
    'rutor': {
        'anime_query': "0/10/300/2/QUERYEXTRA",
        'movie_query': "0/1/300/2/QUERYEXTRA",
        'season_query': "0/4/300/2/QUERYEXTRA",
        'show_query': "0/4/300/2/QUERYEXTRA",
        'season_keywords': "{title} {season:2}x01|S{season:2}",
        'season_keywords2': "",
        'tv_keywords': '{title} s{season:2}e{episode:2}',
        'tv_keywords2': '{title} {season:2}x01|S{season:2}',
        'parser': {
            'row': "find_once('table', order=3).find_all('tr', start=2)",
            'seeds': "item(tag='span', order=1, select=('class', 'green'))",
            'peers': "item(tag='span', order=1, select=('class', 'red'))",
            'size': "item.find_all('td', ('align', 'right'))[-1].text()",
            'torrent': "'http://rutor.info%s' % (item(tag='a', order=1, attribute='href').split('.info', 1)[-1])"
        }
    },

    # YTS
    'yts': {
        'is_api': True,
        'separator': '%20',
        'base_url': 'https://yts.ag/api/v2/list_movies.json',
        'general_query': '?query_term=QUERY&sort_by=seeds&order_by=desc',
        'movie_query': '?query_term=QUERY&sort_by=seeds&order_by=desc',
        'show_query': '?query_term=QUERY&sort_by=seeds&order_by=desc',
        'season_query': '?query_term=QUERY&sort_by=seeds&order_by=desc',
        'anime_query': '?query_term=QUERY&sort_by=seeds&order_by=desc',
        'movie_keywords': '{title}',
        'api_format': {
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
    },

    # RARBG
    'rarbg': {
        'is_api': True,
        'base_url': 'https://torrentapi.org/pubapi_v2.php',
        'token': '?get_token=get_token&app_id=script.quasar.burst',
        'general_query': '?mode=search&search_string=QUERY&format=json_extended&app_id=script.quasar.burst&token=TOKEN',
        'movie_query': '?mode=search&search_string=QUERY&format=json_extended&app_id=script.quasar.burst&token=TOKEN',
        'show_query': '?mode=search&search_string=QUERY&format=json_extended&app_id=script.quasar.burst&token=TOKEN',
        'season_query': '?mode=search&search_string=QUERY&format=json_extended&app_id=script.quasar.burst&token=TOKEN',
        'anime_query': '?mode=search&search_string=QUERY&format=json_extended&app_id=script.quasar.burst&token=TOKEN',
        'season_keywords': '{title} s{season:2}',
        'api_format': {
            'results': 'torrent_results',
            'torrent': 'download',
            'name': 'title',
            'seeds': 'seeders',
            'peers': 'leechers',
            'size': 'size',
        }
    },

    # Nyaa
    'nyaa': {
        'root_url': "https://www.nyaa.se/",
        'base_url': "https://www.nyaa.se/?page=search&cats=1_0&term=QUERY&EXTRA&sort=2",
        'parser': {
            'torrent': "'https:%s' % item(tag='a', select=('title', 'Download'), attribute='href', order=1)"
        }
    },


    #
    # Private trackers
    #

    # TorrentLeech
    'torrentleech': {
        'subpage': False
    },

    # AlphaReign
    'alphareign': {
        'login_object': "{'username': USERNAME, 'password': PASSWORD, 'csrf_name': CSRF_NAME, 'csrf_value': CSRF_VALUE}"
    },

    # freshon.tv
    'freshon.tv': {
        'spoof': 'Deluge 1.3.12.0',
        'subpage': False,
        'tv_keywords': '{title} S{season:2}',
        'tv_keywords2': None,
        'season_keywords': '{title} S{season:2}',
        'season_keywords2': None,
        'parser': {
            'torrent': "'" + definitions['freshon.tv']['root_url'] + "%s' % " + definitions['freshon.tv']['parser']['torrent']
        }
    },

    # FileList
    'filelist': {
        'parser': {
            'torrent': "'/%s' % " + definitions['filelist']['parser']['torrent']
        },
        'movie_query': '19&searchin=0&sort=0'
    },

    # XtremeZone
    'myxzorg': {
        'root_url': definitions['myxzorg']['root_url'].replace('http://', 'https://'),
        'base_url': definitions['myxzorg']['base_url'].replace('http://', 'https://'),
        'subpage': False,
        'parser': {
            'peers': "item(tag='td', order=9)",
            'seeds': "item(tag='td', order=7)",
            'torrent': "item(tag='a', attribute='href', order=5)"
        }
    },

    # T411
    't411': {
        'is_api': True,
        'filter_title': True,
        'base_url': 'https://api.t411.ai',
        'root_url': 'https://api.t411.ai',
        'token_auth': '/auth',
        'login_object': "{'username': USERNAME, 'password': PASSWORD}",
        'download_path': '/torrents/download/',
        'general_query': '/torrents/search/QUERY?limit=100&cid=0',
        'movie_query': '/torrents/search/QUERY?limit=100&cid=631',
        'show_query': '/torrents/search/QUERY?limit=100&cid=433&EXTRA',
        'season_query': '/torrents/search/QUERY?limit=100&cid=433&EXTRA',
        'anime_query': '/torrents/search/QUERY?limit=100&cid=637&EXTRA',
        'tv_extra': "term[45][]={season+t411season}&term[46][]={episode+t411episode}",
        'season_extra': "term[45][]={season+t411season}&term[46][]=936",
        'api_format': {
            'results': 'torrents',
            'name': 'name',
            'torrent': 'id',
            'size': 'size',
            'seeds': 'seeders',
            'peers': 'leechers',
        }
    },

    # UHDBits
    'uhdbits': {
        'subpage': False,
        'base_url': "https://uhdbits.org/torrents.php?order_way=desc&order_by=seeders&rating=0&rating1=10&"
                    "searchstr=QUERYEXTRA&taglist=&tags_type=1&action=basic&searchsubmit=1",
        'name': "UHDBits",
        'parser': {
            "row": "find_all('tr', ('class', 'torrent'))",
            "name": "'%s %s' % (item(tag='a', order=4), item(tag='div', order=1, select=('class', 'torrent_info')))",
            "size": "item(tag='td', order=5)",
            "seeds": "item(tag='td', order=6)",
            "peers": "item(tag='td', order=7)",
            "torrent": "'https://uhdbits.org/%s' % item(tag='a', attribute='href', order=2)"
        }
    },
}

# Overrides that change overrides
overrides['1337x']['parser']['torrent'] = "'" + overrides['1337x']['root_url'] + "%s' % " + definitions['1337x']['parser']['torrent']

overrides['myxzorg']['parser']['torrent'] = "'" + overrides['myxzorg']['root_url'] + "/%s' % " + \
                                              overrides['myxzorg']['parser']['torrent'] + \
                                              ".replace('details.php', 'dwn.php')"
