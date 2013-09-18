#!/usr/bin/env python3

from datetime import datetime
from itertools import combinations
import os
from random import shuffle
import sys

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'aligulac.settings')

from aligulac.tools import get_latest_period

from ratings.models import (
    Group,
    Rating,
)
from ratings.tools import filter_active

from simul.formats.teamak import TeamAK
from simul.formats.teampl import TeamPL
from simul.playerlist import make_player

print('[%s] Updating team ratings' % str(datetime.now()))

# {{{ Update ratings
curp = get_latest_period()
for team in Group.objects.filter(active=True, is_team=True):
    ratings = filter_active(Rating.objects.filter(
        period=curp,
        player__groupmembership__group=team,
        player__groupmembership__current=True,
        player__groupmembership__playing=True,
    )).order_by('-rating')

    if ratings.count() >= 5:
        team.meanrating = sum([r.rating for r in ratings[:5]]) / 5
    else:
        team.meanrating = -10
    team.save()
# }}}
