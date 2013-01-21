#!/usr/bin/python
import os, datetime, re, sys
from urllib2 import urlopen, Request

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "aligulac.settings")

from ratings.models import Period, Player, Rating, Team

for cur in Period.objects.filter(computed=True):
    top = Rating.objects.filter(period=cur).order_by('-rating')[:2]
    n2 = top[1]
    n1 = top[0]
    diff = n1.rating - n2.rating
    n1.domination = diff
    n1.save()
