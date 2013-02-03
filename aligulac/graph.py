#!/usr/bin/python

'''
This creates a SQLite database of the proscene connectivity graph, useful for importing into gephi.
'''

import os, sqlite3, atexit

# Without this, Django imports won't work correctly
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "aligulac.settings")

from django.db.models import Q, Sum
from ratings.models import Player, Match

# Remove this file if it exists
os.system('rm data.sqlite')

# Set up the SQLite database
db = sqlite3.connect('data.sqlite')
cur = db.cursor()
atexit.register(lambda: cur.close())

cur.execute('''CREATE TABLE nodes (id integer, label text)''')
cur.execute('''CREATE TABLE edges (source integer, target integer, weight integer)''')

db.commit()

# Create the player entries
players = list(Player.objects.all())
for p in players:
    print str(p)
    cur.execute('''INSERT INTO nodes VALUES (:id, :label)''', {'id': p.id, 'label': str(p).decode()})

db.commit()

print len(players), 'players'

# For each player, create links to other players
# Links only go from players with low IDs to players with high IDs, to ensure uniqueness
for i in range(0,len(players)):
    source = players[i]
    print i+1, source

    # Find target players
    q = Q(match_pla__plb=source) | Q(match_plb__pla=source)
    targets = Player.objects.filter(q).filter(id__gt=source.id).distinct()

    # For each target, find weights
    for target in targets:
        q = Q(pla=source, plb=target) | Q(pla=target, plb=source)
        matches = Match.objects.filter(q)
        if matches.exists():
            weight = matches.aggregate(Sum('sca'))['sca__sum']
            weight += matches.aggregate(Sum('scb'))['scb__sum']
            cur.execute('''INSERT INTO edges VALUES (:source, :target, :weight)''',\
                    {'source': source.id, 'target': target.id, 'weight': weight})

# Write to file
db.commit()
