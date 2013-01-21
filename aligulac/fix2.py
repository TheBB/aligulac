#!/usr/bin/python
import os
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "aligulac.settings")

from itertools import combinations
from random import shuffle

from ratings.models import Period, Player, Rating, Match, Team
from simul.playerlist import make_player
from simul.formats.teampl import TeamPL
from simul.formats.match import Match

from numpy import *
from rating import update

for player in Player.objects.filter(dom_val__isnull=False, dom_start__isnull=False,\
        dom_end__isnull=False, dom_val__gt=-0).order_by('-dom_val'):
    print player.tag, player.dom_val, player.dom_start.id, player.dom_end.id
