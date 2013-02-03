#!/usr/bin/python

'''
This script recomputes the Hall of Fame.
'''

# Required for Django imports to work correctly
import os
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "aligulac.settings")

from itertools import combinations

from django.db.models import F, Avg

from ratings.models import Period, Player, Rating
from ratings.tools import filter_active_ratings

limit = 10              # The benchmark position on the rating list. Above here, players will gain points.
                        # Below, players will lose points.

mean = False            # Set to True to use the mean of the top N players as a benchmark, False to just
                        # use the rating of the Nth player.

first_period = 15       # Before this it doesn't count.

# First, clear everything
Rating.objects.update(domination=None)

# Evaluate the domination scores for every player in every period
print 'Evaluating domination scores...'
for period in Period.objects.filter(computed=True, id__gte=first_period):
    bench = filter_active_ratings(Rating.objects.filter(period=period)).order_by('-rating')[limit-1].rating
    if mean:
        bench = filter_active_ratings(Rating.objects.filter(period=period, rating__gte=bench))
        bench = bench.aggregate(Avg('rating'))['rating__avg']
    filter_active_ratings(Rating.objects.filter(period=period)).update(domination=F('rating')-bench)

# Evaluate the hall of fame scores
print 'Evaluating Hall of Fame. This might take a while...'
for player in Player.objects.all():
    ratings = list(Rating.objects.filter(player=player, period__id__gte=first_period).order_by('period__id'))

    # Ignore players without ratings
    if len(ratings) == 0:
        continue

    # Collect a list of indices where the rating domination switches from positive to negative or vice versa
    # Always pick the positive side of the split
    # Also include the endpoints if those have positive domination
    inds = []
    for i in range(1, len(ratings)):
        if ratings[i].domination == None or ratings[i-1].domination == None:
            continue
        if ratings[i].domination * ratings[i-1].domination < 0:
            if ratings[i].domination > 0:
                inds.append(i)
            else:
                inds.append(i-1)
    if ratings[0].domination > 0:
        inds.append(0)
    if ratings[-1].domination > 0:
        inds.append(len(ratings)-1)

    # Make sure indices are unique and in increasing order
    inds = sorted(list(set(inds)))      

    dom = 0
    init = None
    fin = None

    # Try out all possible combination of start and end indices to find the optimal choice
    for i1, i2 in combinations(inds, 2):
        d = sum([r.domination for r in ratings[i1:i2+1] if r.domination != None])
        if d > dom:
            dom = d
            init = ratings[i1].period
            try:
                fin = ratings[i2+1].period
            except:
                # This is called if the range runs to the current period, and there is no next rating
                fin = Period.objects.get(id=ratings[-1].period.id+1)

    # If no range was found yielding positive domination, pick the least negative one
    if init == None:
        dom = -100
        for i in range(1,len(ratings)):
            if ratings[i].decay > 3:
                continue
            if ratings[i].dev > 0.2:
                continue
            if ratings[i].domination > dom:
                dom = ratings[i].domination
                init = ratings[i].period

    # This should never fire
    if init == None:
        continue

    if fin == None:
        fin = Period.objects.get(id=init.id+1)

    # Write to database
    player.dom_val = dom
    player.dom_start = init
    player.dom_end = fin
    player.save()
