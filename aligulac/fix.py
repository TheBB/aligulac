#!/usr/bin/python
import os
import sys
import csv
from urllib2 import urlopen, Request
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "aligulac.settings")

from BeautifulSoup import BeautifulSoup

from django.db.models import Q

from ratings.models import Player, Match
from ratings.tools import find_player

user_agent = 'Mozilla/5.0 (X11; Linux x86_64; rv:16.0) Gecko/20100101 Firefox/16.0'
kr_url = 'http://www.teamliquid.net/tlpd/sc2-korean/players/{id}'
in_url = 'http://www.teamliquid.net/tlpd/sc2-international/players/{id}'

players = set()

matches = []
with open('tlpd.dump', 'rb') as csvfile:
    reader = csv.reader(csvfile, delimiter=',', quotechar='"')
    for row in reader:
        matches.append(row)

def do_guy(id, tag):
    search = Player.objects.filter(Q(tlpd_kr_id=id) | Q(tlpd_in_id=id))
    if search.exists():
        return search[0]

    print in_url.format(id=id)

    tag = raw_input('Tag? ')

    if tag.isdigit():
        p = Player.objects.get(id=int(tag))
        p.tlpd_in_id = id
        p.save()
        return p

    race = raw_input('Race? ')
    country = raw_input('Country? ')

    p = Player()
    p.tag = tag
    p.race = race.upper()
    p.country = country.upper()
    p.tlpd_in_id = id
    p.save()

    return p

num = 0

for match in matches:
    num += 1

    pla = do_guy(int(match[3]), match[2])
    plb = do_guy(int(match[6]), match[5])

    q = Q(pla=pla, plb=plb) | Q(plb=pla, pla=plb)
    search = Match.objects.filter(q).extra(where=['abs(datediff(date,\'%s\')) < 2' % match[0]])
    if search.count() > 0:
        print search
    else:
        m = Match()
        m.pla = pla
        m.plb = plb
        m.sca = int(match[4])
        m.scb = int(match[7])
        m.rca = pla.race
        m.rcb = plb.race
        m.date = match[0]
        m.event = match[1] + ' (TLPD)'
        m.set_period()
        m.save()

        print 'Match %i:' % num, m
