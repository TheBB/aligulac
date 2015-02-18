#!/usr/bin/env python3

from datetime import datetime
from itertools import combinations
import os
import csv

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'aligulac.settings')

from django.db.models import Q, F
from ratings.models import WCSPoints, Player, Event, Match, TYPE_EVENT
from ratings.tools import display_matches

with open('../all_players.csv', 'w', newline='') as csvfile:
    out = csv.writer(csvfile)
    out.writerow(['ID', 'Player', 'Race'])
    for p in Player.objects.all().order_by('id'):
        out.writerow([p.id, p.tag, p.race])

player_ids = [4134,276,111,89,184,95,146,4105,1813,246,58,27,485,1655,2170,
              129,575,151,123,153,882,4734,317,160,145,107,5945,34,1557,19,8,655]
players = Player.objects.filter(id__in=player_ids)

for p in players:
    # with open('../{}_points.csv'.format(p.tag.lower()), 'w', newline='') as csvfile:
    #     out = csv.writer(csvfile)
    #     out.writerow(['ID', 'Event ID', 'Event name', 'WCS tier',
    #                   'WCS year', 'Round reached', 'Points awarded'])
    #     for pts in WCSPoints.objects.filter(player=p).order_by('event__latest'):
    #         last_round = (Event.objects
    #                       .filter(uplink__parent=pts.event)
    #                       .filter(Q(match__pla=p) | Q(match__plb=p))
    #                       .last())
    #         out.writerow([pts.id, pts.event_id, pts.event.fullname,
    #                       pts.event.wcs_tier, pts.event.wcs_year,
    #                       last_round.fullname, pts.points])

    with open('../{}_matches.csv'.format(p.tag.lower()), 'w', newline='') as csvfile:
        out = csv.writer(csvfile)
        out.writerow(['ID',
                      'Player A ID', 'Player A', 'Race A', 'Score A',
                      'Player B ID', 'Player B', 'Race B', 'Score B',
                      'Date', 'Event ID', 'Event name', 'Round ID', 'Round name',
                      'WCS tier', 'WCS year'])
        matches = (p.get_matchset()
                   .filter(eventobj__uplink__parent__wcs_year__isnull=False,
                           eventobj__uplink__parent__type=TYPE_EVENT)
                   .order_by('date'))
        matches = display_matches(matches, fix_left=p)
        for m in matches:
            event = m['match'].eventobj.get_event_event()
            out.writerow([m['match_id'],
                          m['pla']['id'], m['pla']['tag'], m['pla']['race'], m['pla']['score'],
                          m['plb']['id'], m['plb']['tag'], m['plb']['race'], m['plb']['score'],
                          m['date'], event.id, event.fullname, m['match'].eventobj_id,
                          m['match'].eventobj.fullname, event.wcs_tier, event.wcs_year])
    print(p)
