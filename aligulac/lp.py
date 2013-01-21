#!/usr/bin/python
import os, datetime, re, sys
from urllib2 import urlopen, Request

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "aligulac.settings")

from django.db.models import Q, Avg
from ratings.models import Period, Player, Rating, Match

from BeautifulSoup import BeautifulSoup, NavigableString
from countries import data, transformations

set = Player.objects
for p in sys.argv[1:-1]:
    if p.isdigit():
        set = set.filter(id=int(p))
    elif len(p) == 1:
        set = set.filter(race=p.upper())
    elif len(p) == 2 and p.upper() in data.cca2_to_ccn:
        set = set.filter(country=p.upper())
    else:
        set = set.filter(tag__iexact=p)

if set.count() > 1:
    print 'Player not unique, add more information'
    sys.exit(1)
elif set.count() < 1:
    print 'Player not found'
    sys.exit(1)
else:
    p = set[0]

p.lp_name = sys.argv[-1]
p.save()
