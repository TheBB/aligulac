#!/usr/bin/python

'''
This updates everything.
'''

import os, sys, datetime

# Required for Django imports to work correctly.
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "aligulac.settings")

from ratings.models import Period
from aligulac.settings import PATH_TO_DIR
from django.db.models import Q

pers = Period.objects.filter(Q(needs_recompute=True) | Q(match__treated=False))\
        .filter(start__lte=datetime.date.today()).distinct().order_by('id')
if pers.exists():
    earliest = pers[0]
    latest = Period.objects.filter(start__lte=datetime.date.today()).order_by('-id')[0]

    for i in range(earliest.id, latest.id+1):
        os.system(PATH_TO_DIR + 'period.py %i' % i)

    os.system(PATH_TO_DIR + 'domination.py')

os.system(PATH_TO_DIR + 'teamranks.py ak')
os.system(PATH_TO_DIR + 'teamranks.py pl')

os.system('touch ' + PATH_TO_DIR + 'update')
