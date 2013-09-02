#!/usr/bin/python

'''
Written for monk's "Why does EG-TL suck" article.
'''

import os
import sys

# Required for Django imports to work correctly.
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "aligulac.settings")

from django.db.models import Q, F
from ratings.models import Player, Match, Rating, Event, Period

proleague = Event.objects.get(id=450)
exclude = Event.objects.get(id=9840)

matches = Match.objects.filter(eventobj__lft__gte=proleague.lft, eventobj__rgt__lte=proleague.rgt).\
                        exclude(eventobj__lft__gte=exclude.lft, eventobj__rgt__lte=exclude.rgt)

players = dict()

def create_if_not_exists(players, p):
    if not p in players:
        players[p] = []

for m in matches:
    create_if_not_exists(players, m.pla)
    create_if_not_exists(players, m.plb)

    try:
        rta = m.pla.rating_set.get(period_id=m.period_id-1)
        diff = rta.get_rating(m.rcb)
        players[m.pla].append((diff, m.rcb, m.plb, m.date))
    except:
        players[m.pla].append((0, m.rcb, m.plb, m.date))


    try:
        rtb = m.plb.rating_set.get(period_id=m.period_id-1)
        diff = rtb.get_rating(m.rca)
        players[m.plb].append((diff, m.rca, m.pla, m.date))
    except:
        players[m.plb].append((0, m.rca, m.pla, m.date))

teams = set()

for p in players:
    sdiff = sum(q[0] for q in players[p])
    p.mdiff = sdiff/len(players[p])

    team = p.teammembership_set.filter(current=True)[0].team
    if team.id in [40, 18]:
        p.steam = 'EG-TL'
    else:
        p.steam = team.name

    teams.add(p.steam)

def print_player(players, p, full=False):
    print '{rt: <15} {t: <15} {m: >5.1f}'.format(rt=p.tag + ' (' + p.race + ')', t=p.steam, m=1000*p.mdiff)

    if full:
        for q in players[p]:
            print '    ' + q[3].strftime('%Y-%m-%d') + ' v' + q[1] + '{diff: >7.1f}'.format(diff=1000*q[0])
        print ''

sort_players = list(players)
sort_players.sort(key=lambda a: a.mdiff, reverse=True)

#for p in sort_players:
    #print_player(players, p, full=True)

for t in teams:
    diff = 0.0
    games = 0

    for p in players:
        if p.steam == t:
            diff += len(players[p]) * p.mdiff
            games += len(players[p])

    diff /= games
    print '{t: <15} {m: >5.1f}'.format(t=t, m=1000*diff)
