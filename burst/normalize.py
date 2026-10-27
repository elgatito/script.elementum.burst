# coding: utf-8
# Name:        magnetic.py
# Author:      Mancuniancol
# Created on:  30.05.2017
# Licence:     GPL v.3: http://www.gnu.org/copyleft/gpl.html
"""
    Normalization strings to Unicode
"""

import re
import html
import unicodedata
from urllib.parse import unquote


def remove_accents(string):
    """
        Remove any accent in the string
    :param string: string to remove accents
    :type string: str
    :return: string without accents
    :rtype: str
    """
    nfkd_form = unicodedata.normalize('NFKD', string)
    return "".join([c for c in nfkd_form if not unicodedata.combining(c)])


CONTROL_CHARS_RE = re.compile('[%s]' % re.escape(''.join(map(chr, list(range(0, 32)) + list(range(127, 160))))))
NBSP_RE = re.compile('[%s]' % re.escape(chr(160)))


def remove_control_chars(string):
    """
        remove control characters
    :param string: string to modify
    :type string: str
    :return: modified string
    :rtype: str
    """
    return NBSP_RE.sub(' ', CONTROL_CHARS_RE.sub('', string))


def normalize_string(string, replacing=False):
    """
    Decode and Convert to Unicode any string
    :param string: string to convert
    :type string: str or bytes
    :param replacing: Whether is ' is replaced
    :type replacing: bool
    :return: converted string
    :rtype: str
    """
    if isinstance(string, bytes):
        string = string.decode('utf-8', 'ignore')
    elif not isinstance(string, str):
        string = str(string)

    string = remove_control_chars(string)
    string = unquote(string)
    string = string.replace('<![CDATA[', '').replace(']]', '')
    string = html.unescape(string)

    if replacing:
        string = string.replace("'", '')

    return string.lower()
