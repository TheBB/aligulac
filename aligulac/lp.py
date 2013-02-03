#!/usr/bin/python

'''
This is a quick script to easily set Liquipedia links.
'''

import os, sys
from urllib2 import urlopen, Request

# Without this, Django imports won't work correctly
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "aligulac.settings")

from ratings.tools import find_player

# Use the regular search tool to find the player
player = find_player(sys.argv[1:-1])

# There can only be one
if player.count() > 1:
    print 'Player not unique, add more information'
    sys.exit(1)
elif player.count() < 1:
    print 'Player not found'
    sys.exit(1)
else:
    player = player[0]

# Write to database
p.lp_name = sys.argv[-1]
p.save()
