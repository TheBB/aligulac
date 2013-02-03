#!/usr/bin/python
import os
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "aligulac.settings")

from django.db.models import F, Avg

from itertools import combinations
from random import shuffle

from ratings.models import Period, Player, Rating, Match, Team
from simul.playerlist import make_player
from simul.formats.teampl import TeamPL
from simul.formats.match import Match

from numpy import *
from rating import update

limit = 8
mean = False
first_period=14

Rating.objects.all().update(domination=None)

print 'Evaluating domination scores...'
for period in Period.objects.filter(computed=True, id__gt=first_period):
    bench = Rating.objects.filter(period=period, decay__lt=4, dev__lt=0.2).order_by('-rating')[limit-1].rating
    if mean:
        objs = Rating.objects.filter(period=period, decay__lt=4, dev__lt=0.2, rating__gte=bench)
        bench = objs.aggregate(Avg('rating'))['rating__avg']
    print '%i: %f' % (period.id, bench)
    Rating.objects.filter(period=period, decay__lt=4, dev__lt=0.2).update(domination=F('rating')-bench)

print 'Evaluating Hall of Fame...'
for player in Player.objects.all():
    ratings = list(Rating.objects.filter(player=player, period__id__gt=first_period).order_by('period__id'))

    if len(ratings) == 0:
        continue

    inds = []
    for i in range(1, len(ratings)):
        if ratings[i].domination == None or ratings[i-1].domination == None:
            continue
        if ratings[i].domination * ratings[i-1].domination < 0:
            if ratings[i].domination > 0:
                inds.append(i)
            else:
                inds.append(i-1)
    if ratings[0].domination > 0:
        inds.append(0)
    if ratings[-1].domination > 0:
        inds.append(len(ratings)-1)
    inds = sorted(list(set(inds)))

    dom = 0
    init = None
    fin = None
    for i1, i2 in combinations(inds, 2):
        d = sum([r.domination for r in ratings[i1:i2+1] if r.domination != None])
        if d > dom:
            dom = d
            init = ratings[i1].period
            try:
                fin = ratings[i2+1].period
            except:
                fin = Period.objects.get(id=ratings[-1].period.id+1)

    if init == None:
        dom = -100
        init = None
        for i in range(1,len(ratings)):
            if ratings[i].decay > 3:
                continue
            if ratings[i].dev > 0.2:
                continue
            if ratings[i].domination > dom:
                dom = ratings[i].domination
                init = ratings[i].period

    if init == None:
        continue

    if fin == None:
        fin = Period.objects.get(id=init.id+1)

    player.dom_val = dom
    player.dom_start = init
    player.dom_end = fin
    player.save()
