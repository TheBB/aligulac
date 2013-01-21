#!/usr/bin/python
import os
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "aligulac.settings")

from itertools import combinations
from random import shuffle

from ratings.models import Period, Player, Rating, Match, Team
from simul.playerlist import make_player
from simul.formats.teampl import TeamPL
from simul.formats.match import Match

from numpy import *
from rating import update

for player in Player.objects.all():
    ratings = list(Rating.objects.filter(player=player, period__id__gt=11).order_by('period__id'))

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
        d = sum([r.domination for r in ratings[i1:i2+1] if r.decay < 4])
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
