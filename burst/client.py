# -*- coding: utf-8 -*-

"""
Burst web client
"""

import os
import re
import sys
import json
import urllib2
from time import sleep
from urlparse import urlparse
from contextlib import closing
from quasar.provider import log
from cookielib import Cookie, LWPCookieJar
from urllib import urlencode
from utils import encode_dict

from xbmc import translatePath


USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 " \
             "(KHTML, like Gecko) Chrome/53.0.2785.21 Safari/537.36"
try:
    PATH_TEMP = translatePath("special://temp").decode(sys.getfilesystemencoding(), 'ignore')
except:
    PATH_TEMP = translatePath("special://temp").decode('utf-8')


class Client:
    """
    Web client class with automatic charset detection and decoding
    """
    def __init__(self):
        self._counter = 0
        self._cookies_filename = ''
        self._cookies = LWPCookieJar()
        self.user_agent = USER_AGENT
        self.clearance = None
        self.content = None
        self.status = None
        self.token = None
        self.passkey = None
        self.headers = dict()

    def _create_cookies(self, payload):
        return urlencode(payload)

    def _read_cookies(self, url=''):
        cookies_path = os.path.join(PATH_TEMP, 'burst')
        if not os.path.exists(cookies_path):
            try:
                os.makedirs(cookies_path)
            except Exception as e:
                log.debug("Error creating cookies directory: %s" % repr(e))
        self._cookies_filename = os.path.join(cookies_path, urlparse(url).netloc + '_cookies.jar')
        if os.path.exists(self._cookies_filename):
            try:
                self._cookies.load(self._cookies_filename)
            except Exception as e:
                log.debug("Reading cookies error: %s" % repr(e))

        # Check for cf_clearance cookie
        # https://github.com/scakemyer/cloudhole-api
        if self.clearance and not any(cookie.name == 'cf_clearance' for cookie in self._cookies):
            c = Cookie(version=None,
                       name='cf_clearance',
                       value=self.clearance[13:],
                       port=None,
                       port_specified=False,
                       domain='.{uri.netloc}'.format(uri=urlparse(url)),
                       domain_specified=True,
                       domain_initial_dot=True,
                       path='/',
                       path_specified=True,
                       secure=False,
                       expires=None,
                       discard=False,
                       comment=None,
                       comment_url=None,
                       rest=None,
                       rfc2109=False)
            self._cookies.set_cookie(c)

    def _save_cookies(self):
        try:
            self._cookies.save(self._cookies_filename)
        except Exception as e:
            log.debug("Saving cookies error: %s" % repr(e))

    def _good_spider(self):
        self._counter += 1
        if self._counter > 1:
            sleep(0.25)

    def cookies(self):
        """ Saved client cookies

        Returns:
            list: A list of saved Cookie objects
        """
        return self._cookies

    def open(self, url, language='en', post_data=None, get_data=None):
        """ Opens a connection to a webpage and saves its HTML content in ``self.content``

        Args:
            url        (str): The URL to open
            language   (str): The language code for the ``Content-Language`` header
            post_data (dict): POST data for the request
            get_data  (dict): GET data for the request
        """
        if not post_data:
            post_data = {}
        if get_data:
            url += '?' + urlencode(get_data)

        log.debug("Opening URL: %s" % repr(url))
        result = False

        data = urlencode(post_data) if len(post_data) > 0 else None
        req = urllib2.Request(url, data)

        self._read_cookies(url)
        log.debug("Cookies for %s: %s" % (repr(url), repr(self._cookies)))

        opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(self._cookies))
        req.add_header('User-Agent', self.user_agent)
        req.add_header('Content-Language', language)
        req.add_header("Accept-Encoding", "gzip")
        if self.token:
            req.add_header("Authorization", self.token)

        try:
            self._good_spider()
            with closing(opener.open(req)) as response:
                self.headers = response.headers
                self._save_cookies()
                if response.headers.get("Content-Encoding", "") == "gzip":
                    import zlib
                    self.content = zlib.decompressobj(16 + zlib.MAX_WBITS).decompress(response.read())
                else:
                    self.content = response.read()

                charset = response.headers.getparam('charset')

                if not charset:
                    match = re.search("""<meta(?!\s*(?:name|value)\s*=)[^>]*?charset\s*=[\s"']*([^\s"'/>]*)""", self.content)
                    if match:
                        charset = match.group(1)

                if charset and charset.lower() == 'utf-8':
                    charset = 'utf-8-sig'  # Changing to utf-8-sig to remove BOM if found on decode from utf-8

                if charset:
                    log.debug('Decoding charset from %s for %s' % (charset, repr(url)))
                    self.content = self.content.decode(charset, 'replace')

                self.status = response.getcode()
            result = True

        except urllib2.HTTPError as e:
            self.status = e.code
            log.warning("Status for %s : %s" % (repr(url), str(self.status)))
            if e.code == 403 or e.code == 503:
                log.warning("CloudFlared at %s, try enabling CloudHole" % url)

        except urllib2.URLError as e:
            self.status = repr(e.reason)
            log.warning("Status for %s : %s" % (repr(url), self.status))

        except Exception as e:
            import traceback
            log.error("%s failed with %s:" % (repr(url), repr(e)))
            map(log.debug, traceback.format_exc().split("\n"))

        log.debug("Status for %s : %s" % (repr(url), str(self.status)))

        return result

    def login(self, url, data, fails_with):
        """ Login wrapper around ``open``

        Args:
            url        (str): The URL to open
            data      (dict): POST login data
            fails_with (str): String that must **not** be included in the response's content

        Returns:
            bool: Whether or not login was successful
        """
        result = False
        if self.open(url.encode('utf-8'), post_data=encode_dict(data)):
            result = True
            if fails_with in self.content:
                self.status = 'Wrong username or password'
                result = False
        return result


def get_cloudhole_key():
    """ CloudHole API key fetcher

    Returns:
        str: A CloudHole API key
    """
    cloudhole_key = None
    try:
        r = urllib2.Request("https://cloudhole.herokuapp.com/key")
        r.add_header('Content-type', 'application/json')
        with closing(urllib2.urlopen(r)) as response:
            content = response.read()
        log.info("CloudHole key: %s" % content)
        data = json.loads(content)
        cloudhole_key = data['key']
    except Exception as e:
        log.error("Getting CloudHole key error: %s" % repr(e))
    return cloudhole_key


def get_cloudhole_clearance(cloudhole_key):
    """ CloudHole clearance fetcher

    Args:
        cloudhole_key (str): The CloudHole API key saved in settings or from ``get_cloudhole_key`` directly
    Returns:
        tuple: A CloudHole clearance cookie and user-agent string
    """
    user_agent = USER_AGENT
    clearance = None
    if cloudhole_key:
        try:
            r = urllib2.Request("https://cloudhole.herokuapp.com/clearances")
            r.add_header('Content-type', 'application/json')
            r.add_header('Authorization', cloudhole_key)
            with closing(urllib2.urlopen(r)) as response:
                content = response.read()
            log.debug("CloudHole returned: %s" % content)
            data = json.loads(content)
            user_agent = data[0]['userAgent']
            clearance = data[0]['cookies']
            log.info("New UA and clearance: %s / %s" % (user_agent, clearance))
        except Exception as e:
            log.error("CloudHole error: %s" % repr(e))
    return clearance, user_agent
