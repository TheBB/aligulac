#!/usr/bin/env python3

import os

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'aligulac.settings')

from datetime import date, datetime
import sys

from django.db.models import Q

from aligulac.settings import PROJECT_PATH

from ratings.models import Period

if 'all' in sys.argv:
    earliest = Period.objects.earliest('id')
else:
    try:
        earliest = (
            Period.objects.filter(Q(needs_recompute=True) | Q(match__treated=False))
                .filter(start__lte=date.today()).earliest('id')
        )
    except:
        print('[%s] Nothing to do' % str(datetime.now()))
        os.system('touch ' + PROJECT_PATH + 'update')
        sys.exit(0)

latest = Period.objects.filter(start__lte=date.today()).latest('id')

print('[%s] Recomputing periods %i through %i' % (str(datetime.now()), earliest.id, latest.id))

for i in range(earliest.id, latest.id+1):
    os.system(PROJECT_PATH + 'period.py %i' % i)

if not 'debug' in sys.argv:
    os.system(PROJECT_PATH + 'smoothing.py')
    os.system(PROJECT_PATH + 'domination.py')
    os.system(PROJECT_PATH + 'teamranks.py ak')
    os.system(PROJECT_PATH + 'teamranks.py pl')

    print('[%s] Updating MC numbers' % str(datetime.now()))
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

    os.system('touch ' + PROJECT_PATH + 'update')

print('[%s] Finished' % str(datetime.now()))
