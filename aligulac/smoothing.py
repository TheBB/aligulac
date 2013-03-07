#!/usr/bin/python

'''
Backwards smoothing.
'''

import os
import sys

from numpy import *

# Required for Django imports to work correctly.
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "aligulac.settings")

from django.db import connection, transaction
from django.db.models import Q, F
from ratings.models import Player, Match, Rating, Event, Period
from aligulac.parameters import RATINGS_DEV_DECAY, RATINGS_INIT_DEV, RATINGS_MIN_DEV

if __name__ == '__main__':
    last = Period.objects.filter(computed=True).order_by('-id')[0]
    Rating.objects.filter(period=last).update(bf_rating=F('rating'), bf_rating_vp=F('rating_vp'),\
            bf_rating_vt=F('rating_vt'), bf_rating_vz=F('rating_vz'), bf_dev=F('dev'), bf_dev_vp=F('dev_vp'),\
            bf_dev_vt=F('dev_vt'), bf_dev_vz=F('dev_vz'))

    cur = connection.cursor()

    for period in range(last.id-1, 0, -1):
        # Update devs
        for tp in ['', '_vp', '_vt', '_vz']:
            cur.execute('''UPDATE ratings_rating AS p, ratings_rating AS m
                        SET m.bf_dev{t} = 1/SQRT(1/POW(m.dev{t},2) + 1/(POW(p.bf_dev{t},2) + POW({dec},2)))
                        WHERE p.player_id=m.player_id AND p.period_id={pid} AND m.period_id={mid}'''\
                                .format(t=tp, dec=RATINGS_DEV_DECAY, pid=period+1, mid=period))
        transaction.commit_unless_managed()

        # Update ratings
        for tp in ['', '_vp', '_vt', '_vz']:
            cur.execute('''UPDATE ratings_rating AS p, ratings_rating AS m
                        SET m.bf_rating{t} = POW(m.bf_dev{t},2)*
                                (m.rating{t}/POW(m.dev{t},2) + p.rating{t}/(POW(p.bf_dev{t},2) + POW({dec},2)))
                        WHERE p.player_id=m.player_id AND p.period_id={pid} AND m.period_id={mid}'''\
                                .format(t=tp, dec=RATINGS_DEV_DECAY, pid=period+1, mid=period))
        transaction.commit_unless_managed()

        # Force devs in the required interval
        for tp in ['', '_vp', '_vt', '_vz']:
            cur.execute('''UPDATE ratings_rating AS m
                        SET m.bf_dev{t} = GREATEST(LEAST(m.bf_dev{t}, {init}), {min})
                        WHERE m.period_id={mid}'''\
                                .format(t=tp, init=RATINGS_INIT_DEV, min=RATINGS_MIN_DEV, mid=period))
        transaction.commit_unless_managed()

        # Renormalize
        cur.execute('''UPDATE ratings_rating AS m
                       SET m.temp = (m.bf_rating_vp+m.bf_rating_vt+m.bf_rating_vz)/3
                       WHERE m.period_id={mid}'''\
                               .format(mid=period))
        transaction.commit_unless_managed()

        cur.execute('''UPDATE ratings_rating AS m
                       SET m.bf_rating    = m.bf_rating    + m.temp,
                           m.bf_rating_vp = m.bf_rating_vp - m.temp,
                           m.bf_rating_vt = m.bf_rating_vt - m.temp,
                           m.bf_rating_vz = m.bf_rating_vz - m.temp
                       WHERE m.period_id={mid}'''\
                               .format(mid=period))
        transaction.commit_unless_managed()
