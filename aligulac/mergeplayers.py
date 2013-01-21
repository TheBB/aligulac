#!/usr/bin/python
import os, datetime, re, sys
from urllib2 import urlopen, Request

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "aligulac.settings")

from ratings.models import Period, Player, Rating, Match, Event, TeamMembership

#try:
source = Player.objects.get(id=int(sys.argv[1]))
target = Player.objects.get(id=int(sys.argv[2]))

Match.objects.filter(pla=source).update(pla=target)
Match.objects.filter(plb=source).update(plb=target)
Rating.objects.filter(player=source).delete()
TeamMembership.objects.filter(player=source).delete()
source.delete()
#except:
    #print 'Player(s) not found'
