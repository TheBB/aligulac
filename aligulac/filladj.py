#!/usr/bin/python

import os
import sys

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "aligulac.settings")

from ratings.models import Event, EventAdjacency

EventAdjacency.objects.all().delete()

level = list(Event.objects.filter(parent__isnull=True))
l = 0
while len(level) > 0:
    print('Level: %i (%i events)' % (l, len(level)))
    next_level = []
    for p in level:
        EventAdjacency.objects.create(parent=p, child=p, distance=0)
        children = Event.objects.filter(parent=p)
        for c in children:
            EventAdjacency.objects.create(parent=p, child=c, distance=1)
            next_level.append(c)
    level = next_level
    l += 1

for d in range(1,8):
    print('Creating links with distance %i' % (d+1))
    for top in EventAdjacency.objects.filter(distance=d):
        bottom = EventAdjacency.objects.filter(parent_id=top.child_id, distance=1).values('child_id')
        for c in bottom.values():
            EventAdjacency.objects.create(parent_id=top.parent_id, child_id=c['child_id'], distance=d+1)

