# -*- coding: utf-8 -*-

"""
Burst web client
"""

import os
import re
import ssl
import sys
import json
import urllib2
import httplib
import socket
import dns.resolver
import socks
import antizapret
from time import sleep
from urlparse import urlparse
from contextlib import closing
from elementum.provider import log, get_setting
from cookielib import Cookie, LWPCookieJar
from urllib import urlencode
from utils import encode_dict
from sockshandler import SocksiPyHandler

from xbmc import translatePath

try:
    ssl._create_default_https_context = ssl._create_unverified_context
except:
    log.debug("Skipping SSL workaround due to old Python version")
    pass

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 " \
             "(KHTML, like Gecko) Chrome/53.0.2785.21 Safari/537.36"
try:
    PATH_TEMP = translatePath("special://temp").decode(sys.getfilesystemencoding(), 'ignore')
except:
    PATH_TEMP = translatePath("special://temp").decode('utf-8')

dns_cache = {}
dns_public_list = ['9.9.9.9', '8.8.8.8', '8.8.4.4']
dns_opennic_list = ['193.183.98.66', '172.104.136.243', '89.18.27.167']

proxy_types = [socks.SOCKS4, socks.SOCKS5, socks.HTTP, socks.HTTP]
opener = None

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


class MyHTTPConnection(httplib.HTTPConnection):
    def connect(self):
        self.sock = socket.create_connection((MyResolver(self.host), self.port), self.timeout)

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


class MyHTTPHandler(urllib2.HTTPHandler):
    def http_open(self, req):
        return self.do_open(MyHTTPConnection, req)

# class MyHTTPSHandler(urllib2.HTTPSHandler):
#     def https_open(self, req):
#         return self.do_open(MyHTTPSConnection, req)

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
        global dns_public_list
        global dns_opennic_list
        dns_public_list = get_setting("public_dns_list", unicode).replace(" ", "").split(",")
        dns_opennic_list = get_setting("opennic_dns_list", unicode).replace(" ", "").split(",")
        socket.setdefaulttimeout(60)

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

    def open(self, url, language='en', post_data=None, get_data=None, headers=None, proxy_url=None, charset='utf8'):
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

        handlers = [urllib2.HTTPCookieProcessor(self._cookies)]

        if get_setting("use_public_dns", bool):
            handlers.append(MyHTTPHandler)

        if proxy['enabled']:
            if proxy['use_type'] == 0 and proxy_url:
                log.debug("Setting proxy from Elementum: %s" % (proxy_url))
                handlers.append(parse_proxy_url(proxy_url))
            elif proxy['use_type'] == 1:
                log.debug("Setting proxy with custom settings: %s" % (repr(proxy)))
                handlers.append(SocksiPyHandler(proxytype=proxy['type'], proxyaddr=proxy['host'], proxyport=int(proxy['port']), username=proxy['login'], password=proxy['password'], rdns=True))
            elif proxy['use_type'] == 2:
                try:
                    handlers.append(antizapret.AntizapretProxyHandler())
                except Exception as e:
                    log.info("Could not create antizapret configuration: %s" % (e))

        opener = urllib2.build_opener(*handlers)

        req.add_header('User-Agent', self.user_agent)
        req.add_header('Content-Language', language)
        req.add_header("Accept-Encoding", "gzip")
        req.add_header("Origin", url)
        req.add_header("Referer", url)

        if headers:
            for key, value in headers.iteritems():
                if value:
                    req.add_header(key, value)
                else:
                    del req.headers[key.capitalize()]

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

                # We try to remove non-utf chars. Should we?
                if (charset and charset.lower() == 'utf-8') or charset is None:
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

    def login(self, url, data, fails_with, charset='utf8'):
        """ Login wrapper around ``open``

        Args:
            url        (str): The URL to open
            data      (dict): POST login data
            fails_with (str): String that must **not** be included in the response's content

        Returns:
            bool: Whether or not login was successful
        """
        result = False
        if self.open(url.encode('utf-8'), post_data=encode_dict(data, charset)):
            result = True
            try:
                if fails_with in self.content:
                    self.status = 'Wrong username or password'
                    result = False
            except Exception as e:
                log.debug("Login failed with: %s" % e)
                try:
                    if fails_with in self.content.decode('utf-8'):
                        self.status = 'Wrong username or password'
                        result = False
                except:
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
        with closing(opener.open(r)) as response:
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
            with closing(opener.open(r)) as response:
                content = response.read()
            log.debug("CloudHole returned: %s" % content)
            data = json.loads(content)
            user_agent = data[0]['userAgent']
            clearance = data[0]['cookies']
            log.info("New UA and clearance: %s / %s" % (user_agent, clearance))
        except Exception as e:
            log.error("CloudHole error: %s" % repr(e))
    return clearance, user_agent

def parse_proxy_url(proxy_url):
    proto = None
    host = None
    port = None
    login = None
    password = None

    if not proxy_url:
        return

    proto_parsed = proxy_url.split("://")[0].lower()
    if proto_parsed == "socks5":
        proto = socks.SOCKS5
    elif proto_parsed == "socks4":
        proto = socks.SOCKS4
    elif proto_parsed == "http":
        proto = socks.HTTP
    elif proto_parsed == "https":
        proto = socks.HTTP

    host_string = proxy_url.split("://")[1]
    if '@' in host_string:
        ary = host_string.split("@")
        user_string = ary[0]
        host_string = ary[1]

        ary = user_string.split(":")
        login = ary[0]
        password = ary[1]
    if host_string:
        ary = host_string.split(":")
        host = ary[0]
        port = ary[1]

    return SocksiPyHandler(proxytype=proto, proxyaddr=host, proxyport=int(port), username=login, password=password, rdns=True)
