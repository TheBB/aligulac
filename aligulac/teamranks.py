#!/usr/bin/env python3

from datetime import datetime
from itertools import combinations
import os
from random import shuffle
import sys

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'aligulac.settings')

from aligulac.tools import get_latest_period

from ratings.models import (
    Group,
    Rating,
)
from ratings.tools import filter_active

from simul.formats.teamak import TeamAK
from simul.formats.teampl import TeamPL
from simul.playerlist import make_player

proleague = 'pl' in sys.argv

nplayers_max = 6 if proleague else 5
nplayers_min = 6 if proleague else 1
Simulator = TeamPL if proleague else TeamAK

# {{{ Get a list of teams that can compete
curp = get_latest_period()
allowed_teams = []
teams = Group.objects.filter(active=True, is_team=True)
for t in teams:
    nplayers_available = filter_active(Rating.objects.filter(
        period=curp,
        player__groupmembership__group=t,
        player__groupmembership__current=True,
        player__groupmembership__playing=True,
    )).count()

    if nplayers_available >= nplayers_min:
        allowed_teams.append(t)

disallowed = Group.objects.filter(is_team=True).exclude(id__in=[t.id for t in allowed_teams])
if proleague:
    disallowed.update(scorepl=0.0)
else:
    disallowed.update(scoreak=0.0)

nteams = len(allowed_teams)
# }}}

# {{{ Simulate
print('[%s] Simulating %s for %i teams' % (str(datetime.now()), 'PL' if proleague else 'AK', nteams))

scores = {t: 0.0 for t in allowed_teams}
for ta, tb in combinations(allowed_teams, 2):
    players = []
    for t in [ta, tb]:
        ratings = list(filter_active(Rating.objects.filter(
            period=curp,
            player__groupmembership__group=t,
            player__groupmembership__current=True,
            player__groupmembership__playing=True,
        )).order_by('-rating').select_related('player')[:nplayers_max])

        if proleague:
            players.append(ratings[::-1])
        else:
            ace = ratings[0]
            shuffle(ratings)
            players.append(ratings + [ace])

    if proleague:
        sipl = [make_player(r.player) for r in players[0]] + [make_player(r.player) for r in players[1]]
    else:
        sipl = [[make_player(r.player) for r in ratings] for ratings in players]

    sim = Simulator(2)
    sim.set_players(sipl)
    sim.compute()

    if proleague:
        scores[ta] += sim._tally[0].win/(nteams-1)
        scores[tb] += sim._tally[1].win/(nteams-1)
    else:
        scores[ta] += sim._tally[0][1]/(nteams-1)
        scores[tb] += sim._tally[1][1]/(nteams-1)
# }}}

# {{{ Save
print('[%s] Saving %s scores for %i teams' % (str(datetime.now()), 'PL' if proleague else 'AK', nteams))
for team in allowed_teams:
    if proleague:
        team.scorepl = scores[team]
    else:
        team.scoreak = scores[team]
    team.save()
# }}}
