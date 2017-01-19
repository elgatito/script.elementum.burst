#!/usr/bin/env python

import os
import re
import sys
import json
from bs4 import BeautifulSoup

mainFile = 'main.py'
addonFile = 'addon.xml'
settingsFile = os.path.join('resources', 'settings.xml')


def parse(main=None, addon=None, settings=None, provider=None, path=None, from_cli=False):
    if addon is None and path is None:
        raise Exception("No path specified.")

    if addon is None:
        with open(path + addonFile, 'r') as addonContent:
            addon = addonContent.read()

    if settings is None:
        with open(path + settingsFile, 'r') as settingsContent:
            settings = settingsContent.read()

    parsed = BeautifulSoup(settings, 'lxml')
    parsed_addon = BeautifulSoup(addon, 'lxml')

    color = re.findall(r".*COLOR\s(\w+)\].*", addon)
    provider_name = parsed_addon.addon['name'].replace('Magnetic', '').replace("MC's", '').replace('Provider', '').replace('[/COLOR]', '').strip()
    provider_name = re.sub(r'\[COLOR\s+[\w]+\]', '', provider_name)
    private = parsed.settings.findAll('category')[0]['label'] == '32000'  # Has a username/password section...

    general_url = re.findall(r".*id=\"general_url\"[\r\n]?\s+default=\"(.*)\".*", settings)
    movie_url = re.findall(r".*id=\"movie_url\"[\r\n]?\s+default=\"(.*)\"", settings)
    show_url = re.findall(r".*id=\"tv_url\"[\r\n]?\s+default=\"(.*)\"", settings)
    season_url = re.findall(r".*id=\"season_url\"[\r\n]?\s+default=\"(.*)\"", settings)
    anime_url = re.findall(r".*id=\"anime_url\"[\r\n]?\s+default=\"(.*)\"", settings)
    separator = re.findall(r".*id=\"separator\"[\r\n]?\s+default=\"(.*)\"", settings)

    general_keywords = re.findall(r".*id=\"general_query1\"[\r\n]?\s+default=\"(.*)\"", settings)
    general_extra = re.findall(r".*id=\"general_extra1\"[\r\n]?\s+default=\"(.*)\"", settings)
    movie_keywords = re.findall(r".*id=\"movie_query1\"[\r\n]?\s+default=\"(.*)\"", settings)
    movie_extra = re.findall(r".*id=\"movie_extra1\"[\r\n]?\s+default=\"(.*)\"", settings)
    tv_keywords = re.findall(r".*id=\"tv_query1\"[\r\n]?\s+default=\"(.*)\"", settings)
    tv_keywords2 = re.findall(r".*id=\"tv_query2\"[\r\n]?\s+default=\"(.*)\"", settings)
    tv_extra = re.findall(r".*id=\"tv_extra1\"[\r\n]?\s+default=\"(.*)\"", settings)
    tv_extra2 = re.findall(r".*id=\"tv_extra2\"[\r\n]?\s+default=\"(.*)\"", settings)
    season_keywords = re.findall(r".*id=\"season_query1\"[\r\n]?\s+default=\"(.*)\"", settings)
    season_keywords2 = re.findall(r".*id=\"season_query2\"[\r\n]?\s+default=\"(.*)\"", settings)
    season_extra = re.findall(r".*id=\"season_extra1\"[\r\n]?\s+default=\"(.*)\"", settings)
    season_extra2 = re.findall(r".*id=\"season_extra2\"[\r\n]?\s+default=\"(.*)\"", settings)
    anime_keywords = re.findall(r".*id=\"anime_query1\"[\r\n]?\s+default=\"(.*)\"", settings)
    anime_extra = re.findall(r".*id=\"anime_extra1\"[\r\n]?\s+default=\"(.*)\"", settings)

    subpage = re.findall(r".*id=\"read_magnet_link\"[\r\n]?\s+default=\"(.*)\"", settings)
    row = re.findall(r".*id=\"row_search\"[\r\n]?\s+default=\"(.*)\"", settings)
    name = re.findall(r".*id=\"name_search\"[\r\n]?\s+default=\"(.*)\"", settings)
    infohash = re.findall(r".*id=\"info_hash_search\"[\r\n]?\s+default=\"(.*)\"", settings)
    torrent = re.findall(r".*id=\"magnet_search\"[\r\n]?\s+default=\"(.*)\"", settings)
    size = re.findall(r".*id=\"size_search\"[\r\n]?\s+default=\"(.*)\"", settings)
    seeds = re.findall(r".*id=\"seeds_search\"[\r\n]?\s+default=\"(.*)\"", settings)
    peers = re.findall(r".*id=\"peers_search\"[\r\n]?\s+default=\"(.*)\"", settings)
    language = re.findall(r".*\"\{title:(\w+)\}\".*", settings)

    login_path = None
    login_object = ''
    login_failed = ''
    if private:
        if main is None:
            with open(path + mainFile, 'r') as mainContent:
                main = mainContent.read()
        login = re.findall(r".*Browser\.login\(Settings\.url\s?\+\s?\'(.*)\',[\r\n]?\s+{(.*[\r\n]?\s?.*[\r\n]?\s?.*[\r\n]?\s?.*[\r\n]?\s?.*)},\s+[\r\n]?[\'\"](.*)[\'\"]\)", main)  # NOQA
        if login:
            login_path = login[0][0]
            if not login_path.startswith('/'):
                login_path = '/' + login_path
            login_object = login[0][1].replace(': username', ': USERNAME').replace(': password', ': PASSWORD')
            login_object = login_object.replace('\n', '').replace('\r', '').replace('  ', '')
            login_object = "{%s}" % login_object
            login_failed = login[0][2]

    # Get common base_url
    base_url = general_url[0] if general_url else None
    if base_url:
        urls = general_url + movie_url + show_url + season_url + anime_url
        common = os.path.commonprefix(urls)
        if common:
            base_url = common

    if path and provider is None:
        provider = path.split('.')[-1][:-1]

    export = {provider: {
        'name': provider_name,
        'color': color[0],
        'private': private,
        'login_path': login_path,
        'login_object': '%s' % login_object.strip(),
        'login_failed': '%s' % login_failed.strip(),
        'base_url': base_url,
        'general_query': general_url[0].replace(base_url, '') if general_url else None,
        'movie_query': movie_url[0].replace(base_url, '') if movie_url else None,
        'show_query': show_url[0].replace(base_url, '') if show_url else None,
        'season_query': season_url[0].replace(base_url, '') if season_url else None,
        'anime_query': anime_url[0].replace(base_url, '') if anime_url else None,
        'separator': separator[0] if separator else None,
        'language': language[0] if language else None,
        'general_keywords': general_keywords[0] if general_keywords else None,
        'general_extra': general_extra[0] if general_extra else None,
        'movie_keywords': movie_keywords[0] if movie_keywords else None,
        'movie_extra': movie_extra[0] if movie_extra else None,
        'tv_keywords': tv_keywords[0] if tv_keywords else None,
        'tv_keywords2': tv_keywords2[0] if tv_keywords2 else None,
        'tv_extra': tv_extra[0] if tv_extra else None,
        'tv_extra2': tv_extra2[0] if tv_extra2 else None,
        'anime_keywords': anime_keywords[0] if anime_keywords else None,
        'anime_extra': anime_extra[0] if anime_extra else None,
        'season_keywords': season_keywords[0] if season_keywords else None,
        'season_keywords2': season_keywords2[0] if season_keywords2 else None,
        'season_extra': season_extra[0] if season_extra else None,
        'season_extra2': season_extra2[0] if season_extra2 else None,
        'subpage': subpage[0] == 'true' if subpage else None,
        'parser': {
            'row': row[0] if row else None,
            'name': name[0] if name else None,
            'infohash': infohash[0] if infohash else None,
            'torrent': torrent[0] if torrent else None,
            'size': size[0] if size else None,
            'seeds': seeds[0] if seeds else None,
            'peers': peers[0] if peers else None,
        }
    }}
    if from_cli:
        print json.dumps(export, indent=4, sort_keys=True, separators=(',', ': ')).replace('null', 'None')
    else:
        return export


if __name__ == "__main__":
    if len(sys.argv) < 2:
        raise Exception("Not enough arguments")

    path = sys.argv[1]
    if not path.endswith(os.path.sep):
        path += os.path.sep

    parse(addon=None,
          settings=None,
          provider=None,
          path=path,
          from_cli=True)
