#!/usr/bin/python

'''
This script will recompute the ratings for a given period.

./period.py <period_id>

The script will yield an error message if there are untreated matches from previous periods, or if previous
periods are marked as not computed.
'''

import sys, os
from numpy import *
from scipy.stats import norm

# This is required for Django imports to work correctly
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "aligulac.settings")

from django.db.models import Q, F
from ratings.models import Period, Player, Rating, Match

from rating import update

# Parameters for rating computation
RACES = 'PTZ'
EXRACES = 'M' + RACES       # 'M' is 'MEAN'
INIT_RATING = 0.0
INIT_DEV = 0.6
MIN_DEV = 0.05
DEV_DECAY = 0.04

# This is a meta class holding information about rating computation
class CPlayer:

    def __init__(self):
        self.prev_rating = dict()       # A dict mapping EXRACES to ratings
        self.prev_dev = dict()          # A dict mapping EXRACES to RDs
        self.oppc = []                  # Opponent categories
        self.oppr = []                  # Opponent ratings
        self.oppd = []                  # Opponent RDs
        self.W = []                     # Number of wins
        self.L = []                     # Number of losses
        self.player = None              # Django Player object
        self.prev_rating_obj = None     # Django previous Rating object

    # Returns previous ratings in an array
    def get_rating_array(self):
        ret = []
        for r in EXRACES:
            ret.append(self.prev_rating[r])
        return array(ret)

    # Returns previous RDs in an array
    def get_dev_array(self):
        ret = []
        for r in EXRACES:
            ret.append(self.prev_dev[r])
        return array(ret)

def get_new_players(cplayers, period):
    """Collects information about all new players, and adds them to the cplayers dict if not already there."""

    players = Player.objects.filter(Q(match_pla__period=period) | Q(match_plb__period=period)).distinct()
    for player in players:
        # Skip if player is already added
        if player.id in cplayers:
            continue

        cp = CPlayer()
        cp.player = player

        # Fill in the previous rating information
        for r in EXRACES:
            cp.prev_rating[r] = INIT_RATING
            cp.prev_dev[r] = INIT_DEV

        # Add to the dict
        cplayers[player.id] = cp

def get_existing_players(cplayers, prev):
    """Collects information about all players already rated, and adds them to the cplayers dict."""

    ratings = Rating.objects.filter(period=prev).select_related('player')
    for rating in ratings:
        cp = CPlayer()
        cp.player = rating.player
        cp.prev_rating_obj = rating

        # Fill in the previous rating information
        for r in RACES:
            cp.prev_rating[r] = rating.get_rating(r)
            cp.prev_dev[r] = rating.get_dev(r)
        cp.prev_rating['M'] = rating.get_rating()
        cp.prev_dev['M'] = rating.get_dev()

        # Add to the dict
        cplayers[rat.player.id] = cp

def decay_dev(cp):
    """Decays the RD of a player."""
    for r in EXRACES:
        cp.prev_dev[r] = min(sqrt(cp.prev_dev[r]**2 + DEV_DECAY**2), INIT_DEV)

def get_matches(cplayers, period):
    """
    Collects all results during a period and adds them to the cplayer objects.
    Returns the number of games played.
    """

    # Useful meta function to add a match to a cplayer object
    def add(cp_my, cp_op, rc_my, rc_op, sc_my, sc_op, weight=1.0):
        cp_my.oppc.append(RACES.index(rc_op))
        cp_my.oppr.append(cp_op.prev_rating['M'] + cp_op.prev_rating[rc_my])
        cp_my.oppd.append(sqrt(cp_op.prev_dev['M']**2 + cp_op.prev_dev[rc_my]**2))
        cp_my.W.append(weight * sc_my)
        cp_my.L.append(weight * sc_op)

    # Counter for number of games
    ngames = 0

    # Loop over all matches
    matches = Match.objects.filter(period=period).select_related('pla', 'plb')
    for m in matches:
        # Get cplayer objects
        cpa = cplayers[m.pla.id]
        cpb = cplayers[m.plb.id]

        # Set the played races for each player. For the vast majority of matches this should be a single item
        # list per player. When a player plays as random, or an unrecognized race, it will be treated as even
        # weight over all the three races
        rcas = [m.rca] if m.rca in RACES else RACES
        rcbs = [m.rcb] if m.rcb in RACES else RACES
        weight = float(1)/len(rcas)/len(rcbs)

        # For each race combination, add information to the cplayer objects
        for ra in rcas:
            for rb in rcbs:
                add(cpa, cpb, ra, rb, m.sca, m.scb, weight)
                add(cpb, cpa, rb, ra, m.scb, m.sca, weight)

        # Count games
        ngames += m.sca + m.scb

    return ngames

def array_to_dict(ar):
    """Transforms a rating/RD dict to an array."""
    d = dict()
    d['M'] = ar[0]
    d['P'] = ar[1]
    d['T'] = ar[2]
    d['Z'] = ar[3]
    return d

# Main code for this script
if __name__ == '__main__':
    # Get period
    try:
        period = Period.objects.get(id=int(sys.argv[1]))
    except:
        print('No such period.')
        sys.exit(1)

    print('Period {}: from {} to {}'.format(period.id, period.start, period.end))

    # Check that all previous periods are computed
    prev = Period.objects.filter(id__lt=period.id, computed=False)
    if prev.exists():
        print('Previous period #%i not computed. Aborting.' % prev[0].id)
        sys.exit(1)

    # Check that all previous matches are treated
    matches = Match.objects.filter(period__id__lt=period.id, treated=False).order_by('period__id')
    if matches.exists():
        print('There are untreated matches from period #%i. Aborting.' % matches[0].period.id)
        sys.exit(1)

    # Find the previous period if it exists
    try:
        prev = Period.objects.get(id=period.id-1)
    except:
        prev = None

    # Get all cplayer objects
    cplayers = dict()
    if prev:
        get_existing_players(cplayers, prev)
    get_new_players(cplayers, period)

    # Update RDs since a period has passed
    for cp in cplayers.values():
        decay_dev(cp)
    print('Initialized and decayed ratings for {} players.'.format(len(cplayers)))

    # Collect match information
    num_games = get_matches(cplayers, period)
    print('Gathered results from {} games.'.format(num_games))

    # Update ratings
    num_retplayers = 0
    num_newplayers = 0
    for cp in cplayers.values():
        (newr, newd, compr, compd) = update(cp.get_rating_array(), cp.get_dev_array(),\
                array(cp.oppr), array(cp.oppd), array(cp.oppc), array(cp.W), array(cp.L),\
                cp.player.tag, False)
        cp.new_rating = array_to_dict(newr)
        cp.new_dev = array_to_dict(newd)
        cp.comp_rating = array_to_dict(compr)
        cp.comp_dev = array_to_dict(compd)

        # Count player as returning or new
        if len(cp.W) > 0 and cp.prev_rating_obj:
            num_retplayers += 1
        elif len(cp.W) > 0:
            num_newplayers += 1
    print('Updated ratings for {} players.'.format(len(cplayers)))

    # Write ratings to database
    print('Saving ratings. This can take some time...')
    for cp in cplayers.values():
        # Grab the current rating object if it exists, or make a new one
        try:
            rating = Rating.objects.get(player=cp.player, period=period)
        except:
            rating = Rating()
            rating.player = cp.player
            rating.period = period

        # Link to previous rating
        if cp.prev_rating_obj:
            rating.prev = cp.prev_rating_obj

        # Set the decay of the rating (number of periods since last game was played)
        if not cp.prev_rating_obj or len(cp.W) > 0:
            rating.decay = 0
        else:
            rating.decay = cp.prev_rating_obj.decay + 1

        # Set the actual ratings
        rating.set_rating(cp.new_rating)
        rating.set_dev(cp.new_dev)
        rating.set_comp_rating(cp.comp_rating)
        rating.set_comp_dev(cp.comp_dev)

        # Write
        rating.save()

    print('Bookkeeping. This can take some time...')

    # Set all matches to treated
    Match.objects.filter(period=period).update(treated=True)

    # Compute OP/UP race
    def mean(a):
        return sum([f.rating for f in a])/len(a)
    rp = mean(Rating.objects.filter(period=period, player__race='P', decay__lt=4).order_by('-rating')[:5])
    rt = mean(Rating.objects.filter(period=period, player__race='T', decay__lt=4).order_by('-rating')[:5])
    rz = mean(Rating.objects.filter(period=period, player__race='Z', decay__lt=4).order_by('-rating')[:5])
    sp = norm.cdf(rp-rt) + norm.cdf(rp-rz)
    st = norm.cdf(rt-rp) + norm.cdf(rt-rz)
    sz = norm.cdf(rz-rp) + norm.cdf(rz-rt)
    period.dom_p = sp
    period.dom_t = st
    period.dom_z = sz

    # Write some period statistics
    period.num_retplayers = num_retplayers
    period.num_newplayers = num_newplayers
    period.num_games = num_games
    period.computed = True
    period.save()

    # Recompute the hall of fame
    os.system('./domination.py')
