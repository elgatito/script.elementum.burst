# coding: utf-8
# Name:        magnetic.py
# Author:      Mancuniancol
# Created on:  30.05.2017
# Licence:     GPL v.3: http://www.gnu.org/copyleft/gpl.html
"""
Normalization strings to Unicode
"""
import json
import re
import unicodedata
from HTMLParser import HTMLParser
from urllib import unquote


def clean_title(string=None):
    """
    Checks if the two string are equals even without accents
    :param string: first string
    :type: string: unicode
    :return: str
    """
    if string:
        string = re.sub(r'\((.*?)\)', '', string).strip()

    return string


def are_equals(string_1='', string_2=''):
    """
    Checks if the two string are equals even without accents
    :param string_1: first string
    :type: string_1: unicode
    :param string_2: second string
    :type: string_2: unicode
    :return:
    """
    string_1 = safe_name(string_1)
    string_2 = safe_name(string_2)
    string_a = remove_accents(string_1)
    string_b = remove_accents(string_2)
    return any([string_1 == string_2, string_a == string_b])


def remove_accents(string):
    """
    Remove any accent in the string
    :param string: string to remove accents
    :type string: str or unicode
    :return:
    """
    if not isinstance(string, unicode):
        string = normalize_string(string)

    nfkd_form = unicodedata.normalize('NFKD', string)
    only_ascii = nfkd_form.encode('ASCII', 'ignore').strip()
    return string if only_ascii == '' else only_ascii


def remove_control_chars(string):
    control_chars = ''.join(map(unichr, range(0, 32) + range(127, 160)))
    control_char_re = re.compile(u'[%s]' % re.escape(control_chars))
    tem_string = control_char_re.sub('', string)
    control_char_re = re.compile(u'[%s]' % re.escape(unichr(160)))
    return control_char_re.sub(' ', tem_string)


def safe_name_torrent(value):  # Make the name directory and filename safe
    # erase keyword
    value = value.lower()
    value = re.sub('^\[.*?\]', '', value)  # erase [HorribleSub] for ex.
    # check for anime
    value = re.sub('- ([0-9][0-9][0-9][0-9]) ', ' \g<1>', value + " ")
    value = re.sub('- ([0-9]+) ', '- EP\g<1>', value + " ")
    if 'season' not in value.lower():
        value = value.lower().replace(" episode ", " - EP")

    # check for qualities
    value = value.replace("1920x1080", "1080p")
    value = value.replace("1280x720", "720p")
    value = value.replace("853x480", "480p")
    value = value.replace("848x480", "480p")
    value = value.replace("704x480", "480p")
    value = value.replace("640x480", "480p")
    value = value.replace("microhd", " microhd")  # sometimes comes with the year
    value = value.replace("dvdrip", " dvdrip")  # sometimes comes with the year
    value = value.replace("1080p", "")
    value = value.replace("720p", "")
    value = value.replace("480p", "")
    value = safe_name(value)
    return value.replace('s h i e l d', 'SHIELD').replace('c s i', 'CSI')


def safe_name(string, charset='utf-8'):
    """
    Make the name directory and filename safe
    :param charset: encoding
    :type charset: str
    :param string: string to convert
    :type string: str or unicode
    :return: converted string
    """
    string = normalize_string(string, charset)
    string = string.lower().title()
    keys = {'"': ' ', '*': ' ', '/': ' ', ':': ' ', '<': ' ', '>': ' ', '?': ' ', '|': ' ', '_': ' ',
            "'": '', 'Of': 'of', 'De': 'de', '.': ' ', ')': ' ', '(': ' ', '[': ' ', ']': ' ', '-': ' '}
    for key in keys.keys():
        string = string.replace(key, keys[key])

    string = re.sub(u' +', u' ', string)
    return string


def normalize_string(string, charset=None):
    """
    Decode and Convert to Unicode any string
    :param charset: encoding
    :type charset: str
    :param string: string to convert
    :type string: str or unicode
    :return: converted unicode
    """
    if not isinstance(string, unicode):
        try:
            if re.search('=[0-9a-fA-F]{2}', string):
                string = string.decode('Quoted-printable')

            string = json.loads('"%s"' % string, encoding=charset)

        except ValueError:
            try:
                string = unicode(eval(string), "raw_unicode_escape")

            except SyntaxError:
                string = string.decode('latin-1')

            except TypeError:
                string = unicode(string, errors='ignore')

        except LookupError:
            return u''

        except TypeError:
            string = unicode(string, errors='ignore')

    string = remove_control_chars(string)
    string = fix_bad_unicode(string)
    string = unquote(string)
    string = string.replace('<![CDATA[', '').replace(']]', '')
    string = HTMLParser().unescape(string)
    return string


def fix_bad_unicode(text):
    """
    https://blog.luminoso.com/2012/08/20/fix-unicode-mistakes-with-python/

    Something you will find all over the place, in real-world text, is text
    that's mistakenly encoded as utf-8, decoded in some ugly format like
    latin-1 or even Windows codepage 1252, and encoded as utf-8 again.

    This causes your perfectly good Unicode-aware code to end up with garbage
    text because someone else (or maybe "someone else") made a mistake.

    This function looks for the evidence of that having happened and fixes it.
    It determines whether it should replace nonsense sequences of single-byte
    characters that were really meant to be UTF-8 characters, and if so, turns
    them into the correctly-encoded Unicode character that they were meant to
    represent.

    The input to the function must be Unicode. It's not going to try to
    auto-decode bytes for you -- then it would just create the problems it's
    supposed to fix.

        //>>> print fix_bad_unicode(u'Ãºnico')
        único

        //>>> print fix_bad_unicode(u'This text is fine already :þ')
        This text is fine already :þ

    Because these characters often come from Microsoft products, we allow
    for the possibility that we get not just Unicode characters 128-255, but
    also Windows's conflicting idea of what characters 128-160 are.

        //>>> print fix_bad_unicode(u'This â€” should be an em dash')
        This — should be an em dash

    We might have to deal with both Windows characters and raw control
    characters at the same time, especially when dealing with characters like
    \x81 that have no mapping in Windows.

        //>>> print fix_bad_unicode(u'This text is sad .â\x81”.')
        This text is sad .?.

    This function even fixes multiple levels of badness:

        //>>> wtf = u'\xc3\xa0\xc2\xb2\xc2\xa0_\xc3\xa0\xc2\xb2\xc2\xa0'
        //>>> print fix_bad_unicode(wtf)
        ?_?

    However, it has safeguards against fixing sequences of letters and
    punctuation that can occur in valid text:

        //>>> print fix_bad_unicode(u'not such a fan of Charlotte Brontë…”')
        not such a fan of Charlotte Brontë…”

    Cases of genuine ambiguity can sometimes be addressed by finding other
    characters that are not double-encoding, and expecting the encoding to
    be consistent:

        //>>> print fix_bad_unicode(u'AHÅ™, the new sofa from IKEA®')
        AHÅ™, the new sofa from IKEA®

    Finally, we handle the case where the text is in a single-byte encoding
    that was intended as Windows-1252 all along but read as Latin-1:

        //>>> print fix_bad_unicode(u'This text was never Unicode at all\x85')
        This text was never Unicode at all…
    """
    if not isinstance(text, unicode):
        raise TypeError("This isn't even decoded into Unicode yet. "
                        "Decode it first.")
    if len(text) == 0:
        return text

    max_ord = max(ord(char) for char in text)
    if max_ord < 128:
        # Hooray! It's ASCII!
        return text

    else:
        attempts = [(text, text_badness(text) + len(text))]
        if max_ord < 256:
            tried_fixing = reinterpret_latin1_as_utf8(text)
            tried_fixing2 = reinterpret_latin1_as_windows1252(text)
            attempts.append((tried_fixing, text_cost(tried_fixing)))
            attempts.append((tried_fixing2, text_cost(tried_fixing2)))

        elif all(ord(char) in WINDOWS_1252_CODEPOINTS for char in text):
            tried_fixing = reinterpret_windows1252_as_utf8(text)
            attempts.append((tried_fixing, text_cost(tried_fixing)))

        else:
            # We can't imagine how this would be anything but valid text.
            return text

        # Sort the results by badness
        attempts.sort(key=lambda x: x[1])
        # print attempts
        good_text = attempts[0][0]
        if good_text == text:
            return good_text

        else:
            return fix_bad_unicode(good_text)


def reinterpret_latin1_as_utf8(wrong_text):
    new_bytes = wrong_text.encode('latin-1', 'replace')
    return new_bytes.decode('utf-8', 'replace')


def reinterpret_windows1252_as_utf8(wrong_text):
    altered_bytes = []
    for char in wrong_text:
        if ord(char) in WINDOWS_1252_GREMLINS:
            altered_bytes.append(char.encode('WINDOWS_1252'))

        else:
            altered_bytes.append(char.encode('latin-1', 'replace'))

    return ''.join(altered_bytes).decode('utf-8', 'replace')


def reinterpret_latin1_as_windows1252(wrongtext):
    """
    Maybe this was always meant to be in a single-byte encoding, and it
    makes the most sense in Windows-1252.
    """
    return wrongtext.encode('latin-1').decode('WINDOWS_1252', 'replace')


def text_badness(text):
    """"
    Look for red flags that text is encoded incorrectly:

    Obvious problems:
    - The replacement character \ufffd, indicating a decoding error
    - Unassigned or private-use Unicode characters

    Very weird things:
    - Adjacent letters from two different scripts
    - Letters in scripts that are very rarely used on computers (and
      therefore, someone who is using them will probably get Unicode right)
    - Improbable control characters, such as 0x81

    Moderately weird things:
    - Improbable single-byte characters, such as ƒ or ¬
    - Letters in somewhat rare scripts
    """
    assert isinstance(text, unicode)
    errors = 0
    very_weird_things = 0
    weird_things = 0
    prev_letter_script = None
    for pos in xrange(len(text)):
        char = text[pos]
        index = ord(char)
        if index < 256:
            # Deal quickly with the first 256 characters.
            weird_things += SINGLE_BYTE_WEIRDNESS[index]

            if SINGLE_BYTE_LETTERS[index]:
                prev_letter_script = 'latin'

            else:
                prev_letter_script = None

        else:
            category = unicodedata.category(char)
            if category == 'Co':
                # Unassigned or private use
                errors += 1

            elif index == 0xfffd:
                # Replacement character
                errors += 1

            elif index in WINDOWS_1252_GREMLINS:
                low_char = char.encode('WINDOWS_1252').decode('latin-1')
                weird_things += SINGLE_BYTE_WEIRDNESS[ord(low_char)] - 0.5

            if category.startswith('L'):
                # It's a letter. What kind of letter? This is typically found
                # in the first word of the letter's Unicode name.
                name = unicodedata.name(char)
                script_name = name.split()[0]
                freq, script = SCRIPT_TABLE.get(script_name, (0, 'other'))
                if prev_letter_script:
                    if script != prev_letter_script:
                        very_weird_things += 1

                    if freq == 1:
                        weird_things += 2

                    elif freq == 0:
                        very_weird_things += 1

                prev_letter_script = script

            else:
                prev_letter_script = None

    return 100 * errors + 10 * very_weird_things + weird_things


def text_cost(text):
    """
    Assign a cost function to the length plus weirdness of a text string.
    """
    return text_badness(text) + len(text)


#######################################################################
# The rest of this file is esoteric info about characters, scripts, and their
# frequencies.
#
# Start with an inventory of "gremlins", which are characters from all over
# Unicode that Windows has instead assigned to the control characters
# 0x80-0x9F. We might encounter them in their Unicode forms and have to figure
# out what they were originally.

WINDOWS_1252_GREMLINS = [
    # adapted from http://effbot.org/zone/unicode-gremlins.htm
    0x0152,  # LATIN CAPITAL LIGATURE OE
    0x0153,  # LATIN SMALL LIGATURE OE
    0x0160,  # LATIN CAPITAL LETTER S WITH CARON
    0x0161,  # LATIN SMALL LETTER S WITH CARON
    0x0178,  # LATIN CAPITAL LETTER Y WITH DIAERESIS
    0x017E,  # LATIN SMALL LETTER Z WITH CARON
    0x017D,  # LATIN CAPITAL LETTER Z WITH CARON
    0x0192,  # LATIN SMALL LETTER F WITH HOOK
    0x02C6,  # MODIFIER LETTER CIRCUMFLEX ACCENT
    0x02DC,  # SMALL TILDE
    0x2013,  # EN DASH
    0x2014,  # EM DASH
    0x201A,  # SINGLE LOW-9 QUOTATION MARK
    0x201C,  # LEFT DOUBLE QUOTATION MARK
    0x201D,  # RIGHT DOUBLE QUOTATION MARK
    0x201E,  # DOUBLE LOW-9 QUOTATION MARK
    0x2018,  # LEFT SINGLE QUOTATION MARK
    0x2019,  # RIGHT SINGLE QUOTATION MARK
    0x2020,  # DAGGER
    0x2021,  # DOUBLE DAGGER
    0x2022,  # BULLET
    0x2026,  # HORIZONTAL ELLIPSIS
    0x2030,  # PER MILLE SIGN
    0x2039,  # SINGLE LEFT-POINTING ANGLE QUOTATION MARK
    0x203A,  # SINGLE RIGHT-POINTING ANGLE QUOTATION MARK
    0x20AC,  # EURO SIGN
    0x2122,  # TRADE MARK SIGN
]

# a list of Unicode characters that might appear in Windows-1252 text
WINDOWS_1252_CODEPOINTS = range(256) + WINDOWS_1252_GREMLINS

# Rank the characters typically represented by a single byte -- that is, in
# Latin-1 or Windows-1252 -- by how weird it would be to see them in running
# text.
#
#   0 = not weird at all
#   1 = rare punctuation or rare letter that someone could certainly
#       have a good reason to use. All Windows-1252 gremlins are at least
#       weirdness 1.
#   2 = things that probably don't appear next to letters or other
#       symbols, such as math or currency symbols
#   3 = obscure symbols that nobody would go out of their way to use
#       (includes symbols that were replaced in ISO-8859-15)
#   4 = why would you use this?
#   5 = unprintable control character
#
# The Portuguese letter Ã (0xc3) is marked as weird because it would usually
# appear in the middle of a word in actual Portuguese, and meanwhile it
# appears in the mis-encodings of many common characters.

SINGLE_BYTE_WEIRDNESS = (
    #   0  1  2  3  4  5  6  7  8  9  a  b  c  d  e  f
    5, 5, 5, 5, 5, 5, 5, 5, 5, 0, 0, 5, 5, 5, 5, 5,  # 0x00
    5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5,  # 0x10
    0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  # 0x20
    0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  # 0x30
    0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  # 0x40
    0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  # 0x50
    0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  # 0x60
    0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 5,  # 0x70
    2, 5, 1, 4, 1, 1, 3, 3, 4, 3, 1, 1, 1, 5, 1, 5,  # 0x80
    5, 1, 1, 1, 1, 3, 1, 1, 4, 1, 1, 1, 1, 5, 1, 1,  # 0x90
    1, 0, 2, 2, 3, 2, 4, 2, 4, 2, 2, 0, 3, 1, 1, 4,  # 0xa0
    2, 2, 3, 3, 4, 3, 3, 2, 4, 4, 4, 0, 3, 3, 3, 0,  # 0xb0
    0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  # 0xc0
    1, 0, 0, 0, 0, 0, 0, 2, 0, 0, 0, 0, 0, 0, 0, 0,  # 0xd0
    0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  # 0xe0
    1, 0, 0, 0, 0, 0, 0, 2, 0, 0, 0, 0, 0, 0, 0, 0,  # 0xf0
)

# Pre-cache the Unicode data saying which of these first 256 characters are
# letters. We'll need it often.
SINGLE_BYTE_LETTERS = [
    unicodedata.category(unichr(i)).startswith('L')
    for i in xrange(256)
]

# A table telling us how to interpret the first word of a letter's Unicode
# name. The number indicates how frequently we expect this script to be used
# on computers. Many scripts not included here are assumed to have a frequency
# of "0" -- if you're going to write in Linear B using Unicode, you're
# probably aware enough of encoding issues to get it right.
#
# The lowercase name is a general category -- for example, Han characters and
# Hiragana characters are very frequently adjacent in Japanese, so they all go
# into category 'cjk'. Letters of different categories are assumed not to
# appear next to each other often.
SCRIPT_TABLE = {
    'LATIN': (3, 'latin'),
    'CJK': (2, 'cjk'),
    'ARABIC': (2, 'arabic'),
    'CYRILLIC': (2, 'cyrillic'),
    'GREEK': (2, 'greek'),
    'HEBREW': (2, 'hebrew'),
    'KATAKANA': (2, 'cjk'),
    'HIRAGANA': (2, 'cjk'),
    'HIRAGANA-KATAKANA': (2, 'cjk'),
    'HANGUL': (2, 'cjk'),
    'DEVANAGARI': (2, 'devanagari'),
    'THAI': (2, 'thai'),
    'FULLWIDTH': (2, 'cjk'),
    'MODIFIER': (2, None),
    'HALFWIDTH': (1, 'cjk'),
    'BENGALI': (1, 'bengali'),
    'LAO': (1, 'lao'),
    'KHMER': (1, 'khmer'),
    'TELUGU': (1, 'telugu'),
    'MALAYALAM': (1, 'malayalam'),
    'SINHALA': (1, 'sinhala'),
    'TAMIL': (1, 'tamil'),
    'GEORGIAN': (1, 'georgian'),
    'ARMENIAN': (1, 'armenian'),
    'KANNADA': (1, 'kannada'),  # mostly used for looks of disapproval
    'MASCULINE': (1, 'latin'),
    'FEMININE': (1, 'latin')
}


def cleaning_title(value=''):
    """
    Removes extra words in the title
    :param value: title
    :type value: unicode
    :return:
    """
    keywords_clean_title = ['version', 'extendida', 'extended', 'edition', 'hd', 'unrated', 'version', 'vose',
                            'special', 'edtion', 'uncensored', 'fixed', 'censurada', 'episode', 'ova', 'complete',
                            'swesub'
                            ]
    for keyword in keywords_clean_title:  # checking keywords
        value = (value + ' ').replace(' ' + keyword.title() + ' ', ' ')
    return value.strip()


def exceptions_title(title=''):
    """
    Changes title to which uses in Internet
    :param title: title
    :type title: unicode
    :return:
    """
    value = title.lower() + " "
    if "csi " in value and "ny" not in value and "miami" not in value and "cyber" not in value:
        title = value.replace("csi", "CSI Crime Scene Investigation")

    if "juego de tronos" in value:
        title = value.replace("juego de tronos", "Game of Thrones")

    if "mentes criminales" in value:
        title = value.replace("mentes criminales", "Criminal Minds")

    if "les revenants" in value:
        title = value.replace("les revenants", "The Returned")

    if "the great british baking show" in value:
        title = value.replace("the great british baking show", "The Great British Bake Off")

    if "house of cards" in value and '[us]' in value in value:
        title = value.replace("[us]", "")

    if "house of cards" in value and '(us)' in value in value:
        title = value.replace("(us)", "")

    if "house of cards" in value and ' us ' in value in value:
        title = value.replace(" us ", "")

    return title


# noinspection PyPep8,PyBroadException
def formatting_title(value='', type_video="MOVIE"):
    """
    Parsers the title from string
    :param value:
    :type value: str or unicode
    :param type_video: type of video
    :return:
    """
    pos = value.rfind("/")
    value = value if pos < 0 else value[pos:]
    value = safe_name_torrent(value).lower() + ' '
    formats = [' ep[0-9]+', ' s[0-9]+e[0-9]+', ' s[0-9]+ e[0-9]+', ' [0-9]+x[0-9]+',
               ' [0-9][0-9][0-9][0-9] [0-9][0-9] [0-9][0-9]',
               ' [0-9][0-9] [0-9][0-9] [0-9][0-9]', ' season [0-9]+ episode [0-9]+',
               ' season [0-9]+', ' season[0-9]+', ' s[0-9][0-9]',
               ' temporada [0-9]+ capitulo [0-9]+', ' temporada[0-9]+', ' temporada [0-9]+',
               ' seizoen [0-9]+ afl [0-9]+', ' saison[0-9]+', ' saison [0-9]+',
               ' temp [0-9]+ cap [0-9]+', ' temp[0-9]+ cap[0-9]+',
               ]
    keywords = ['en 1080p', 'en 720p', 'en dvd', 'en dvdrip', 'en hdtv', 'en bluray', 'en blurayrip',
                'en web', 'en rip', 'en ts screener', 'en screener', 'en cam', 'en camrip', 'pcdvd', 'bdremux',
                'en ts-screener', 'en hdrip', 'en microhd', '1080p', '720p', 'dvd', 'dvdrip', 'hdtv', 'bluray',
                'blurayrip', 'web', 'rip', 'ts screener', 'screener', 'cam', 'camrip', 'ts-screener', 'hdrip',
                'brrip', 'blu', 'webrip', 'hdrip', 'bdrip', 'microhd', 'ita', 'eng', 'esp', "spanish espanol",
                'castellano', '480p', 'bd', 'bdrip', 'hi10p', 'sub', 'x264', 'sbs', '3d', 'br', 'hdts', 'dts',
                'dual audio', 'hevc', 'aac', 'batch', 'h264', 'gratis', 'descargar', 'hd', 'html', 'hdit',
                'blurip', 'high definition', 'german', 'french', 'truefrench', 'vostfr', 'dvdscr', 'swesub',
                '4k', 'uhd', 'subbed', 'mp4'
                ]
    s_show = None
    for f_format in formats:  # search if it is a show
        s_show = re.search(f_format, value)  # format shows
        if s_show is not None:
            break

    if s_show is None and type_video != "MOVIE":
        if type_video == 'SHOW':
            value += ' s00e00'

        if type_video == 'ANIME':
            value += ' ep00'

        for f_format in formats:  # search if it is a show
            s_show = re.search(f_format, value)  # format shows
            if s_show is not None:
                break

    if s_show is None:
        # it is a movie
        value += ' 0000 '  # checking year
        s_year = re.search(' [0-9][0-9][0-9][0-9] ', value)
        year = s_year.group(0).strip()
        pos = value.find(year)
        if pos > 0:
            title = value[:pos].strip()
            rest = value[pos + 5:].strip().replace('0000', '')

        else:
            title = value.replace('0000', '')
            rest = ''

        while pos != -1:  # loop until doesn't have any keyword in the title
            value = title + ' '
            for keyword in keywords:  # checking keywords
                pos = value.find(' ' + keyword + ' ')
                if pos > 0:
                    title = value[:pos]
                    rest = value[pos:].strip() + ' ' + rest
                    break

        title = title.title().strip().replace('Of ', 'of ').replace('De ', 'de ')
        clean_title_value = cleaning_title(title)
        # finishing clean_title
        if '0000' not in year:
            title += ' (' + year.strip() + ')'
        year = year.replace('0000', '')
        folder = title
        result = {'title': title, 'folder': folder, 'rest': rest.strip(), 'type': 'MOVIE',
                  'clean_title': clean_title_value,
                  'year': year
                  }
        return result

    else:
        # it is a show
        rest = value.strip()  # original name
        season_episode = s_show.group(0)
        # clean title
        for keyword in keywords:  # checking keywords
            value = value.replace(' ' + keyword + ' ', ' ')

        title = value[:value.find(season_episode)].strip()
        title = title.strip()
        season_episode = season_episode.replace('temporada ', 's').replace(' capitulo ', 'e')
        season_episode = season_episode.replace('season ', 's').replace(' episode ', 'e')
        season_episode = season_episode.replace('temp ', 's').replace(' cap ', 'e')
        season_episode = season_episode.replace('seizoen ', 's').replace(' afl ', 'e')

        if 'x' in season_episode:
            season_episode = 's' + season_episode.replace('x', 'e')

        # force S00E00 instead S0E0
        if 's' in season_episode and 'e' in season_episode and 'season' not in season_episode:
            temp_episode = season_episode.replace('s', '').split('e')
            season_episode = 's%02de%02d' % (int(temp_episode[0]), int(temp_episode[1]))

        if 's' not in season_episode and 'e' not in season_episode:  # date format
            date = season_episode.split()
            if len(date[0]) == 4:  # yyyy-mm-dd format
                season_episode = season_episode.replace(' ', '-')  # date style episode talk shows

            else:  # dd mm yy format
                if int(date[2]) > 50:
                    date[2] = '19' + date[2]

                else:
                    date[2] = '20' + date[2]
                season_episode = date[2] + '-' + date[1] + '-' + date[0]

        season_episode = season_episode.replace(' ', '')  # remove spaces in the episode format
        title = exceptions_title(title)
        # finding year
        value = title + ' 0000 '
        s_year = re.search(' [0-9][0-9][0-9][0-9] ', value)
        year = s_year.group(0).strip()
        pos = value.find(year)
        if pos > 0:
            title = value[:pos].strip()

        else:
            title = value.replace('0000', '')

        year = year.replace('0000', '')
        # the rest
        title = title.title().strip().replace('Of ', 'of ').replace('De ', 'de ')
        folder = title  # with year
        clean_title_value = cleaning_title(title.replace(year, '').strip())  # without year
        title = folder + ' ' + season_episode.upper()
        title = title.replace('S00E00', '').replace('EP00', '')
        t_type = "SHOW"
        result = {'title': title, 'folder': folder, 'rest': rest, 'type': t_type, 'clean_title': clean_title_value,
                  'year': year
                  }
        if bool(re.search("EP[0-9]+", title)):
            result['type'] = "ANIME"
            result['season'] = 1
            result['episode'] = int(season_episode.replace('ep', ''))

        else:
            temp = (season_episode.replace('s', '')).split('e')
            result['season'] = 0
            result['episode'] = 0
            try:
                result['season'] = int(temp[0])
                result['episode'] = int(temp[1])

            except:
                pass

        return result
