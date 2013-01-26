#!/usr/bin/python
import sys
import os
from numpy import *
from scipy.stats import norm

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "aligulac.settings")

from django.db.models import Q, F
from ratings.models import Period, Player, Rating, Match

from rating import update

RACES = ['P', 'T', 'Z']
EXRACES = ['M'] + RACES
INIT_RATING = 0.0
INIT_DEV = 0.6
MIN_DEV = 0.05
DEV_DECAY = 0.04

class CPlayer:

    def __init__(self):
        self.prev_rating = dict()
        self.prev_dev = dict()
        self.oppc = []
        self.oppr = []
        self.oppd = []
        self.W = []
        self.L = []
        self.player = None
        self.prev_rating_obj = None

    def get_rating_array(self):
        ret = []
        for r in EXRACES:
            ret.append(self.prev_rating[r])
        return array(ret)

    def get_dev_array(self):
        ret = []
        for r in EXRACES:
            ret.append(self.prev_dev[r])
        return array(ret)

def get_new_players(cplayers, period):
    """Collects information about all new players."""

    pls = Player.objects.filter(Q(match_pla__period=period) | Q(match_plb__period=period)).distinct()
    for p in pls:
        if p.id in cplayers:
            continue

        cp = CPlayer()
        cp.player = p

        for r in RACES:
            cp.prev_rating[r] = INIT_RATING
            cp.prev_dev[r] = INIT_DEV
        cp.prev_rating['M'] = INIT_RATING
        cp.prev_dev['M'] = INIT_DEV

        cplayers[p.id] = cp

def get_existing_players(cplayers, prev):
    """Collects information about all players already rated."""

    rats = Rating.objects.filter(period=prev).select_related('player')
    for rat in rats:
        cp = CPlayer()
        cp.player = rat.player
        cp.prev_rating_obj = rat

        for r in RACES:
            cp.prev_rating[r] = rat.get_rating(r)
            cp.prev_dev[r] = rat.get_dev(r)
        cp.prev_rating['M'] = rat.get_rating()
        cp.prev_dev['M'] = rat.get_dev()

        cplayers[rat.player.id] = cp

def decay_dev(cp):
    """Decays the RD of a player."""
    for r in EXRACES:
        cp.prev_dev[r] = min(sqrt(cp.prev_dev[r]**2 + DEV_DECAY**2), INIT_DEV)

def get_matches(cplayers, period):
    """Collects all results during a period."""

    def add(cp_my, cp_op, rc_my, rc_op, sc_my, sc_op, weight=1.0):
        cp_my.oppc.append(RACES.index(rc_op))
        cp_my.oppr.append(cp_op.prev_rating['M'] + cp_op.prev_rating[rc_my])
        cp_my.oppd.append(sqrt(cp_op.prev_dev['M']**2 + cp_op.prev_dev[rc_my]**2))
        cp_my.W.append(weight * sc_my)
        cp_my.L.append(weight * sc_op)

    ret = 0

    matches = Match.objects.filter(period=period).select_related('pla', 'plb')
    for m in matches:
        cpa = cplayers[m.pla.id]
        cpb = cplayers[m.plb.id]

        rcas = [m.rca] if m.rca in RACES else RACES
        rcbs = [m.rcb] if m.rcb in RACES else RACES
        weight = float(1)/len(rcas)/len(rcbs)

        for ra in rcas:
            for rb in rcbs:
                add(cpa, cpb, ra, rb, m.sca, m.scb, weight)
                add(cpb, cpa, rb, ra, m.scb, m.sca, weight)

        ret += m.sca + m.scb

    return ret

def array_to_dict(ar):
    d = dict()
    d['M'] = ar[0]
    d['P'] = ar[1]
    d['T'] = ar[2]
    d['Z'] = ar[3]
    return d

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

    try:
        prev = Period.objects.get(id=period.id-1)
    except:
        prev = None

    # Get all cplayer objects
    cplayers = dict()
    if prev:
        get_existing_players(cplayers, prev)
    get_new_players(cplayers, period)

    # Update devs to after a period has passed
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
                array(cp.oppr), array(cp.oppd), array(cp.oppc), array(cp.W), array(cp.L), cp.player.tag,\
                False)
        cp.new_rating = array_to_dict(newr)
        cp.new_dev = array_to_dict(newd)
        cp.comp_rating = array_to_dict(compr)
        cp.comp_dev = array_to_dict(compd)

        if len(cp.W) > 0 and cp.prev_rating_obj:
            num_retplayers += 1
        elif len(cp.W) > 0:
            num_newplayers += 1
    print('Updated ratings for {} players.'.format(len(cplayers)))

    # Save new ratings
    print('Saving ratings. This can take some time...')
    for cp in cplayers.values():
        try:
            rating = Rating.objects.get(player=cp.player, period=period)
        except:
            rating = Rating()
            rating.player = cp.player
            rating.period = period

        if cp.prev_rating_obj:
            rating.prev = cp.prev_rating_obj

        if not cp.prev_rating_obj or len(cp.W) > 0:
            rating.decay = 0
        else:
            rating.decay = cp.prev_rating_obj.decay + 1

        rating.set_rating(cp.new_rating)
        rating.set_dev(cp.new_dev)
        rating.set_comp_rating(cp.comp_rating)
        rating.set_comp_dev(cp.comp_dev)

        rating.save()

    print('Bookkeeping. This can take some time...')

    Match.objects.filter(period=period).update(treated=True)

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

    period.num_retplayers = 0
    period.num_newplayers = 0
    period.num_games = 0
    period.computed = True
    period.save()

    top = Rating.objects.filter(period=period, decay__lt=4).order_by('-rating')
    n1 = top[0]
    n2 = top[1]
    top.update(domination=F('rating')-n1.rating)
    n1.domination = n1.rating - n2.rating
    n1.save()

    os.system('./domination.py')
