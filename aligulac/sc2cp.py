#!/usr/bin/python
from __future__ import with_statement
import os
import sys
import time
from urllib2 import urlopen, Request

from BeautifulSoup import BeautifulSoup

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "aligulac.settings")

from ratings.models import Match, Player

_user_agent = 'Mozilla/5.0 (X11; Linux x86_64; rv:16.0) Gecko/20100101 Firefox/16.0'
_base_url = 'http://www.sc2charts.net/en/edb/players/%i/'

def get_url(url):
    try:
        request = Request(url, headers={'User-Agent': _user_agent})
        result = urlopen(request).read()
        result = result.replace("</scr'+'ipt>", '')
        return result
    except:
        return None

if __name__ == '__main__':
    rid = int(sys.argv[1])
    if Player.objects.filter(sc2c_id=rid).count() > 0:
        print 'Did not import new player, already exists.'
        sys.exit(1)

    soup = BeautifulSoup(get_url(_base_url % rid))

    tag = soup.findAll('h1')[0].contents[0].strip()
    try:
        country = soup.findAll(lambda t: (u'class', u'content_flag') in t.attrs)[0]['src'].split('/')[-1].split('.')[0].upper()
    except:
        country = ''
    race = sys.argv[2]

    print '------ From %s' % (_base_url % rid)
    k = raw_input('------ Add new player: %s (%s, %s)? ' % (tag, country, race))
    if k.isdigit():
        p = Player.objects.get(id=int(k))
        p.sc2c_id = rid
        p.save()
    elif k.upper() == 'Y':
        p = Player()
        p.tag = tag
        p.country = country
        p.race = race
        p.sc2c_id = rid
        p.save()
