#!/usr/bin/env python3

from datetime import datetime
from itertools import combinations
import os

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'aligulac.settings')

from django.db.models import F

from ratings.models import (
    Period,
    Player,
    Rating,
)
from ratings.tools import filter_active

# This is the benchmark position on the rating list. Above, players will gain domination points.
LIMIT = 7

# Nothing counts before here.
FIRST_PERIOD = 25

# {{{ Evaluate the domination scores
print('[%s] Erasing domination scores' % str(datetime.now()), flush=True)
Rating.objects.update(domination=None)

print('[%s] Reevaluating domination scores' % str(datetime.now()), flush=True)
for period in Period.objects.filter(computed=True, id__gte=FIRST_PERIOD):
    benchmark = filter_active(period.rating_set.all()).order_by('-rating')[LIMIT-1].rating
    filter_active(period.rating_set.all()).update(domination=F('rating')-benchmark)
# }}}

# {{{ Hall of fame
print('[%s] Reevaluating hall of fame' % str(datetime.now()), flush=True)
for player in Player.objects.all():
    ratings = list(
        player.rating_set.filter(period__id__gte=FIRST_PERIOD)
            .order_by('period__id')
            .values('domination', 'period__id')
    )

    if len(ratings) == 0:
        continue

    # {{{ Collect a list of indices where the domination switches sign (always pick the positive side)
    inds = set()
    for i in range(1, len(ratings)):
        if ratings[i]['domination'] is None or ratings[i-1]['domination'] is None:
            continue
        if ratings[i]['domination'] * ratings[i-1]['domination'] < 0:
            inds.add(i if ratings[i]['domination'] > 0 else i-1)
    if ratings[0]['domination'] is not None and ratings[0]['domination'] > 0:
        inds.add(0)
    if ratings[-1]['domination'] is not None and ratings[-1]['domination'] > 0:
        inds.add(len(ratings) - 1)
    inds = sorted(list(inds))
    # }}}

    # {{{ Try out combinations of start and end indices to find the optimal choice
    dom, init, fin = 0, None, None
    for i1, i2 in combinations(inds, 2):
        d = sum([r['domination'] for r in ratings[i1:i2+1] if r['domination'] != None])
        if d > dom:
            dom, init, fin = d, i1, i2

    # If no range was found with positive domination, pick the least negative
    if init is None:
        init, _ = min(enumerate(ratings), key=lambda e: e[1]['domination'] or 10000)
        fin = init
        dom = ratings[init]['domination']
    # }}}

    player.dom_val = dom
    player.dom_start_id = init + FIRST_PERIOD
    player.dom_end_id = fin + FIRST_PERIOD + 1
    player.save()
# }}}
