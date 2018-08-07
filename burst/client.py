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

from xbmc import translatePath

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/53.0.2785.21 Safari/537.36"

try:
    PATH_TEMP = translatePath("special://temp").decode(sys.getfilesystemencoding(), 'ignore')
except:
    PATH_TEMP = translatePath("special://temp").decode('utf-8')

dns_cache = {}
dns_public_list = ['9.9.9.9', '8.8.8.8', '8.8.4.4']
dns_opennic_list = ['193.183.98.66', '172.104.136.243', '89.18.27.167']

proxy_types = ["socks4", "socks5", "http", "https"]
_orig_create_connection = connection.create_connection

antizapret = antizapret.AntizapretDetector()

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


# class MyHTTPConnection(httplib.HTTPConnection):
#     def connect(self):
#         self.sock = socket.create_connection((MyResolver(self.host), self.port), self.timeout)

# HTTPS requests are not working, because of handshakes fails, so disabling now
# class MyHTTPSConnection(httplib.HTTPSConnection):
#     def connect(self):
#         self.verify_mode = ssl.CERT_NONE
#         self.check_hostname = False
#
#         sock = socket.create_connection((MyResolver(self.host), self.port), self.timeout)
#         # self.sock = ssl.wrap_socket(sock, self.key_file, self.cert_file)
#         if self._tunnel_host:
#             self.sock = sock
#             self._tunnel()
#         try:
#             self.sock = ssl.wrap_socket(sock, ssl_version=ssl.PROTOCOL_SSLv23)
#         except Exception, e:
#             log.debug("Trying SSLv3.: %s --- %s" % (e, self))
#             # self.sock = ssl.wrap_socket(sock, ssl_version=ssl.PROTOCOL_TLSv1, ciphers="ADH-AES256-SHA")
#             self.sock = ssl.wrap_socket(sock, ssl_version=ssl.PROTOCOL_TLSv1)


# class MyHTTPHandler(urllib2.HTTPHandler):
#     def http_open(self, req):
#         return self.do_open(MyHTTPConnection, req)

# class MyHTTPSHandler(urllib2.HTTPSHandler):
#     def https_open(self, req):
#         return self.do_open(MyHTTPSConnection, req)

class Client:
    """
    Web client class with automatic charset detection and decoding
    """
    def __init__(self, proxy_url=None, charset='utf-8'):
        self._counter = 0
        self._cookies_filename = ''
        self._cookies = LWPCookieJar()
        self.user_agent = USER_AGENT
        self.clearance = None
        self.content = None
        self.status = None
        self.token = None
        self.passkey = None
        self.proxy_url = proxy_url
        self.charset = charset

        self.use_antizapret = False
        self.needs_proxylock = False
        # self.antizapret = antizapret.AntizapretDetector()

        self.headers = dict()

        self.session = requests.session()
        self.session.verify = False
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
                else:
                    del req_headers[key.capitalize()]

        if self.token:
            req_headers["Authorization"] = self.token

        req = None
        if post_data:
            req = requests.Request('POST', url, data=post_data, headers=req_headers)
        else:
            req = requests.Request('GET', url, headers=req_headers)
        prepped = self.session.prepare_request(req)

        try:
            self._good_spider()
            with self.session.send(prepped) as response:
                self.headers = response.headers
                self._save_cookies()
                self.content = response.text
                self.status = response.status_code

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
        if self.open(url.encode('utf-8'), post_data=encode_dict(data, self.charset)):
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

# def get_cloudhole_key():
#     """ CloudHole API key fetcher

#     Returns:
#         str: A CloudHole API key
#     """
#     cloudhole_key = None
#     try:
#         r = urllib2.Request("https://cloudhole.herokuapp.com/key")
#         r.add_header('Content-type', 'application/json')
#         with closing(opener.open(r)) as response:
#             content = response.read()
#         log.info("CloudHole key: %s" % content)
#         data = json.loads(content)
#         cloudhole_key = data['key']
#     except Exception as e:
#         log.error("Getting CloudHole key error: %s" % repr(e))
#     return cloudhole_key


# def get_cloudhole_clearance(cloudhole_key):
#     """ CloudHole clearance fetcher

#     Args:
#         cloudhole_key (str): The CloudHole API key saved in settings or from ``get_cloudhole_key`` directly
#     Returns:
#         tuple: A CloudHole clearance cookie and user-agent string
#     """
#     user_agent = USER_AGENT
#     clearance = None
#     if cloudhole_key:
#         try:
#             r = urllib2.Request("https://cloudhole.herokuapp.com/clearances")
#             r.add_header('Content-type', 'application/json')
#             r.add_header('Authorization', cloudhole_key)
#             with closing(opener.open(r)) as response:
#                 content = response.read()
#             log.debug("CloudHole returned: %s" % content)
#             data = json.loads(content)
#             user_agent = data[0]['userAgent']
#             clearance = data[0]['cookies']
#             log.info("New UA and clearance: %s / %s" % (user_agent, clearance))
#         except Exception as e:
#             log.error("CloudHole error: %s" % repr(e))
#     return clearance, user_agent

# def parse_proxy_url(proxy_url):
#     proto = None
#     host = None
#     port = None
#     login = None
#     password = None

#     if not proxy_url:
#         return

#     proto_parsed = proxy_url.split("://")[0].lower()
#     if proto_parsed == "socks5":
#         proto = socks.SOCKS5
#     elif proto_parsed == "socks4":
#         proto = socks.SOCKS4
#     elif proto_parsed == "http":
#         proto = socks.HTTP
#     elif proto_parsed == "https":
#         proto = socks.HTTP

#     host_string = proxy_url.split("://")[1]
#     if '@' in host_string:
#         ary = host_string.split("@")
#         user_string = ary[0]
#         host_string = ary[1]

#         ary = user_string.split(":")
#         login = ary[0]
#         password = ary[1]
#     if host_string:
#         ary = host_string.split(":")
#         host = ary[0]
#         port = ary[1]

#     return SocksiPyHandler(proxytype=proto, proxyaddr=host, proxyport=int(port), username=login, password=password, rdns=True)

def patched_create_connection(address, *args, **kwargs):
    """Wrap urllib3's create_connection to resolve the name elsewhere"""
    # resolve hostname to an ip address; use your own
    # resolver here, as otherwise the system resolver will be used.
    host, port = address
    log.debug("Custom resolver: %s --- %s --- %s" % (host, port, repr(address)))
    hostname = MyResolver(host)

    return _orig_create_connection((hostname, port), *args, **kwargs)
