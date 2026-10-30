# -*- coding: utf-8 -*-

"""
Burst season and episode numbers in torrent names
"""

import re

# Not after / not before a letter or digit; unlike \b, "_" counts as a separator
_START = r'(?<![^\W_])'
_END = r'(?![^\W_])'
_SEP = r'[ ._]*'
_RANGES = ('-', '~', 'to', 'thru', 'through')
_SEPARATOR = r'(-|~|&|,|\+|(?:to|thru|through|and)' + _END + ')'
_SEASON_WORD = r'(?:seasons?|saisons?|temporadas?|staffeln?|stagion[ei]|sezon[aiy]?|сезон[аиы]?)'
_EPISODE_WORD = r'(?:episodes?|episodios?|episódios?|épisodes?|folgen?|odcinek|odcinki|epizod[aey]?|capitulos?|capítulos?|серия|серии|серія|серії|эпизод[аы]?|епізод[иі]?)'
_SXXEYY = r's(\d{1,2})[ ._-]*(?:ep?|episode)[ ._-]*(\d{1,3})(?!\d)'
_NXYY = r'(\d{1,2})x(\d{2,3})' + _END

# S02E09, S02 EP09, S02.Episode.9, 2x09
EPISODE_RX = re.compile(_START + '(?:' + _SXXEYY + '|' + _NXYY + ')')
# What continues an episode: -S02E10, -2x10, -E10, -10 or & E10 after a range or list separator, or E10 right after it
NEXT_EPISODE_RX = re.compile('(?:' + _SEP + _SEPARATOR + _SEP + '(?:' + _SXXEYY + '|' + _NXYY + '|(?:ep?|episode)?' + _SEP + r'(\d{1,3})' + _END + r')|[ ._-]*e(\d{1,3})(?!\d))')
# S02, Season 2, Saison 2, Сезон 2
SEASON_RX = re.compile(_START + '(?:s|' + _SEASON_WORD + r'[ ._:-]*)(\d{1,2})' + _END)
NEXT_SEASON_RX = re.compile(_SEP + _SEPARATOR + _SEP + '(?:s|' + _SEASON_WORD + r'[ ._:-]*)?(\d{1,2})' + _END)
# 2 сезон, 2-й сезон, 1-4 сезоны; not "2 сезона", which counts seasons
SEASON_BEFORE_RX = re.compile(_START + r'(\d{1,2})(?:' + _SEP + '-' + _SEP + r'(\d{1,2})' + _SEP + 'сезон[ыи]|(?:-?(?:й|ый|ий|ой))?' + _SEP + 'сезон(?![а-яё]))')
# E05, Ep 5, Episode 5, Серии 1-10
BARE_EPISODE_RX = re.compile(_START + '(?:e|ep[ ._-]*|' + _EPISODE_WORD + r'[ ._:-]*)(\d{1,3})' + _END)
NEXT_BARE_EPISODE_RX = re.compile(_SEP + _SEPARATOR + _SEP + '(?:e|ep[ ._-]*|' + _EPISODE_WORD + r'[ ._:-]*)?(\d{1,3})' + _END)
DASHES_RX = re.compile('[\u2010-\u2015\u2212]')
CYRILLIC_X_RX = re.compile(r'(?<=\d)х(?=\d)')


def _ranges(text, first_rx, next_rx, value):
    """ Collects the inclusive ranges that ``first_rx`` and the ``next_rx`` matches right after it name, and blanks them in ``text``

    Args:
        text      (str): Text to search
        first_rx   (re): Pattern of the first number
        next_rx    (re): Pattern of a range or list separator and the next number
        value (function): Returns the number of a match, given the previous number

    Returns:
        tuple: ``(ranges, text)``: list of ``[first, last]`` ranges, and the text with the matches replaced by spaces
    """
    ranges = []
    match = first_rx.search(text)
    while match:
        last = value(match, None)
        ranges.append([last, last])
        end = match.end()
        follow = next_rx.match(text, end)
        while follow:
            current = value(follow, last)
            if follow.group(1) in _RANGES:
                if current < last:
                    break
                ranges[-1][1] = current
            else:
                ranges.append([current, current])
            last = current
            end = follow.end()
            follow = next_rx.match(text, end)
        text = text[:match.start()] + ' ' * (end - match.start()) + text[end:]
        match = first_rx.search(text, end)
    return ranges, text


def _episode(match, last):
    """ Season and episode of an ``EPISODE_RX`` or ``NEXT_EPISODE_RX`` match; a bare episode number keeps the previous season """
    groups = match.groups()
    if last is not None:
        groups = groups[1:]
    if groups[0] or groups[2]:
        return int(groups[0] or groups[2]), int(groups[1] or groups[3])
    return last[0], int(groups[4] or groups[5])


def _number(match, last):
    """ The number of a season or bare episode match """
    return int(match.group(match.lastindex))


def parse(name):
    """ Finds the seasons and episodes that a torrent name is for

    Args:
        name (str): Torrent name

    Returns:
        tuple: ``(episodes, seasons, bare)``, lists of inclusive ``[first, last]`` ranges: ``(season, episode)`` pairs
        from SxxEyy and NxYY, seasons named without an episode (S02, Season 2), and episodes named without a
        season (E05, Episode 5)
    """
    text = CYRILLIC_X_RX.sub('x', DASHES_RX.sub('-', name.lower()))
    episodes, text = _ranges(text, EPISODE_RX, NEXT_EPISODE_RX, _episode)

    seasons = []
    for match in SEASON_BEFORE_RX.finditer(text):
        first = int(match.group(1))
        seasons.append([first, max(first, int(match.group(2) or first))])
    text = SEASON_BEFORE_RX.sub(lambda match: ' ' * len(match.group(0)), text)
    more_seasons, text = _ranges(text, SEASON_RX, NEXT_SEASON_RX, _number)
    seasons += more_seasons

    bare, text = _ranges(text, BARE_EPISODE_RX, NEXT_BARE_EPISODE_RX, _number)
    return episodes, seasons, bare


def name_matches(name, season, episode=None):
    """ Checks that a torrent name is for a season, and for an episode of it when ``episode`` is given

    Ranges count (``S02E08-S02E10``, ``S01E01-S04E10``, ``S02E08E09E10``, ``S01-S04``, ``Season 1 through 4``), and
    ``&``, ``and``, ``,`` and ``+`` list seasons or episodes (``S01 & S04`` is seasons 1 and 4). A season named without
    an episode (``S02``, ``Season 2``, ``Сезон 2``) is a pack of all its episodes, unless the name also states which
    episodes it has (``Season 2 Episode 5``, ``S02 1080p E05``, ``Сезон 2 / Серии 1-10``). ``S02-09`` is seasons 2 to 9,
    the usual name of a multi-season pack. Season and episode 0 (specials) are checked like the others.

    A name without season or episode numbers (``Complete Series``) is kept, and so is a notation this does not know,
    such as absolute episode numbers or season words in languages other than English, French, Spanish, Portuguese,
    German, Italian, Polish, Croatian/Serbian, Russian and Ukrainian.

    Args:
        name    (str): Torrent name
        season  (int): Searched season
        episode (int): Searched episode, or ``None`` for a season search

    Returns:
        bool: ``False`` if the name is for another season or episode, ``True`` otherwise
    """
    episodes, seasons, bare = parse(name)
    if episode is None:
        if episodes or seasons:
            return any(first[0] <= season <= last[0] for first, last in episodes) or any(first <= season <= last for first, last in seasons)
        return True

    if any(first <= (season, episode) <= last for first, last in episodes):
        return True
    if any(first <= season <= last for first, last in seasons):
        return not bare or any(first <= episode <= last for first, last in bare)
    if episodes or seasons:
        return False
    return not bare or any(first <= episode <= last for first, last in bare)
