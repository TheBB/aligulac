#!/usr/bin/python

'''
This script analyzes the predictive power of the rating system.
'''

import sys, os
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "aligulac.settings")

from django.db.models import Q

from ratings.models import Match
from ratings.tools import cdf

from math import floor, sqrt
from random import choice
import numpy
from numpy.polynomial.polynomial import polyfit
from numpy import array
import pylab

NS = 30

tables = { 'kr-w': [0]*NS, 'kr-l': [0]*NS, 'kr-g': [0]*NS, 'kr-z': [], 'kr-f': [], 'kr-gg': [],
           'in-w': [0]*NS, 'in-l': [0]*NS, 'in-g': [0]*NS, 'in-z': [], 'in-f': [], 'in-gg': [],
           'xx-w': [0]*NS, 'xx-l': [0]*NS, 'xx-g': [0]*NS, 'xx-z': [], 'xx-f': [], 'xx-gg': [],
           'al-w': [0]*NS, 'al-l': [0]*NS, 'al-g': [0]*NS, 'al-z': [], 'al-f': [], 'al-gg': [] }

names = { 'al': 'All', 'kr': 'Korean', 'in': 'International', 'xx': 'Cross-scene' }
           
num = 0

matches = Match.objects.all().select_related('player__rating', 'player')
nmatches = matches.count()

for m in matches:
    num += 1
    if num % 1000 == 0:
        print('{num}/{nmatches}'.format(num=num, nmatches=nmatches))

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

    S = int(floor(2*(prob-0.5)*NS))

    tlist = ['al']
    if m.pla.country == 'KR' and m.plb.country == 'KR':
        tlist.append('kr')
    elif m.pla.country != 'KR' and m.plb.country != 'KR':
        tlist.append('in')
    else:
        tlist.append('xx')

    for t in tlist:
        tables[t+'-w'][S] += na
        tables[t+'-l'][S] += nb
        tables[t+'-g'][S] += na + nb

slw = float(50)/NS
for t in ['al','kr','in','xx']:
    for i in range(0,NS):
        if tables[t+'-g'][i] == 0:
            continue
        tables[t+'-z'].append(50.0+slw*(i+0.5))
        tables[t+'-f'].append(float(tables[t+'-w'][i]) / float(tables[t+'-g'][i]))
        tables[t+'-gg'].append(tables[t+'-g'][i])
    tables[t+'-fit'] = polyfit(tables[t+'-z'], [100*f for f in tables[t+'-f']], 1, w=tables[t+'-gg'])

sub = 1
for t in ['al','kr','in','xx']:
    Z = tables[t+'-z']
    F = tables[t+'-f']
    A = tables[t+'-fit']

    pylab.subplot(2,2,sub)

    p1, = pylab.plot(Z, [100*f for f in F], '#000000', marker='o', linewidth=2)
    p2, = pylab.plot(tables[t+'-z'] + [100], [z for z in tables[t+'-z']] + [100], '#ff0000', linestyle='--')
    p3, = pylab.plot([Z[0],100], [A[0]+A[1]*Z[0],A[0]+A[1]*100], '#0000ff', linestyle='--')

    z = 1.96
    F = array(F)
    G = array(tables[t+'-gg'])
    ci_mean = (F + z**2/2/G) / (1 + z**2/G)
    ci_width = z * numpy.sqrt(F*(1-F)/G + z**2/4/G**2) / (1 + z**2/G)
    pylab.fill_between(Z, 100*(ci_mean-ci_width), 100*(ci_mean+ci_width), 
                       facecolor='#dddddd', edgecolor='#bbbbbb')

    pylab.axis([50,100,50,100])
    pylab.grid()
    #pylab.xlabel('Predicted winrate')
    #pylab.ylabel('Actual winrate')

    pylab.title(names[t] + ' (%i)' % sum(tables[t+'-g']), fontsize=10)

    sub += 1

fig = pylab.gcf()
fig.suptitle('Predicted vs. actual winrate for different scenes', fontsize=14)
pylab.show()
