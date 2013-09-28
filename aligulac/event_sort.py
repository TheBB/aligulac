#!/usr/bin/env python3

# {{{ Imports
import os

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'aligulac.settings')

from itertools import chain

from django.db import connection, transaction

from ratings.models import Event
# }}}

roots = Event.objects.filter(parent__isnull=True).order_by('fullname').values('id')
next_ids = [e['id'] for e in roots]
id_pile = [{'root': next_ids}]

while len(next_ids) > 0:
    children = Event.objects.prefetch_related('parent_event').in_bulk(next_ids)
    id_pile.append({p.id: [e.id for e in p.parent_event.all()] for p in children.values()})
    next_ids = list(chain(*id_pile[-1].values()))

id_pile = id_pile[:-1]

while len(id_pile) > 1:
    top = id_pile[-2]
    bottom = id_pile[-1]
    for tid, pre_list in top.items():
        temp = [((cid,), bottom[cid]) for cid in pre_list]
        top[tid] = list(chain(*chain(*temp)))
    id_pile = id_pile[:-1]

order = id_pile[0]['root']

cur = connection.cursor()
cur.execute('BEGIN')
cur.execute(
    'CREATE TEMPORARY TABLE temp_event_order (id integer PRIMARY KEY, idx integer) '
    'ON COMMIT DROP'
)
cur.execute('INSERT INTO temp_event_order VALUES ' + ', '.join(str((i, idx)) for idx, i in enumerate(order)))
cur.execute('UPDATE event AS e SET idx = t.idx FROM temp_event_order AS t WHERE e.id = t.id')
cur.execute('COMMIT')
