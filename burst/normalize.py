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
    :return: clean title
    :rtype: unicode
    """
    if string:
        string = re.sub(r'\((.*?)\)', u'', string).strip()

    return string


def are_equals(string_1='', string_2=''):
    """
        Checks if the two string are equals even without accents
    :param string_1: first string
    :type: string_1: unicode
    :param string_2: second string
    :type: string_2: unicode
    :return: True if it is equal, False otherwise
    :rtype: bool
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
    :return: string without accents
    :rtype: unicode
    """
    if not isinstance(string, unicode):
        string = normalize_string(string)

    nfkd_form = unicodedata.normalize('NFKD', string)
    only_ascii = nfkd_form.encode('ASCII', 'ignore').strip()
    return string if only_ascii == u'' else only_ascii


def remove_control_chars(string):
    """
        remove control characters
    :param string: string to modify
    :type string: unicode
    :return: modified string
    :rtype: unicode
    """
    control_chars = ''.join(map(unichr, range(0, 32) + range(127, 160)))
    control_char_re = re.compile(u'[%s]' % re.escape(control_chars))
    tem_string = control_char_re.sub('', string)
    control_char_re = re.compile(u'[%s]' % re.escape(unichr(160)))
    return control_char_re.sub(' ', tem_string)


def safe_name_torrent(string):
    """
        Make the name directory and filename safe
    :param string: string to modify
    :type string: unicode
    :return: modified string
    :rtype: unicode
    """
    # erase keyword
    string = string.lower()
    string = re.sub(u'^\[.*?\]', u'', string)  # erase [HorribleSub] for ex.
    # check for anime
    string = re.sub(u'- ([0-9][0-9][0-9][0-9]) ', u' \g<1>', string + u' ')
    string = re.sub(u'- ([0-9]+) ', u'- EP\g<1>', string + u' ')
    if 'season' not in string.lower():
        string = string.lower().replace(u' episode ', u' - EP')

    # check for qualities
    string = string.replace(u'1920x1080', u'1080p')
    string = string.replace(u'1280x720', u'720p')
    string = string.replace(u'853x480', u'480p')
    string = string.replace(u'848x480', u'480p')
    string = string.replace(u'704x480', u'480p')
    string = string.replace(u'640x480', u'480p')
    string = string.replace(u'microhd', u' microhd')  # sometimes comes with the year
    string = string.replace(u'dvdrip', u' dvdrip')  # sometimes comes with the year
    string = string.replace(u'1080p', u'')
    string = string.replace(u'720p', u'')
    string = string.replace(u'480p', u'')
    string = safe_name(string)
    return string.replace(u's h i e l d', u'SHIELD').replace(u'c s i', u'CSI')


def safe_name(string, charset='utf-8', replacing=False):
    """
    Make the name directory and filename safe
    :param charset: encoding
    :type charset: str
    :param string: string to convert
    :type string: str or unicode
    :param replacing: Whether is ' is replaced
    :type replacing: bool
    :return: converted string
    :rtype: unicode
    """
    string = normalize_string(string, charset, replacing)
    string = string.lower().title()
    keys = {u'*': u' ', u'/': u' ', u':': u' ', u'<': u' ', u'>': u' ', u'?': u' ', u'|': u' ', u'_': u' ',
            u'.': u' ', u')': u' ', u'(': u' ', u'[': u' ', u']': u' ', u'-': u' '}
    for key in keys.keys():
        string = string.replace(key, keys[key])

    string = re.sub(u' +', u' ', string)
    return string


def normalize_string(string, charset=None, replacing=False):
    """
    Decode and Convert to Unicode any string
    :param charset: encoding
    :type charset: str
    :param string: string to convert
    :type string: str or unicode
    :param replacing: Whether is ' is replaced
    :type replacing: bool
    :return: converted unicode
    :rtype: unicode
    """
    if not isinstance(string, unicode):
        try:
            if re.search(u'=[0-9a-fA-F]{2}', string):
                string = string.decode('Quoted-printable')

            string = json.loads(u'%s' % string, encoding=charset)

        except ValueError:
            try:
                string = unicode(eval(string), 'raw_unicode_escape')

            except (SyntaxError, NameError):
                string = string.decode('latin-1')
                pass

            except TypeError:
                string = unicode(string, errors='ignore')
                pass

        except LookupError:
            return u''

        except TypeError:
            string = unicode(string, errors='ignore')
            pass

    string = remove_control_chars(string)
    string = fix_bad_unicode(string)
    string = unquote(string)
    string = string.replace(u'<![CDATA[', u'').replace(u']]', u'')
    string = HTMLParser().unescape(string)
    if replacing:
        string = string.replace(u"'", '')

    string = string.lower()

    return string


def fix_bad_unicode(string):
    """
    https://blog.luminoso.com/2012/08/20/fix-unicode-mistakes-with-python/

    Something you will find all over the place, in real-world text, is text
    that's mistakenly encoded as utf-8, decoded in some ugly format like
    latin-1 or even Windows codepage 1252, and encoded as utf-8 again.

    This causes your perfectly good Unicode-aware code to end up with garbage
    text because someone else (or maybe 'someone else') made a mistake.

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
    if not isinstance(string, unicode):
        raise TypeError("This isn't even decoded into Unicode yet. "
                        'Decode it first.')
    if len(string) == 0:
        return string

    max_ord = max(ord(char) for char in string)
    if max_ord < 128:
        # Hooray! It's ASCII!
        return string

    else:
        attempts = [(string, text_badness(string) + len(string))]
        if max_ord < 256:
            tried_fixing = reinterpret_latin1_as_utf8(string)
            tried_fixing2 = reinterpret_latin1_as_windows1252(string)
            attempts.append((tried_fixing, text_cost(tried_fixing)))
            attempts.append((tried_fixing2, text_cost(tried_fixing2)))

        elif all(ord(char) in WINDOWS_1252_CODEPOINTS for char in string):
            tried_fixing = reinterpret_windows1252_as_utf8(string)
            attempts.append((tried_fixing, text_cost(tried_fixing)))

        else:
            # We can't imagine how this would be anything but valid text.
            return string

        # Sort the results by badness
        attempts.sort(key=lambda x: x[1])
        # print attempts
        good_text = attempts[0][0]
        if good_text == string:
            return good_text

        else:
            return fix_bad_unicode(good_text)


def reinterpret_latin1_as_utf8(wrong_text):
    new_bytes = wrong_text.encode('latin-1', 'replace')
    return new_bytes.decode('utf-8', 'replace')


def reinterpret_windows1252_as_utf8(wrong_text):
    """
        Maybe this was always meant to be in a single-byte encoding, and it
        makes the most sense in utf-8.
    :param wrong_text: text with problems
    :type: str or unicode
    :return: corrected text
    :rtype: str or unicode
    """
    altered_bytes = []
    for char in wrong_text:
        if ord(char) in WINDOWS_1252_GREMLINS:
            altered_bytes.append(char.encode('WINDOWS_1252'))

        else:
            altered_bytes.append(char.encode('latin-1', 'replace'))

    return ''.join(altered_bytes).decode('utf-8', 'replace')


def reinterpret_latin1_as_windows1252(wrong_text):
    """
        Maybe this was always meant to be in a single-byte encoding, and it
        makes the most sense in Windows-1252.
    :param wrong_text: text with problems
    :type: str or unicode
    :return: corrected text
    :rtype: str or unicode
    """
    return wrong_text.encode('latin-1').decode('WINDOWS_1252', 'replace')


def text_badness(text):
    """
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
# Start with an inventory of 'gremlins', which are characters from all over
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
# of '0' -- if you're going to write in Linear B using Unicode, you're
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
