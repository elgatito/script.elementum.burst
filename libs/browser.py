# -*- coding: utf-8 -*-

import json
import urllib2
from os import path
from time import sleep
from storage import Storage
from urlparse import urlparse
from contextlib import closing
from quasar.provider import log
from cookielib import Cookie, LWPCookieJar
from urllib import quote_plus, urlencode

from xbmc import translatePath


USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_8_5) AppleWebKit/537.36" \
             " (KHTML, like Gecko) Chrome/30.0.1599.66 Safari/537.36"
PATH_TEMP = translatePath("special://temp")


class Browser:
    """
    Browser with cookie handling
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
        self.headers = dict()

    def _create_cookies(self, payload):
        return urlencode(payload)

    def _read_cookies(self, url=''):
        self._cookies_filename = path.join(PATH_TEMP, urlparse(url).netloc + '_cookies.jar')
        if path.exists(self._cookies_filename):
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
        return self._cookies

    def open(self, url='', language='en', post_data=None, get_data=None, use_cache=False):
        cache_file = quote_plus(url) + '.cache'
        if use_cache:
            cache = Storage.open(cache_file, ttl=15)
            if 'uri' in cache:
                self.status = 200
                self.content = cache['content']
                self.headers = cache['headers']
                log.info('Using cache for %s' % url)
                cache.close()
                return True

        # Creating request
        if post_data is None:
            post_data = {}
        if get_data is not None:
            url += '?' + urlencode(get_data)

        log.debug("Opening URL: %s" % url)
        result = False

        data = urlencode(post_data) if len(post_data) > 0 else None
        req = urllib2.Request(url, data)

        self._read_cookies(url)
        log.debug("Cookies for %s: %s" % (url, repr(self._cookies)))

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

                self.status = response.getcode()
            result = True

        except urllib2.HTTPError as e:
            self.status = e.code
            log.warning("Status for %s : %s" % (url, str(self.status)))
            if e.code == 403 or e.code == 503:
                log.warning("CloudFlared at %s, try enabling CloudHole" % url)

        except urllib2.URLError as e:
            self.status = e.reason
            log.warning("Status for %s : %s" % (url, str(self.status)))

        except Exception as e:
            import traceback
            log.error("%s failed with %s:" % (url, repr(e)))
            map(log.debug, traceback.format_exc().split("\n"))

        if result:
            if use_cache:
                cache = Storage.open(cache_file, ttl=15)
                cache['content'] = self.content
                cache['headers'] = self.headers
                cache.sync()

        log.debug("Status for %s : %s" % (url, str(self.status)))

        return result

    def login(self, url='', data=None, fails_with=''):
        """
        Login to web site
        :param url:  url address from web site
        :type url: str
        :param payload: parameters for the login request
        :type payload: dict
        :param word:  message from the web site when the login fails
        :type word: str
        :return: True if the login was successful. False, otherwise.
        """
        result = False
        if self.open(url, post_data=data):
            result = True
            if fails_with in self.content.decode('utf-8'):
                self.status = 'Wrong username or password'
                result = False
        return result


def get_cloudhole_key():
    """
    Get CloudHole API key
    https://github.com/scakemyer/cloudhole-api
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


def get_cloudhole_clearance(cloudhole_key=None):
    """
    Define the clearance value and USER AGENT
    https://github.com/scakemyer/cloudhole-api
    :param cloudhole_key: key from cloudhole
    :type  cloudhole_key: str
    :return clearance, USER AGENT
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
