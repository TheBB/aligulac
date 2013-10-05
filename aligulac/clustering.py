#!/usr/bin/env python3

# {{{ Imports
import os

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'aligulac.settings')

from datetime import datetime
import subprocess
import sys

from django.db import connection

from ratings.models import (
    Period,
    Player,
)
# }}}

period = Period.objects.get(id=sys.argv[1])

print('[%s] Getting edge weights' % str(datetime.now()))

cur = connection.cursor()
pid, lim = period.id, period.id - 30
cur.execute('''
    SELECT
        pa.id,
        pa.tag,
        pb.id,
        pb.tag,
        (SELECT SUM(EXP((period_id-%i)/3.0) * (sca + scb))
         FROM match
         WHERE ((pla_id=pa.id AND plb_id=pb.id) OR (pla_id=pb.id AND plb_id=pa.id))
           AND period_id <= %i AND period_id >= %i
        ) AS games
    FROM player AS pa CROSS JOIN player AS pb
    WHERE 
        EXISTS (SELECT 1 FROM match 
                WHERE ((pla_id=pa.id AND plb_id=pb.id) OR (pla_id=pb.id AND plb_id=pa.id))
                  AND period_id <= %i AND period_id >= %i
               )
        AND (pa.id > pb.id)
''' % (pid, pid, lim, pid, lim))
rows = cur.fetchall()

with open('/tmp/clusters.abc', 'w') as f:
    for row in rows:
        row = list(row)
        row[1] = row[1].replace(' ', '_')
        row[3] = row[3].replace(' ', '_')
        f.write('%i-%s %i-%s %f\n' % tuple(row))

print('[%s] Markov clustering' % str(datetime.now()))

with open(os.devnull, 'wb') as devnull:
    subprocess.check_call([
        '/home/efonn/local/mcl/bin/mcl', '/tmp/clusters.abc', '--abc', '-I', '2.3', '-o', '/tmp/clusters.out'
    ], stdout=devnull, stderr=subprocess.STDOUT)

clusters = []
with open('/tmp/clusters.out') as f:
    lines = f.readlines()
    cluster = 1
    for line in lines:
        for player in line.split('\t'):
            id = int(player.split('-')[0])
            clusters.append((id, cluster))
        cluster += 1

print('[%s] Updating database (%i clusters)' % (str(datetime.now()), cluster-1))

cur.execute('BEGIN')
cur.execute('''
    CREATE TEMPORARY TABLE temp_rating_clusters (
        player_id integer PRIMARY KEY,
        cluster integer
    ) ON COMMIT DROP
''')
cur.execute('INSERT INTO temp_rating_clusters VALUES ' + ', '.join(str(c) for c in clusters))
cur.execute('''
    UPDATE rating SET cluster=t.cluster
    FROM temp_rating_clusters AS t WHERE rating.player_id=t.player_id AND rating.period_id=%i
''' % pid)
cur.execute('COMMIT')
