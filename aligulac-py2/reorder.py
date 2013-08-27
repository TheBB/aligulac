#!/usr/bin/python
import os, datetime, re, sys
from urllib2 import urlopen, Request

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "aligulac.settings")

from ratings.models import Period, Player, Rating, Match, Event

try:
    event = Event.objects.get(id=int(sys.argv[1]))
    children = list(Event.objects.filter(parent=event).order_by('lft'))
    print 'Children of', event
except:
    event = None
    children = list(Event.objects.filter(parent__isnull=True).order_by('lft'))
    print 'Roots'

for i in range(0, len(children)):
    print '%i: %s' % (i+1, children[i].name)

ok = False
order = []
while not ok:
    try:
        q = raw_input('New order: ')
        if q == 'exit':
            break
        order = [int(s.strip()) for s in q.split(',')]
    except:
        print 'Improper order'
        continue

    if len(order) != len(children) or len(set(order)) != len(children)\
            or min(order) < 1 or max(order) > len(children):
        print 'Improper order'
    else:
        ok = True

if ok:
    if event != None:
        nextlft = event.lft + 1
    else:
        nextlft = min([e.lft for e in children])

    for oldi in order:
        child = children[oldi-1]
        child.slide(nextlft - child.lft)
        nextlft = child.rgt + 1
