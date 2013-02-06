#!/usr/bin/python

'''
This script looks around the database for possible inconsistencies.
'''

import os, sys, pickle
from datetime import timedelta

# Required for Django imports to work correctly.
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "aligulac.settings")

from django.db.models import Q, F
from ratings.models import Player, Match, Rating, Event, Period
from aligulac.settings import M_WARNINGS, M_APPROVED

with open(M_WARNINGS, 'r') as f:
    warnings = pickle.load(f)

with open(M_APPROVED, 'r') as f:
    approved = pickle.load(f)

def check_matches(matches):
    winners = set([m.get_winner() for m in matches])
    if len(winners) > 1 and None not in winners:
        return

    winscores = set([m.get_winner_score() for m in matches])
    losscores = set([m.get_loser_score() for m in matches])
    if max(winscores) - min(winscores) > 0 or max(losscores) - min(losscores) > 0:
        return

    ids = tuple(sorted([m.id for m in matches]))
    if not ids in approved:
        warnings.add(tuple(sorted([m.id for m in matches])))

def check_opponents(matches):
    start = 0
    for i in range(0, len(matches[:-1])):
        if (matches[i+1].date - matches[i].date).days > 10:
            if i+1 > start + 1:
                check_matches(matches[start:i+1])
            start = i+1
    if len(matches) > start + 1:
        check_matches(matches[start:])

matches = list(Match.objects.all().select_related('pla', 'plb').extra(select={\
        'minid': 'least(pla_id, plb_id)', 'maxid': 'greatest(pla_id, plb_id)'})\
        .order_by('pla__id', 'plb__id', 'date'))

minid = matches[0].minid
maxid = matches[0].maxid
start = 0

for i, m in enumerate(matches):
    if m.minid != minid or m.maxid != maxid:
        if i > start + 1:
            check_opponents(matches[start:i])
        start = i
        minid = m.minid
        maxid = m.maxid
if len(matches) > start + 1:
    check_opponents(matches[start:])

with open(M_WARNINGS, 'w') as f:
    pickle.dump(warnings, f)

with open(M_APPROVED, 'w') as f:
    pickle.dump(approved, f)

print len(warnings)
