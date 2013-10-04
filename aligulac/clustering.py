#!/usr/bin/env python3

# {{{ Imports
import os

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'aligulac.settings')

from django.db import connection

from ratings.models import Player

from countries import data
# }}}

#cur = connection.cursor()

#cur.execute('''
    #SELECT
        #pa.id,
        #pa.tag,
        #pb.id,
        #pb.tag,
        #(SELECT SUM(sca) + SUM(scb)
         #FROM match
         #WHERE (pla_id=pa.id AND plb_id=pb.id) OR (pla_id=pb.id AND plb_id=pa.id)
        #) AS games
    #FROM player AS pa CROSS JOIN player AS pb
    #WHERE 
        #EXISTS (SELECT 1 FROM match WHERE (pla_id=pa.id AND plb_id=pb.id) OR (pla_id=pb.id AND plb_id=pa.id))
        #AND (pa.id > pb.id)
#''')

#rows = cur.fetchall()

#with open('clusters.abc', 'w') as f:
    #for row in rows:
        #row[1] = row[1].replace(' ', '_')
        #row[3] = row[3].replace(' ', '_')
        #f.write('%i-%s %i-%s %i\n' % row)

countries = dict((p['id'], p['country']) for p in Player.objects.all().values('id', 'country'))
clusters = []

with open('clusters.out') as f:
    lines = f.readlines()
    for line in lines:
        cluster = {}
        for player in line.split('\t'):
            id = int(player.split('-')[0])
            try:
                cluster[countries[id]] += 1
            except:
                cluster[countries[id]] = 1
        clusters.append(cluster)

i = 1
for cluster in clusters:
    countries = sorted(cluster.keys(), key=lambda c: cluster[c], reverse=True)
    print('Cluster %i (%i players):' % (i, sum(cluster.values())))
    for c in countries:
        print('%4i: %s' % (cluster[c], data.ccn_to_cn[data.cca2_to_ccn[c]] if c else 'None'))
    print('')

    i += 1
