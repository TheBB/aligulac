#!/usr/bin/python
import os, datetime, re, sys
from urllib2 import urlopen, Request

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "aligulac.settings")

from ratings.models import Period, Player, Rating, Match, Event
from django.db.models import Sum

ngames = Match.objects.all().aggregate(Sum('sca'))['sca__sum'] + Match.objects.all().aggregate(Sum('scb'))['scb__sum']
nmatches = Match.objects.all().count()
npartial = Match.objects.exclude(eventobj__isnull=True, event='').count()
nfull = Match.objects.filter(eventobj__isnull=False).count()

print '%i matches with %i games' % (nmatches, ngames)
print '%i (%.2f%%) with event information' % (npartial, float(npartial)*100/nmatches)
print '%i (%.2f%%) with event object' % (nfull, float(nfull)*100/nmatches)
print '%i matches missing event information' % (nmatches-npartial)
print '%i matches missing event object' % (nmatches-nfull)
