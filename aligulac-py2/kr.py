#!/usr/bin/python

'''
This is an empty file with some basic imports kept around for usefulness to write new scripts.
'''

import os
import sys
from datetime import timedelta, date

# Required for Django imports to work correctly.
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "aligulac.settings")

from django.db.models import Q, F, Sum
from ratings.models import Player, Match, Rating, Event, Period
from aligulac.parameters import KR_START

from pylab import *

N = 20

ntz = lambda x: x if x is not None else 0

n_kr = Player.objects.filter(country='KR').count()
n_nkr = Player.objects.exclude(country='KR').count() - 6

r_kr = []
r_nkr = []
matches = []
dates = []

for p in Period.objects.filter(computed=True, end__lt=datetime.date.today()):
    kr = Rating.objects.filter(player__country='KR', period=p)
    avg_kr = float(ntz(kr.aggregate(Sum('rating'))['rating__sum']))
    avg_kr = (avg_kr + KR_START*(n_kr-kr.count())) / n_kr
    r_kr.append(avg_kr)

    nkr = Rating.objects.exclude(player__country='KR').filter(period=p)
    avg_nkr = float(ntz(nkr.aggregate(Sum('rating'))['rating__sum']))
    avg_nkr /= n_nkr
    r_nkr.append(avg_nkr)

    ms = Match.objects.filter(period=p)
    msa = ms.filter(pla__country='KR').exclude(plb__country='KR')\
            .aggregate(Sum('sca'), Sum('scb'))
    msb = ms.filter(plb__country='KR').exclude(pla__country='KR')\
            .aggregate(Sum('sca'), Sum('scb'))
    matches.append(ntz(msa['sca__sum']) + ntz(msa['scb__sum']) +
                   ntz(msb['sca__sum']) + ntz(msb['scb__sum']))

    dates.append(p.end)

r_kr = array([KR_START] + r_kr)
r_nkr = array([0.0] + r_nkr)
matches = array(matches)

adjust = (n_kr*r_kr + n_nkr*r_nkr) / (n_kr + n_nkr)
r_kr -= adjust
r_nkr -= adjust
print 1000*adjust[-1]

print r_kr - r_nkr

g_kr = diff(r_kr)
g_nkr = diff(r_nkr)

transfer = 1000*g_kr[N:]*n_kr/matches[N:]
p = polyfit(range(0, len(transfer)), transfer, 1)

K = -p[1]/p[0]
print dates[-1] + timedelta(days=int((K - len(transfer)) * 14))

plot([dates[N], dates[-1]], [0, 0], 'k--')
plot(dates[N:], transfer, 'b-', lw=4)
plot([dates[N], dates[-1]], [p[1], p[1] + len(transfer)*p[0]], 'r--', lw=4)
title('Point transfer, Korea vs. The World\nAverage number of points transferred to Korean pool per game')
show()
