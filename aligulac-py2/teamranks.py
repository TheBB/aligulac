#!/usr/bin/python

'''
This script recomputes the team rankings, all-kill or proleague.

./teamranks.py [ak|pl]
'''

# This is required to make Django imports work properly.
import os, sys
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "aligulac.settings")

from itertools import combinations
from random import shuffle

from ratings.models import Period, Rating, Group
from ratings.tools import filter_active_ratings
from simul.playerlist import make_player
from simul.formats.teamak import TeamAK
from simul.formats.teampl import TeamPL

# Get argument: proleague or allkill rank
try:
    proleague = (sys.argv[1] == 'pl')
except:
    proleague = False

# Setup
nplayers_max = 6 if proleague else 5
nplayers_needed = 6 if proleague else 1
Simulator = TeamPL if proleague else TeamAK

# Get a list of all teams that can compete
current_period = Period.objects.filter(computed=True).order_by('-id')[0]
teams = Group.objects.filter(active=True, is_team=True)
allowed_teams = []
for team in teams:
    ratings = Rating.objects.filter(period=current_period, 
                                    player__groupmembership__group=team,
                                    player__groupmembership__current=True, 
                                    player__groupmembership__playing=True)\
                    .exclude(player__race='S').exclude(player__race='R')
    if filter_active_ratings(ratings).count() >= nplayers_needed:
        allowed_teams.append(team)
nteams = len(allowed_teams)

# Prepare the score table
scores = dict()
for t in allowed_teams:
    scores[t] = 0.0

# Loop over all pairs of teams
for (team_a, team_b) in combinations(allowed_teams, 2):
    print team_a.name, '--', team_b.name

    # Get player lists for both teams
    players = []
    for team in [team_a, team_b]:
        ratings = Rating.objects.filter(period=current_period, 
                                        player__groupmembership__group=team,
                                        player__groupmembership__current=True, 
                                        player__groupmembership__playing=True)\
                        .exclude(player__race='S').exclude(player__race='R')
        ratings = list(filter_active_ratings(ratings).order_by('-rating')[:nplayers_max])
        if not proleague:
            # First six in random order, then strongest player for ace match
            ace = ratings[0]
            shuffle(ratings)
            players.append(ratings + [ace])
        else:
            # Five players in order from weakest to strongest
            players.append(ratings[::-1])

    # Convert to player objects for the simul library
    if proleague:
        sim_players = [make_player(r.player) for r in players[0]] +\
                      [make_player(r.player) for r in players[1]]
    else:
        sim_players = [[make_player(r.player) for r in ratings] for ratings in players]

    # Simulate the match
    obj = Simulator(2)
    obj.set_players(sim_players)
    obj.compute()

    # Add the scores
    if proleague:
        scores[team_a] += obj._tally[0].win/(nteams-1)
        scores[team_b] += obj._tally[1].win/(nteams-1)
    else:
        scores[team_a] += obj._tally[0][1]/(nteams-1)
        scores[team_b] += obj._tally[1][1]/(nteams-1)

# Write the scores to database
if proleague:
    teams.update(scorepl=0.0)
else:
    teams.update(scoreak=0.0)

allowed_teams = sorted(list(allowed_teams), key=lambda team: -scores[team])
for team in allowed_teams:
    if proleague:
        team.scorepl = scores[team]
    else:
        team.scoreak = scores[team]
    team.save()

    print '%5.2f%%: %s' % (100*scores[team], team.name)
