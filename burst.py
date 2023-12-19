# -*- coding: utf-8 -*-

import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'resources', 'site-packages'))

from burst.burst import search
from elementum.provider import register, log
from burst.client import Client

def search_movie(payload):
    return search(payload, 'movie')


def search_season(payload):
    return search(payload, 'season')


def search_episode(payload):
    return search(payload, 'episode')

def clear_cookies():
    client = Client()
    cookies = client._locate_cookies()
    log.info("Removing cookies from %s" % (cookies))
    if os.path.isfile(cookies):
        os.remove(cookies)
        log.info("Successfully removed cookies file")


action = None
if len(sys.argv) >= 2:
    action = sys.argv[1]

if action and 'clear_cookies' in action:
    clear_cookies()
else:
    register(search, search_movie, search_episode, search_season)
