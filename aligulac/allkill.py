#!/usr/bin/python
import os
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "aligulac.settings")

from itertools import combinations

from ratings.models import Period, Player, Rating, Match, Team
from simul.playerlist import make_player
from simul.formats.teamak import TeamAK
from simul.formats.match import Match

from numpy import *
from rating import update

cur = Period.objects.filter(computed=True).order_by('-id')[0]
pteams = Team.objects.filter(active=True)
teams = []
for t in pteams:
    if Rating.objects.filter(player__teammembership__team=t, player__teammembership__current=True,\
            player__teammembership__playing=True, period=cur, decay__lt=4, dev__lte=0.2).count() > 0:
        teams.append(t)
nteams = len(teams)
S = dict()
for t in teams:
    S[t] = 0.0

for (ta, tb) in combinations(teams, 2):
    print ta.name, '--', tb.name

    dbpl = []
    for team in [ta, tb]:
        rats = Rating.objects.filter(player__teammembership__team=team, player__teammembership__current=True,\
                player__teammembership__playing=True, period=cur, decay__lt=4, dev__lte=0.2).order_by('-rating')[:5]
        dbpl.append(rats[::-1])
    sipl = [[make_player(r.player) for r in rats] for rats in dbpl]

    obj = TeamAK(2)
    obj.set_players(sipl)
    obj.compute()

    S[ta] += obj._tally[0][1]/(nteams-1)
    S[tb] += obj._tally[1][1]/(nteams-1)

for t in pteams:
    t.scoreak = 0.0
    t.save()

teams = sorted(list(teams), key=lambda t: -S[t])
for t in teams:
    t.scoreak = S[t]
    t.save()
    print '%5.2f%s: %s' % (100*S[t], '%', t.name)
