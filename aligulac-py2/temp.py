#!/usr/bin/python

'''
This is an empty file with some basic imports kept around for usefulness to write new scripts.
'''

import os
import sys

# Required for Django imports to work correctly.
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "aligulac.settings")

from django.db.models import Q, F
from ratings.models import Player, Match, Rating, Event, Period
