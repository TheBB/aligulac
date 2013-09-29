#!/usr/bin/env python3

# {{{ Imports
import os

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'aligulac.settings')

from datetime import datetime
from math import sqrt
from numpy import array
import sys

from django.db import connection
from django.db.models import Q

from aligulac.tools import etn
from aligulac.settings import (
    DECAY_DEV,
    INACTIVE_THRESHOLD,
    INIT_DEV,
    OFFLINE_WEIGHT,
    start_rating,
)

from rating import (
    performance,
    update,
)

from ratings.models import (
    Match,
    P,
    Period,
    Player,
    Rating,
    T,
    Z,
)
from ratings.tools import (
    filter_active,
    cdf,
)
# }}}

# {{{ Initialize periods
try:
    period = Period.objects.get(id=sys.argv[1])
except:
    print('[%s] No such period' % str(datetime.now()), flush=True)
    sys.exit(1)

print('[{0}] Recomputing #{1} ({2} -> {3})'.format(str(datetime.now()), period.id, period.start, period.end),
      flush=True)

if Period.objects.filter(id__lt=period.id).filter(Q(computed=False) | Q(needs_recompute=True)).exists():
    print('[%s] Earlier period not refreshed. Aborting.' % str(datetime.now()), flush=True)
    sys.exit(1)

prev = etn(lambda: Period.objects.get(id=period.id-1))
# }}}

# {{{ Get players
players = {}

if prev:
    for r in Rating.objects.filter(period=prev).select_related('player').prefetch_related('prevrating'):
        players[r.player_id] = {
            'player': r.player,
            'rating': r,
            'prev_ratings': { 'M': r.rating, 'P': r.rating_vp, 'T': r.rating_vt, 'Z': r.rating_vz },
            'prev_devs': { 'M': r.dev, 'P': r.dev_vp, 'T': r.dev_vt, 'Z': r.dev_vz },
            'opp_c': [], 'opp_r': [], 'opp_d': [], 'wins': [], 'losses': [],
        }

new_players = (
    Player.objects.filter(Q(match_pla__period=period) | Q(match_plb__period=period))
        .exclude(id__in=players.keys())
)

for p in new_players:
    players[p.id] = {
        'player': p,
        'rating': None,
        'prev_ratings': { 'M': start_rating(p.country, period.id), 'P': 0.0, 'T': 0.0, 'Z': 0.0 },
        'prev_devs': { 'M': INIT_DEV, 'P': INIT_DEV, 'T': INIT_DEV, 'Z': INIT_DEV },
        'opp_c': [], 'opp_r': [], 'opp_d': [], 'wins': [], 'losses': [],
    }
# }}}

# {{{ Decay all ratings
for p in players.values():
    for r in p['prev_devs']:
        p['prev_devs'][r] = min(sqrt(p['prev_devs'][r]**2 + DECAY_DEV**2), INIT_DEV)
# }}}

# {{{ Collect match information
ngames = 0

for m in Match.objects.filter(period=period).select_related('pla','plb'):
    rca = [m.rca] if m.rca in 'PTZ' else 'PTZ'
    rcb = [m.rcb] if m.rcb in 'PTZ' else 'PTZ'
    weight = 1/len(rca)/len(rcb) * (OFFLINE_WEIGHT if m.offline else 1)

    for ra in rca:
        for rb in rcb:
            players[m.pla_id]['opp_c'].append('PTZ'.index(rb))
            players[m.pla_id]['opp_r'].append(
                players[m.plb_id]['prev_ratings']['M'] + players[m.plb_id]['prev_ratings'][ra])
            players[m.pla_id]['opp_d'].append(sqrt(
                players[m.plb_id]['prev_devs']['M']**2 + players[m.plb_id]['prev_devs'][ra]**2
            ))
            players[m.pla_id]['wins'].append(m.sca * weight)
            players[m.pla_id]['losses'].append(m.scb * weight)

            players[m.plb_id]['opp_c'].append('PTZ'.index(ra))
            players[m.plb_id]['opp_r'].append(
                players[m.pla_id]['prev_ratings']['M'] + players[m.pla_id]['prev_ratings'][rb])
            players[m.plb_id]['opp_d'].append(sqrt(
                players[m.pla_id]['prev_devs']['M']**2 + players[m.pla_id]['prev_devs'][rb]**2
            ))
            players[m.plb_id]['wins'].append(m.scb * weight)
            players[m.plb_id]['losses'].append(m.sca * weight)

    ngames += m.sca + m.scb
# }}}

print('[%s] Initialized %i players and %i games' % (str(datetime.now()), len(players), ngames), flush=True)

# {{{ Compute new ratings, devs and performances
for p in players.values():
    new_ratings, new_devs = update(
        array(
            [p['prev_ratings']['M'], p['prev_ratings']['P'], 
            p['prev_ratings']['T'], p['prev_ratings']['Z']]
        ),
        array([p['prev_devs']['M'], p['prev_devs']['P'], p['prev_devs']['T'], p['prev_devs']['Z']]),
        array(p['opp_r']), array(p['opp_d']), array(p['opp_c']), 
        array(p['wins']), array(p['losses']), p['player'].tag, False
    )

    perfs = performance(
        array(p['opp_r']), array(p['opp_d']), array(p['opp_c']), array(p['wins']), array(p['losses'])
    )

    p.update({
        'new_ratings': { 'M': new_ratings[0], 'P': new_ratings[1], 'T': new_ratings[2], 'Z': new_ratings[3] },
        'new_devs': { 'M': new_devs[0], 'P': new_devs[1], 'T': new_devs[2], 'Z': new_devs[3] },
        'perfs': { 'M': perfs[0], 'P': perfs[1], 'T': perfs[2], 'Z': perfs[3] },
    })
# }}}

# {{{ Prepare to commit
extant_ids = {r.player_id for r in Rating.objects.filter(period=period)}
computed_ids = {p['player'].id for p in players.values()}
insert_ids = computed_ids - extant_ids
update_ids = computed_ids & extant_ids
delete_ids = extant_ids - computed_ids
# }}}

# {{{ Delete extant ratings that shouldn't be there
Match.objects.filter(rta__period=period, rta__player_id__in=delete_ids).update(rta=None)
Match.objects.filter(rtb__period=period, rtb__player_id__in=delete_ids).update(rtb=None)
Rating.objects.filter(prev__period=period, prev__player_id__in=delete_ids).update(prev=None)
Rating.objects.filter(period=period, player_id__in=delete_ids).delete()
# }}}

# {{{ Update extant ratings
cur = connection.cursor()
cur.execute('BEGIN')
cur.execute(
    'CREATE TEMPORARY TABLE temp_rating ( '
    '    player_id integer PRIMARY KEY, '
    '    rating double precision,    rating_vp double precision, '
    '    rating_vt double precision, rating_vz double precision, '
    '    dev double precision,    dev_vp double precision, '
    '    dev_vt double precision, dev_vz double precision, '
    '    comp_rat double precision,    comp_rat_vp double precision, '
    '    comp_rat_vt double precision, comp_rat_vz double precision, '
    '    decay integer'
    ') ON COMMIT DROP'
)
cur.execute('INSERT INTO temp_rating VALUES ' + ', '.join(
    str((
        p['player'].id,
        p['new_ratings']['M'], p['new_ratings']['P'], p['new_ratings']['T'], p['new_ratings']['Z'], 
        p['new_devs']['M'], p['new_devs']['P'], p['new_devs']['T'], p['new_devs']['Z'], 
        p['perfs']['M'], p['perfs']['P'], p['perfs']['T'], p['perfs']['Z'], 
        p['rating'].decay + 1 if p['rating'] and len(p['wins']) == 0 else 0
    )) for p in players.values() if p['player'].id in update_ids)
)
cur.execute(
    'UPDATE rating AS r SET '
    '    rating=t.rating, rating_vp=t.rating_vp, rating_vt=t.rating_vt, rating_vz=t.rating_vz, '
    '    dev=t.dev, dev_vp=t.dev_vp, dev_vt=t.dev_vt, dev_vz=t.dev_vz, '
    '    comp_rat=t.comp_rat, comp_rat_vp=t.comp_rat_vp, '
    '    comp_rat_vt=t.comp_rat_vt, comp_rat_vz=t.comp_rat_vz, '
    '    decay=t.decay '
    'FROM temp_rating AS t WHERE r.player_id=t.player_id AND r.period_id=%i' % period.id
)
cur.execute('COMMIT')
# }}}

# {{{ Insert new ratings
Rating.objects.bulk_create([Rating(
    period       = period,
    player       = p['player'],
    prev         = p['rating'],
    rating       = p['new_ratings']['M'],
    rating_vp    = p['new_ratings']['P'],
    rating_vt    = p['new_ratings']['T'],
    rating_vz    = p['new_ratings']['Z'],
    dev          = p['new_devs']['M'],
    dev_vp       = p['new_devs']['P'],
    dev_vt       = p['new_devs']['T'],
    dev_vz       = p['new_devs']['Z'],
    comp_rat     = p['perfs']['M'],
    comp_rat_vp  = p['perfs']['P'],
    comp_rat_vt  = p['perfs']['T'],
    comp_rat_vz  = p['perfs']['Z'],
    bf_rating    = p['new_ratings']['M'],
    bf_rating_vp = p['new_ratings']['P'],
    bf_rating_vt = p['new_ratings']['T'],
    bf_rating_vz = p['new_ratings']['Z'],
    bf_dev       = p['new_devs']['M'],
    bf_dev_vp    = p['new_devs']['P'],
    bf_dev_vt    = p['new_devs']['T'],
    bf_dev_vz    = p['new_devs']['Z'],
    decay        = 0,
) for p in players.values() if p['player'].id in insert_ids])

if insert_ids:
    str_ids = {str(i) for i in insert_ids}
    cur.execute('''
        UPDATE match SET rta_id =
            (SELECT id FROM rating 
              WHERE rating.player_id=match.pla_id
                AND rating.period_id=%i
            )
         WHERE period_id=%i AND pla_id IN (%s)'''
        % (period.id, period.id+1, ','.join(str_ids))
    )
    cur.execute('''
        UPDATE match SET rtb_id =
            (SELECT id FROM rating 
              WHERE rating.player_id=match.plb_id
                AND rating.period_id=%i
            )
         WHERE period_id=%i AND plb_id IN (%s)'''
        % (period.id, period.id+1, ','.join(str_ids))
    )
# }}}

# {{{ Bookkeeping
Match.objects.filter(period=period).update(treated=True)

def mean(a):
    return sum([f.rating for f in a])/len(a)
rp = mean(filter_active(Rating.objects.filter(period=period, player__race=P)).order_by('-rating')[:5])
rt = mean(filter_active(Rating.objects.filter(period=period, player__race=T)).order_by('-rating')[:5])
rz = mean(filter_active(Rating.objects.filter(period=period, player__race=Z)).order_by('-rating')[:5])
period.dom_p = cdf(rp-rt) + cdf(rp-rz)
period.dom_t = cdf(rt-rp) + cdf(rt-rz)
period.dom_z = cdf(rz-rp) + cdf(rz-rt)

period.num_retplayers = sum([1 if p['rating'] and len(p['wins']) > 0 else 0 for p in players.values()])
period.num_newplayers = sum([1 if not p['rating'] and len(p['wins']) > 0 else 0 for p in players.values()])
period.num_games = ngames
period.computed = True
period.needs_recompute = False
period.save()

Rating.objects.filter(period=period).update(
    position=None, position_vp=None, position_vt=None, position_vz=None
)
cur = connection.cursor()
cur.execute('''
    UPDATE rating
    SET position=r.rnk, position_vp=r.rnk_vp, position_vt=r.rnk_vt, position_vz=r.rnk_vz
    FROM (
        SELECT id,
            rank() OVER (ORDER BY rating DESC) AS rnk,
            rank() OVER (ORDER BY rating + rating_vp DESC) AS rnk_vp,
            rank() OVER (ORDER BY rating + rating_vt DESC) AS rnk_vt,
            rank() OVER (ORDER BY rating + rating_vz DESC) AS rnk_vz
        FROM rating WHERE period_id=%i AND decay < %i
    ) r
    WHERE rating.id = r.id''' % (period.id, INACTIVE_THRESHOLD)
)
# }}}

print(
    '[%s] Deleted: %i, Updated: %i, Inserted: %i'
    % (str(datetime.now()), len(delete_ids), len(update_ids), len(insert_ids)),
    flush=True
)
