# -*- coding: utf-8 -*-

"""
Tests of the season and episode check in burst/episodes.py; run with: python -m pytest tests
"""

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from burst.episodes import name_matches


# Names for an episode search for S02E09
KEEP_S02E09 = [
    'Show.S02E09.1080p.WEB.h264',
    'Show S02 E09 720p',
    'Show S02 EP09 720p',
    'Show.S02.Episode.9.720p',
    'Show_S02E09_720p',
    'Show 2x09 HDTV',
    'Show S02E09v2 720p',
    'Show S02E08-E10 1080p',
    'Show S02E08-S02E10 1080p',
    'Show S01E01-S04E10 Complete',
    'Show S02E08E09E10 720p',
    'Show S02E08-09-10 720p',
    'Show S02E08 & E09 720p',
    'Show 2x08-2x10 HDTV',
    'Show 2x08-10 HDTV',
    'Show S02E08\u2013E10 1080p',
    'Show S02 1080p WEB',
    'Show Season 2 Complete',
    'Show Season 2 Episode 9',
    'Show Season 2 Episodes 1-10',
    'Show S02 1080p E09',
    'Show S01-S06 1080p',
    'Show Season 1-6',
    'Show Seasons 1 to 4',
    'Show S01\u2013S04 1080p',
    'Show Season 1\u20144',
    'Show S01 through S04',
    'Show S01 thru S04',
    'Show S01 & S02 1080p',
    'Show Seasons 1, 2 and 4',
    'Show S02-09 Complete',
    'Show Complete Series 1080p',
    'Show 1920x1080 x264',
    'Шоу Сезон 2 1080p',
    'Шоу / Сезон: 2 / Серии: 1-10 из 10',
    'Шоу 2 сезон 1080p',
    'Шоу 2-й сезон',
    'Шоу 1-4 сезоны',
    'Show Saison 2',
    'Show Temporada 2',
    'Show Staffel 2',
    'Show 2\u044509 HDTV',
    'Show E09 720p',
]

DROP_S02E09 = [
    'Show.S02E10.1080p.WEB.h264',
    'Show S03E09 720p',
    'Show 2x10 HDTV',
    'Show 3x09 HDTV',
    'Show S02E05-E08 1080p',
    'Show S02E10-S02E12 1080p',
    'Show S01E01-S02E08 1080p',
    'Show S02E05E06E07 720p',
    'Show Season 2 Episode 5',
    'Show Season 2 Ep 5',
    'Show Season 2 - E05',
    'Show S02 1080p E05',
    'Show Season 2 Episodes 1-8',
    'Show Season 1',
    'Show S04 Complete 1080p',
    'Show S03-S04 1080p',
    'Show S01 & S04 1080p',
    'Show S01 and S03',
    'Шоу Сезон 1 1080p',
    'Шоу / Сезон: 2 / Серии: 1-8 из 10',
    'Шоу 1 сезон',
    'Show Saison 1',
    'Show Temporada 1',
    'Show Staffel 1',
    'Show E05 720p',
]


@pytest.mark.parametrize('name', KEEP_S02E09)
def test_episode_search_keeps(name):
    assert name_matches(name, 2, 9)


@pytest.mark.parametrize('name', DROP_S02E09)
def test_episode_search_drops(name):
    assert not name_matches(name, 2, 9)


@pytest.mark.parametrize('tag', ['720p', '480p', '576p', '360p', '240p', '1080p', '2160p', '10bit'])
def test_quality_after_hyphen_is_not_a_range(tag):
    name = 'Show S02E09-%s WEB' % tag
    assert name_matches(name, 2, 9)
    assert not name_matches(name, 2, 10)
    assert not name_matches(name, 2, 100)


@pytest.mark.parametrize('name', ['Show S02E08E09E10 720p', 'Show S02E08-09-10 720p', 'Show S02E08-E09-E10 720p'])
def test_three_episodes(name):
    assert name_matches(name, 2, 8)
    assert name_matches(name, 2, 10)
    assert not name_matches(name, 2, 7)
    assert not name_matches(name, 2, 11)


def test_season_list_is_not_a_range():
    for season in (2, 3):
        assert not name_matches('Show S01 & S04 1080p', season)
    assert name_matches('Show S01 & S04 1080p', 4)


def test_season_range_without_second_s():
    # S02-09 is read as seasons 2 to 9 (S01-09 Complete); S02E09 is kept either way
    assert name_matches('Show S02-09 Complete', 2, 9)
    assert name_matches('Show S02-09 Complete', 5, 1)
    assert name_matches('Show S02-09 Complete', 9)
    assert not name_matches('Show S02-09 Complete', 1, 9)
    assert not name_matches('Show S02-09 Complete', 10, 1)


def test_cyrillic_x():
    assert name_matches('Show 2\u044509 HDTV', 2, 9)
    assert not name_matches('Show 2\u044509 HDTV', 3, 9)


@pytest.mark.parametrize('name, kept', [
    ('Show S02 1080p', True),
    ('Show S02E05 720p', True),
    ('Show 2x05 HDTV', True),
    ('Show S01-S04 1080p', True),
    ('Show S01E01-S04E10 Complete', True),
    ('Show Season 1 through 4', True),
    ('Шоу Сезон 2', True),
    ('Show Complete Series', True),
    ('Show E05 720p', True),
    ('Show S03 1080p', False),
    ('Show S03E01 720p', False),
    ('Show S01 & S04 1080p', False),
    ('Show S03-S04 1080p', False),
    ('Шоу Сезон 3', False),
    ('Show Saison 1', False),
    ('Шоу Сезон 1', False),
    ('Show Temporada 1', False),
    ('Show Staffel 1', False),
])
def test_season_search(name, kept):
    assert name_matches(name, 2) is kept


@pytest.mark.parametrize('name, season, episode, kept', [
    ('Show S00E01 Special', 0, 1, True),
    ('Show S00E02 Special', 0, 1, False),
    ('Show S01E01 720p', 0, 1, False),
    ('Show Specials 720p', 0, 1, True),
    ('Show S00 720p', 0, None, True),
    ('Show S01 720p', 0, None, False),
    ('Show S01E00 Pilot', 1, 0, True),
    ('Show S01E01 720p', 1, 0, False),
])
def test_specials(name, season, episode, kept):
    assert name_matches(name, season, episode) is kept
