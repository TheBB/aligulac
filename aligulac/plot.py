#!/usr/bin/python

'''
This script analyzes the predictive power of the rating system.
'''

import sys, os
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "aligulac.settings")

from ratings.models import Match

from scipy.stats import norm
from math import floor, sqrt
from random import choice
import numpy
import pylab

num_slots = 30

table_w = [0]*num_slots
table_l = [0]*num_slots
games = 0

num = 0
for m in Match.objects.all():
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

    prob = norm.cdf(rta-rtb, scale=sqrt(1+dva**2+dvb**2))

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
p2, = pylab.plot(zones, [z for z in zones], '#ff0000', linestyle='--')
p3, = pylab.plot([zones[0],zones[-1]], [a[0]+a[1]*zones[0],a[0]+a[1]*zones[-1]],\
                 '#0000ff', linestyle='--')

pylab.axis([50,100,50,100])
pylab.grid()
pylab.xlabel('Predicted winrate')
pylab.ylabel('Actual winrate')

ax = pylab.twinx()
ax.set_ylabel('Games')
p4, = ax.plot(zones, games, '#000000', linestyle='-')

pylab.title('Actual vs. predicted winrate (' + str(sum(games)) + ' games)')
pylab.legend([p2,p3,p4], ['ideal','fitted','games'], loc=9)
pylab.show()
