#!/usr/bin/python

'''
This script deletes an event, and transfers all the children to the parent event.

./deleteevent.py <event_id>
'''

import os, datetime, re, sys
from urllib2 import urlopen, Request

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "aligulac.settings")

from django.db.models import F
from ratings.models import Period, Player, Rating, Match, Event

try:
    event = Event.objects.get(id=int(sys.argv[1]))
except:
    print 'No such event'
    sys.exit(0)

parent = event.parent
if parent == None:
    print 'No parent'
    sys.exit(0)

inp = raw_input('Delete \'%s\'? ' % str(event))

if inp == 'yes':
    event.event_set.all().update(parent=parent)
    Event.objects.filter(lft__gt=event.lft, lft__lt=event.rgt).update(lft=F('lft')-1)
    Event.objects.filter(rgt__gt=event.lft, rgt__lt=event.rgt).update(rgt=F('rgt')-1)
    Event.objects.filter(lft__gt=event.rgt).update(lft=F('lft')-2)
    Event.objects.filter(rgt__gt=event.rgt).update(rgt=F('rgt')-2)
    event.delete()
