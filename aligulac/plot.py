#!/usr/bin/python

'''
This script analyzes the predictive power of the rating system.
'''

import sys, os
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "aligulac.settings")

from djangi.db.models import Q

from ratings.models import Match
from ratings.tools import cdf

from math import floor, sqrt
from random import choice
import numpy
from numpy import array
import pylab

num_slots = 30

table_w = [0]*num_slots
table_l = [0]*num_slots
games = 0

num = 0
for m in Match.objects.all().select_related('player__rating').filter(pla__country='KR', plb__country='KR'):
    num += 1
    if num % 1000 == 0:
        print num

    if m.sca + m.scb == 0:
        continue

    try:
        rating = m.pla.rating_set.get(period__id=m.period.id-1)
        rta = rating.get_totalrating(m.rcb)
        dva = rating.get_totaldev(m.rcb)
    except:
        rta = 0
        dva = sqrt(2)*0.6

    try:
        rating = m.plb.rating_set.get(period__id=m.period.id-1)
        rtb = rating.get_totalrating(m.rca)
        dvb = rating.get_totaldev(m.rca)
    except:
        rtb = 0
        dvb = sqrt(2)*0.6

    prob = cdf(rta-rtb, scale=sqrt(1+dva**2+dvb**2))

    if prob < 0.5:
        prob = 1-prob
        na, nb = m.scb, m.sca
    elif prob > 0.5:
        na, nb = m.sca, m.scb
    else:
        na, nb = choice([(m.sca, m.scb), (m.scb, m.sca)])

    S = int(floor(2*(prob-0.5)*num_slots))

    table_w[S] += na
    table_l[S] += nb
    games += na + nb

zones = []
fracs = []
games = []
slw = float(50)/num_slots
for i in range(0,num_slots):
    if table_w[i] + table_l[i] == 0:
        continue

    zones.append(50.0+slw*(i+0.5))
    fracs.append(float(table_w[i]) / float(table_w[i] + table_l[i]))
    games.append(table_w[i] + table_l[i])

a = numpy.polynomial.polynomial.polyfit(zones,[100*f for f in fracs], 1, w=games)

p1, = pylab.plot(zones, [100*f for f in fracs], '#000000', marker='o', linewidth=2)
p2, = pylab.plot(zones + [100], [z for z in zones] + [100], '#ff0000', linestyle='--')
p3, = pylab.plot([zones[0],100], [a[0]+a[1]*zones[0],a[0]+a[1]*100],\
                 '#0000ff', linestyle='--')

z = 1.96
fr = array(fracs)
gm = array(games)
ci_mean = (fr + z**2/2/gm) / (1 + z**2/gm)
ci_width = z * numpy.sqrt(fr*(1-fr)/gm + z**2/4/gm**2) / (1 + z**2/gm)
pylab.fill_between(zones, 100*(ci_mean-ci_width), 100*(ci_mean+ci_width), facecolor='#dddddd', edgecolor='#bbbbbb')

pylab.axis([50,100,50,100])
pylab.grid()
pylab.xlabel('Predicted winrate')
pylab.ylabel('Actual winrate')

pylab.title('Actual vs. predicted winrate (' + str(sum(games)) + ' games)')
pylab.legend([p2,p3], ['ideal','fitted'], loc=9)
pylab.show()
