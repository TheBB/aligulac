#!/usr/bin/python

import os

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'aligulac.settings')

from datetime import date
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
        print('Nothing to do')
        os.system('touch ' + PROJECT_PATH + 'update')
        sys.exit(0)

latest = Period.objects.filter(start__lte=date.today()).latest('id')

print('Recomputing periods %i through %i' % (earliest.id, latest.id))
print('--')

for i in range(earliest.id, latest.id+1):
    os.system(PROJECT_PATH + 'period.py %i' % i)
    print('--')

if not 'debug' in sys.argv:
    pass
