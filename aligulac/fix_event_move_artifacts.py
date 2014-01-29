#!/usr/bin/env python3
"""
This should really only be needed to run once as these artifacts won't appear
anymore.
"""


import os

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'aligulac.settings')

from datetime import date, datetime
import sys
import subprocess

from django.core.cache import cache
from django.db import connection
from django.db.models import F, Q
from django.db.transaction import commit_on_success

from aligulac.settings import PROJECT_PATH

from ratings.models import Event

bad_events = Event.objects.raw('''
    SELECT event.id 
    FROM event, eventadjacency 
    WHERE 
        event.parent_id != eventadjacency.parent_id AND 
        event.id = eventadjacency.child_id AND 
        distance = 1 
    ORDER BY fullname;''')

bad_events = list(bad_events)

print("{} bad event(s) found".format(len(bad_events)))

if len(bad_events) == 0:
    print("Exiting...")
    exit(0)

print("Updating... ", end="")

cur = connection.cursor()

cur.execute('''
    UPDATE event 
    SET parent_id = eventadjacency.parent_id 
    FROM eventadjacency 
    WHERE 
        event.parent_id != eventadjacency.parent_id AND 
        eventadjacency.child_id = event.id AND 
        distance = 1;''')

print("Done!")

print("Updating names... ", end="")

@commit_on_success
def update_names():
    for e in bad_events:
        e.update_name()
update_names()

print("Done!")
