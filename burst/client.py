# -*- coding: utf-8 -*-

"""
Burst web client
"""

import os
import sys
import urllib3
import dns.resolver
import antizapret
import requests

from elementum.provider import log, get_setting
from time import sleep
from urlparse import urlparse
from urllib3.util import connection
from cookielib import LWPCookieJar
from urllib import urlencode
from utils import encode_dict

from requests.packages.urllib3.util.retry import Retry
from requests.adapters import HTTPAdapter

from xbmc import translatePath

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/53.0.2785.21 Safari/537.36"

try:
    PATH_TEMP = translatePath("special://temp").decode(sys.getfilesystemencoding(), 'ignore')
except:
    PATH_TEMP = translatePath("special://temp").decode('utf-8')

# Custom DNS default data
dns_cache = {}
dns_public_list = ['9.9.9.9', '8.8.8.8', '8.8.4.4']
dns_opennic_list = ['193.183.98.66', '172.104.136.243', '89.18.27.167']
# Save original DNS resolver
_orig_create_connection = connection.create_connection

# Proxy types
proxy_types = ["socks4", "socks5", "http", "https"]

# Init antizapret object that does detection of antizapret proxies
antizapret = antizapret.AntizapretDetector()

# Disable warning from urllib
urllib3.disable_warnings()

def MyResolver(host):
    if '.' not in host:
        return host

    try:
        return dns_cache[host]
    except KeyError:
        pass

    ip = ResolvePublic(host)
    if not ip:
        ip = ResolveOpennic(host)

    if ip:
        log.debug("Host %s resolved to %s" % (host, ip))
        dns_cache[host] = ip
        return ip
    else:
        return host

def ResolvePublic(host):
    try:
        log.debug("Custom DNS resolving with public DNS for: %s" % host)
        resolver = dns.resolver.Resolver()
        resolver.nameservers = dns_public_list
        answer = resolver.query(host, 'A')
        return answer.rrset.items[0].address
    except:
        return

def ResolveOpennic(host):
    try:
        log.debug("Custom DNS resolving with public DNS for: %s" % host)
        resolver = dns.resolver.Resolver()
        resolver.nameservers = dns_opennic_list
        answer = resolver.query(host, 'A')
        return answer.rrset.items[0].address
    except:
        return

class Client:
    """
    Web client class with automatic charset detection and decoding
    """
    def __init__(self, proxy_url=None, request_charset='utf-8', response_charset=None):
        self._counter = 0
        self._cookies_filename = ''
        self._cookies = LWPCookieJar()
        self.url = None
        self.user_agent = USER_AGENT
        self.clearance = None
        self.content = None
        self.status = None
        self.token = None
        self.passkey = None
        self.proxy_url = proxy_url
        self.request_charset = request_charset
        self.response_charset = response_charset

        self.use_antizapret = False
        self.needs_proxylock = False

        self.headers = dict()
        self.request_headers = None

        self.session = requests.session()
        self.session.verify = False

        # Enabling retrying on failed requests
        retries = Retry(
            total=2,
            read=2,
            connect=2,
            redirect=3,
            backoff_factor=0.1
            # status_forcelist=[ 500, 502, 503, 504 ])
        )

        self.session.mount('http://', HTTPAdapter(max_retries=retries))
        self.session.mount('https://', HTTPAdapter(max_retries=retries))
        # self.session = cfscrape.create_scraper()
        # self.scraper = cfscrape.create_scraper()
        # self.session = self.scraper.session()

        global dns_public_list
        global dns_opennic_list
        dns_public_list = get_setting("public_dns_list", unicode).replace(" ", "").split(",")
        dns_opennic_list = get_setting("opennic_dns_list", unicode).replace(" ", "").split(",")
        # socket.setdefaulttimeout(60)

        # Parsing proxy information
        proxy = {
            'enabled': get_setting("proxy_enabled", bool),
            'use_type': get_setting("proxy_use_type", int),
            'type': proxy_types[0],
            'host': get_setting("proxy_host", unicode),
            'port': get_setting("proxy_port", int),
            'login': get_setting("proxy_login", unicode),
            'password': get_setting("proxy_password", unicode),
        }

        try:
            proxy['type'] = proxy_types[get_setting("proxy_type", int)]
        except:
            pass

        if get_setting("use_public_dns", bool):
            connection.create_connection = patched_create_connection

        if proxy['enabled']:
            if proxy['use_type'] == 0 and proxy_url:
                log.debug("Setting proxy from Elementum: %s" % (proxy_url))
            elif proxy['use_type'] == 1:
                log.debug("Setting proxy with custom settings: %s" % (repr(proxy)))

                if proxy['login'] or proxy['password']:
                    proxy_url = "{}://{}:{}@{}:{}".format(proxy['type'], proxy['login'], proxy['password'], proxy['host'], proxy['port'])
                else:
                    proxy_url = "{}://{}:{}".format(proxy['type'], proxy['host'], proxy['port'])
            elif proxy['use_type'] == 2:

                log.debug("Setting proxy to Antizapret resolver")
                self.use_antizapret = True
                proxy_url = None

            if proxy_url:
                self.session.proxies = {
                    'http': proxy_url,
                    'https': proxy_url,
                }

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

    def open(self, url, language='en', post_data=None, get_data=None, headers=None):
        """ Opens a connection to a webpage and saves its HTML content in ``self.content``

        Args:
            url        (str): The URL to open
            language   (str): The language code for the ``Content-Language`` header
            post_data (dict): POST data for the request
            get_data  (dict): GET data for the request
        """

        if get_data:
            url += '?' + urlencode(get_data)

        if self.use_antizapret:
            parsed = urlparse(url)
            proxy = antizapret.detect(host=parsed.netloc, scheme=parsed.scheme)
            if proxy:
                log.debug("Detected antizapret proxy for %s://%s: %s" % (parsed.scheme, parsed.netloc, proxy))
                self.session.proxies = {
                    'http': proxy,
                    'https': proxy,
                }

        log.debug("Opening URL: %s" % repr(url))
        if self.session.proxies:
            log.debug("Proxies: %s" % (repr(self.session.proxies)))

        self._read_cookies(url)
        self.session.cookies = self._cookies

        log.debug("Cookies for %s: %s" % (repr(url), repr(self._cookies)))

        # Default headers for any request. Pretend like we are the usual browser.
        req_headers = {
            'User-Agent': self.user_agent,
            'Content-Language': language,
            'Accept-Encoding': 'deflate, compress, gzip',
            'Origin': url,
            'Referer': url
        }

        # If headers passed to open() call - we overwrite headers.
        if headers:
            for key, value in headers.iteritems():
                if value:
                    req_headers[key] = value
                elif key.capitalize() in req_headers:
                    del req_headers[key.capitalize()]

        if self.token:
            req_headers["Authorization"] = self.token

        req = None
        if post_data:
            req = requests.Request('POST', url, data=post_data, headers=req_headers)
        else:
            req = requests.Request('GET', url, headers=req_headers)

        prepped = self.session.prepare_request(req)
        self.request_headers = prepped.headers

        try:
            self._good_spider()
            with self.session.send(prepped) as response:
                self.headers = response.headers
                self._save_cookies()
                self.status = response.status_code
                self.url = response.url

                if self.response_charset:
                    self.content = response.content.decode(self.response_charset, 'ignore')
                else:
                    self.content = response.text

        except Exception as e:
            import traceback
            log.error("%s failed with %s:" % (repr(url), repr(e)))
            map(log.debug, traceback.format_exc().split("\n"))

        log.debug("Status for %s : %s" % (repr(url), str(self.status)))

        return self.status == 200

    def login(self, url, data, fails_with):
        """ Login wrapper around ``open``

        Args:
            url        (str): The URL to open
            data      (dict): POST login data
            fails_with (str): String that must **not** be included in the response's content

        Returns:
            bool: Whether or not login was successful
        """
        if self.open(url.encode('utf-8'), post_data=encode_dict(data, self.request_charset)):
            try:
                if fails_with in self.content:
                    self.status = 'Wrong username or password'
                    return False
            except Exception as e:
                log.debug("Login failed with: %s" % e)
                try:
                    if fails_with in self.content.decode('utf-8'):
                        self.status = 'Wrong username or password'
                        return False
                except:
                    return False

            return True

        return False

def patched_create_connection(address, *args, **kwargs):
    """Wrap urllib3's create_connection to resolve the name elsewhere"""
    # resolve hostname to an ip address; use your own
    # resolver here, as otherwise the system resolver will be used.
    host, port = address
    log.debug("Custom resolver: %s --- %s --- %s" % (host, port, repr(address)))
    hostname = MyResolver(host)

    return _orig_create_connection((hostname, port), *args, **kwargs)
