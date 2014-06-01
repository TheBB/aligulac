#!/usr/bin/env python3

# {{{ Imports
import os

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'aligulac.settings')

from datetime import datetime
import math
import subprocess
import sys

from django.db import connection
from django.db.models import Avg, Min, Max
from django.db.transaction import commit_on_success

from ratings.models import (
    Cluster,
    ClusterConnection,
    Match,
    Rating,
    Period,
    Player,
)
# }}}

period = Period.objects.get(id=sys.argv[1])

print('[%s] Getting edge weights' % str(datetime.now()))

cur = connection.cursor()
pid, lim = period.id, period.id - 30
q = Match.objects.filter(period_id__gt=lim, period_id__lte=pid)
# cur.execute('''
#     SELECT
#         pa.id,
#         pa.tag,
#         pb.id,
#         pb.tag,
#         (SELECT SUM(EXP((period_id-%i)/3.0) * (sca + scb))
#          FROM match
#          WHERE ((pla_id=pa.id AND plb_id=pb.id) OR (pla_id=pb.id AND plb_id=pa.id))
#            AND period_id <= %i AND period_id >= %i
#         ) AS games
#     FROM player AS pa CROSS JOIN player AS pb
#     WHERE 
#         EXISTS (SELECT 1 FROM match 
#                 WHERE ((pla_id=pa.id AND plb_id=pb.id) OR (pla_id=pb.id AND plb_id=pa.id))
#                   AND period_id <= %i AND period_id >= %i
#                )
#         AND (pa.id > pb.id)
# ''' % (pid, pid, lim, pid, lim))
# rows = cur.fetchall()

# Indexed by pla, plb
def swap(pt):
    if pt[0] > pt[1]:
        return (pt[1], pt[0])
    return pt
class Matrix(dict):
    def __contains__(self, pt):
        super().__contains__(swap(pt))
    def __getitem__(self, pt):
        if pt not in self:
            return 0
        return super().__getitem__(swap(pt))
    def __setitem__(self, pt, value):
        super().__setitem__(swap(pt), value)
match_matrix = Matrix()

print('[%s] Building matrix' % str(datetime.now()))
for m in q:
    match_matrix[m.pla_id, m.plb_id] += (
        (m.sca + m.scb) * math.exp((m.period_id - pid) / 3.0)
    )

print('[%s] Writing file' % str(datetime.now()))
with open('/tmp/clusters.abc', 'w') as f:
    for (pla, plb), value in match_matrix.items():
        f.write('%i %i %f\n' % (pla, plb, value))

print('[%s] Markov clustering' % str(datetime.now()))

with open(os.devnull, 'wb') as devnull:
    subprocess.check_call([
        'mcl', '/tmp/clusters.abc', '--abc', '-I', '2.3', '-o', '/tmp/clusters.out'
    ], stdout=devnull, stderr=subprocess.STDOUT)

clusters = dict()
cluster_index_set = set()
with open('/tmp/clusters.out') as f:
    lines = f.readlines()
    cluster = 1
    for line in lines:
        current_cluster = set()
        for player in line.split('\t'):
            id = int(player.strip())
            current_cluster.add(id)
            cluster_index_set.add(cluster)
        clusters[cluster] = current_cluster
        cluster += 1

print('[%s] Deleting old clusters' % str(datetime.now()))
ClusterConnection.objects.filter(cluster__period_id=pid).delete()
Cluster.objects.filter(period_id=pid).delete()

print('[%s] Updating database (%i clusters)' % (str(datetime.now()), cluster-1))
period = Period.objects.get(id=pid)

cluster_objects = dict()
@commit_on_success
def create_clusters():
    for cluster_index in cluster_index_set:
        c = Cluster(period=period, index=cluster_index)
        c.save()
        cluster_objects[cluster_index] = c
create_clusters()

@commit_on_success
def update_clusters():
    for cluster_index, cluster in clusters.items():
        for player in cluster:
            conn = ClusterConnection(
                cluster=cluster_objects[cluster_index],
                player_id=player
            )
            conn.save()
update_clusters()

print('[%s] Calculating ratings' % (datetime.now(),))
@commit_on_success
def calculate_ratings():
    for cluster_index, cluster in cluster_objects.items():
        q = Rating.objects.filter(
            player__in=clusters[cluster_index],
            period=pid - 1
        ).aggregate(Avg('rating'), Min('rating'), Max('rating'))

        cluster.max_rating = q['rating__max']
        cluster.mean_rating = q['rating__avg']
        cluster.min_rating = q['rating__min']

        cluster.save()
calculate_ratings()
