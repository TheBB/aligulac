#!/usr/bin/env python3

from datetime import datetime
import os

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'aligulac.settings')
import django
django.setup()

from django.db import connection, transaction
from django.db.models import F

from aligulac.settings import (
    DECAY_DEV,
    INIT_DEV,
    MIN_DEV,
)

from ratings.models import (
    Period,
    Rating,
)

print('[%s] Backwards smoothing' % str(datetime.now()), flush=True)

# {{{ Copy data for the last period
last = Period.objects.filter(computed=True).latest('id')
Rating.objects.filter(period=last).update(
    bf_rating=F('rating'),
    bf_rating_vp=F('rating_vp'),
    bf_rating_vt=F('rating_vt'),
    bf_rating_vz=F('rating_vz'),
    bf_dev=F('dev'),
    bf_dev_vp=F('dev_vp'),
    bf_dev_vt=F('dev_vt'),
    bf_dev_vz=F('dev_vz'),
)
# }}}

cur = connection.cursor()

for period_id in range(last.id-1, 0, -1):
    print('[%s] Smoothing period %i' % (str(datetime.now()), period_id), flush=True)

    # {{{ Update RDs
    with transaction.atomic():
        cur.execute('''
        UPDATE rating
           SET bf_dev=i.d, bf_dev_vp=i.dvp, bf_dev_vt=i.dvt, bf_dev_vz=i.dvz
          FROM (
              SELECT m.id AS id,
                     1/SQRT(1/POW(m.dev,2)+1/(POW(p.bf_dev,2)+POW({dec},2))) AS d,
                     1/SQRT(1/POW(m.dev_vp,2)+1/(POW(p.bf_dev_vp,2)+POW({dec},2))) AS dvp,
                     1/SQRT(1/POW(m.dev_vt,2)+1/(POW(p.bf_dev_vt,2)+POW({dec},2))) AS dvt,
                     1/SQRT(1/POW(m.dev_vz,2)+1/(POW(p.bf_dev_vz,2)+POW({dec},2))) AS dvz
                FROM rating m, rating p
               WHERE p.player_id = m.player_id AND p.period_id = {pid} AND m.period_id = {mid}
          ) i
         WHERE rating.id = i.id'''
         .format(dec=DECAY_DEV, pid=period_id+1, mid=period_id)
        )
    # }}}

    # {{{ Update ratings
    with transaction.atomic():
        cur.execute('''
        UPDATE rating
           SET bf_rating=i.r, bf_rating_vp=i.rvp, bf_rating_vt=i.rvt, bf_rating_vz=i.rvz
          FROM (
              SELECT m.id AS id,
                 POW(m.bf_dev,2) *
                    (m.rating/POW(m.dev,2)+p.rating/(POW(p.bf_dev,2)+POW({dec},2))) AS r,
                 POW(m.bf_dev_vp,2) *
                    (m.rating_vp/POW(m.dev_vp,2)+p.rating_vp/(POW(p.bf_dev_vp,2)+POW({dec},2))) AS rvp,
                 POW(m.bf_dev_vt,2) *
                    (m.rating_vt/POW(m.dev_vt,2)+p.rating_vt/(POW(p.bf_dev_vt,2)+POW({dec},2))) AS rvt,
                 POW(m.bf_dev_vz,2) *
                    (m.rating_vz/POW(m.dev_vz,2)+p.rating_vz/(POW(p.bf_dev_vz,2)+POW({dec},2))) AS rvz
                FROM rating m, rating p
               WHERE p.player_id = m.player_id AND p.period_id = {pid} AND m.period_id = {mid}
          ) i
         WHERE rating.id = i.id'''
        .format(dec=DECAY_DEV, pid=period_id+1, mid=period_id)
        )
    # }}}

    # {{{ Enforce RD between min and max (init)
    with transaction.atomic():
        cur.execute('''
        UPDATE rating
           SET bf_dev=i.d, bf_dev_vp=i.dvp, bf_dev_vt=i.dvt, bf_dev_vz=i.dvz
          FROM (
              SELECT m.id AS id,
                     LEAST(GREATEST(m.bf_dev, {min}), {init}) AS d,
                     LEAST(GREATEST(m.bf_dev_vp, {min}), {init}) AS dvp,
                     LEAST(GREATEST(m.bf_dev_vt, {min}), {init}) AS dvt,
                     LEAST(GREATEST(m.bf_dev_vz, {min}), {init}) AS dvz
                FROM rating m
               WHERE m.period_id = {mid}
          ) i
         WHERE rating.id = i.id'''
        .format(min=MIN_DEV, init=INIT_DEV, mid=period_id)
        )
    # }}}

    # {{{ Subtract mean to renormalize
    with transaction.atomic():
        cur.execute('''
        UPDATE rating
           SET bf_rating    = bf_rating    + i.delta,
               bf_rating_vp = bf_rating_vp - i.delta,
               bf_rating_vt = bf_rating_vt - i.delta,
               bf_rating_vz = bf_rating_vz - i.delta
          FROM (
              SELECT m.id AS id,
                     (m.bf_rating_vp + m.bf_rating_vt + m.bf_rating_vz) / 3 AS delta
                FROM rating m
               WHERE m.period_id = {mid}
          ) i
         WHERE rating.id = i.id'''
        .format(mid=period_id)
        )
    # }}}
