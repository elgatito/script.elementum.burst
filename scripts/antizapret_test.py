#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
sys.path.insert(0, os.path.join(os.path.relpath(os.path.dirname(__file__), "./"), '..', 'resources', 'site-packages'))

import urllib2
import antizapret
from contextlib import closing


test_urls = ["https://rutracker.net/", "https://rutracker.cr/forum/viewtopic.php?t=5324346", "http://rutor.info", "http://nnm-club.me", "https://httpbin.org/ip"]

for u in test_urls:
    print "\n\nTesting url: %s" % (u)
    opener = urllib2.build_opener(antizapret.AntizapretProxyHandler())
    req = urllib2.Request(u)

    try:
        with closing(opener.open(req)) as response:
            print "Request: %s" % (repr(req))
            print "Response: %s" % (repr(response))

            print "Code: %s" % (response.getcode())
            print "Headers: %s" % (repr(response.headers))

            b = response.read()
            if len(b) < 100:
                print "Body: %s" % (b)
            else:
                print "Body len: %s" % (len(b))
    except Exception as e:
        print "Can't make a request: %s" % (e)
