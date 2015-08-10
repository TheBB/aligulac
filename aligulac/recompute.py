#!/usr/bin/env python3

import os

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'aligulac.settings')
import django
django.setup()

from datetime import date, datetime
import itertools
import sys
import subprocess

from django.core.cache import cache
from django.db import connection
from django.db.models import F, Q
from django.db.transaction import atomic

from aligulac.settings import PROJECT_PATH

from ratings.models import Match, Period, Player

print('[%s] Checking for Match <-> Period artifacts... ' % (str(datetime.now())), end="")

q = Match.objects.exclude(period__start__lte=F('date'), period__end__gte=F('date'))

if q.count() > 0:
    print('Found!')
    print('[%s] Fixing artifacts... ' % str(datetime.now()))

    matches = list(q)

    period_set = set()

    @atomic
    def fix_artifacts():
        periods = list(Period.objects.filter(start__lte=datetime.today()))
    
        def get_period(date):
            for period in periods:
                if period.start <= date and period.end >= date:
                    return period

        for match in matches:
            print("    Correcting match: %s" % str(match))
            period_set.add(match.period_id)
        
            target = get_period(match.date)
            
            match.period_id = target.id
            match.save()

            period_set.add(target.id)

    fix_artifacts()

    Period.objects.filter(id__in=period_set).update(needs_recompute=True)
    print('    Done! (%i matches, %i periods)' % (len(matches), len(period_set)))
else:
    print('Done! None found!')

print('[%s] Checking for Match Rating <-> Match Player artifacts... ' % (str(datetime.now())), end="")

q = Match.objects.symmetric_filter(
    ~Q(period__isnull=False, period=F('rta__period') + 1)
)

q2 = Match.objects.filter(
    ~Q(pla=F('rta__player')) |
    ~Q(plb=F('rtb__player'))
)

count = q.count() + q2.count()

if count != 0:
    period_set = set()

    @atomic
    def fix_artifacts():
        print("Found")
        print("[%s] Fixing artifacts..." % str(datetime.now()))
        for m in itertools.chain(q, q2):
            print("    Correcting match: %s" % str(m))
            m.set_ratings()
            m.save()
            period_set.add(m.period_id)

    fix_artifacts()
    Period.objects.filter(id__in=period_set).update(needs_recompute=True)

    print('    Done! (%i matches, %i periods)' % (count, len(period_set)))
else:
    print('Done! None found!')


if 'all' in sys.argv:
    earliest = Period.objects.earliest('id')
else:
    try:
        earliest = (
            Period.objects.filter(Q(needs_recompute=True) | Q(match__treated=False))
                .filter(start__lte=date.today()).earliest('id')
        )
    except:
        print('[%s] Nothing to do' % str(datetime.now()), flush=True)
        subprocess.call(['touch', os.path.join(PROJECT_PATH, 'update')])
        sys.exit(0)

latest = Period.objects.filter(start__lte=date.today()).latest('id')

print('[%s] Recomputing periods %i through %i' % (str(datetime.now()), earliest.id, latest.id), flush=True)

for i in range(earliest.id, latest.id+1):
    subprocess.call([os.path.join(PROJECT_PATH, 'period.py'), str(i)])

if 'debug' not in sys.argv:
    subprocess.call([os.path.join(PROJECT_PATH, 'smoothing.py')])
    subprocess.call([os.path.join(PROJECT_PATH, 'domination.py')])
    subprocess.call([os.path.join(PROJECT_PATH, 'teamranks.py'), 'ak'])
    subprocess.call([os.path.join(PROJECT_PATH, 'teamranks.py'), 'pl'])
    subprocess.call([os.path.join(PROJECT_PATH, 'teamratings.py')])
    subprocess.call([os.path.join(PROJECT_PATH, 'reports.py')])

    print('[%s] Updating MC numbers' % str(datetime.now()), flush=True)
    Player.objects.exclude(id=36).update(mcnum=None)
    Player.objects.filter(id=36).update(mcnum=0)
    g = 0
    while True:
        upd = Player.objects.filter(
            match_pla__offline=True,
            match_pla__plb__mcnum=g,
            mcnum__isnull=True
        ).distinct().update(mcnum=g+1)
        upd += Player.objects.filter(
            match_plb__offline=True,
            match_plb__pla__mcnum=g,
            mcnum__isnull=True
        ).distinct().update(mcnum=g+1)
        if upd == 0:
            break
        g += 1

    print('[%s] Refreshing miscellaneous data' % str(datetime.now()), flush=True)
    cur = connection.cursor()
    cur.execute('UPDATE event SET earliest = (SELECT MIN(date) FROM match JOIN eventadjacency '
                'ON match.eventobj_id=eventadjacency.child_id WHERE eventadjacency.parent_id=event.id)')
    cur.execute('UPDATE event SET latest   = (SELECT MAX(date) FROM match JOIN eventadjacency '
                'ON match.eventobj_id=eventadjacency.child_id WHERE eventadjacency.parent_id=event.id)')
    cur.execute('UPDATE player SET current_rating_id = (SELECT rating.id FROM rating '
                'WHERE rating.period_id=%i AND rating.player_id=player.id)' % latest.id)

    os.system(PROJECT_PATH + 'event_sort.py')

print('[%s] Finished' % str(datetime.now()), flush=True)

subprocess.call(['touch', os.path.join(PROJECT_PATH, 'update')])

cache.clear()
