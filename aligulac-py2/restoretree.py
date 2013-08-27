#!/usr/bin/python
import os, datetime, re, sys
from urllib2 import urlopen, Request

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "aligulac.settings")

from ratings.models import Period, Player, Rating, Match, Event
from django.db.models import Sum

roots = list(Event.objects.filter(parent__isnull=True).order_by('lft'))
nextleft = 0
for r in roots:
    nextleft = r.reorganize(nextleft) + 1 
