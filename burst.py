# -*- coding: utf-8 -*-

from burst.burst import search
from elementum.provider import register


def search_movie(payload):
    return search(payload, 'movie')


def search_season(payload):
    return search(payload, 'season')


def search_episode(payload):
    return search(payload, 'episode')


register(search, search_movie, search_episode, search_season)
