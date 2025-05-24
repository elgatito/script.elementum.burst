#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
sys.path.insert(0, os.path.join(os.path.relpath(os.path.dirname(__file__), "./"), '..', 'resources', 'site-packages'))

import antizapret
import requests
from six.moves import urllib_parse


if __name__ == "__main__":
    antizapret_proxy = antizapret.AntizapretProxy()
    # Test cases
    print("Testing proxy detection:")
    torrent_trackers = [
        "rutracker.org",
        "rutracker.net",
        "rutor.info",
        "rutor.is",
        "nnmclub.to",
        "kinozal.tv",
        "rustorka.com",
        "megapeer.vip",
        "bluebird-hd.org",
        "pirat.one",
        "www.lostfilm.tv",
        "www.lostfilm.download",
        "newstudio.tv",
        "le-production.tv",
        "anilibria.tv",
        "anilibria.top",
        "anilibria.wtf",
        "tr.anidub.com",
        "animaunt.fun",
        "tracker.0day.community",
        "baibako.tv",
        "toloka.to",
        "thepiratebay.org",
        "thepiratebay10.xyz",
        "1337x.to",
        "glodls.to",
        "yts.mx",
        "eztvx.to",
        "bt4gprx.com",
        "bitsearch.to",
        "torrenting.com",
        "www.limetorrents.lol",
        "uindex.org",
    ]
    for domain in torrent_trackers:
        print("{} -> {}".format(domain, antizapret_proxy.detect(domain)))
    print("-" * 20)

    test_urls = ["https://rutracker.org", "https://rutracker.net/forum/viewtopic.php?t=5324346", "https://rutor.info/torrent/472", "https://rutor.is", "https://kinozal.tv", "https://www.lostfilm.tv:443", "https://ifconfig.co:443/ip"]

    for url in test_urls:
        print("\nTesting opening URL: %s" % (url))
        parsed = urllib_parse.urlparse(url)
        proxy = antizapret_proxy.detect(host=parsed.netloc)
        print("Detected Antizapret proxy for %s: %s" % (parsed.netloc, proxy))
        proxies = {
            'http': proxy,
            'https': proxy,
        }
        try:
            response = requests.get(url, proxies=proxies)
            print("Code: %s" % (response.status_code))
            body = response.text
            if len(body) < 100:
                print("Body: %s" % (body))
            else:
                print("Body length: %s" % (len(body)))
        except Exception as e:
            print("Can't make a request: %s" % (e))
