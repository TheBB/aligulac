#!/usr/bin/python
import sys
import os
from numpy import *
from scipy.stats import norm

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "aligulac.settings")

from django.db.models import Q, F
from ratings.models import Period, Player, Rating, Match

from rating import update

period = int(sys.argv[1])

if 'publish' in sys.argv:
    cur = Period.objects.get(id=period)
    cur.computed = True
    cur.save()

    print 'Period %i published' % cur.id
    sys.exit(0)

prev = Period.objects.filter(id__lt=period, computed=False)
if len(prev) > 0:
    print "Previous period #%i not computed. Aborting." % prev[0].id
    sys.exit(1)

post = Period.objects.filter(id__gt=period, computed=True)
if len(post) > 0 and not 'override' in sys.argv:
    print "Following period #%i already computed. Add 'override' to continue. Aborting." % post[0].id
    sys.exit(1)

prev = Period.objects.filter(id=period-1)
if len(prev) > 0:
    prev = prev[0]
else:
    prev = None

cur = Period.objects.get(id=period)
cur.computed = False
cur.save()

Rating.objects.filter(period=cur).delete()
print 'Period %i: from %s to %s' % (cur.id, cur.start, cur.end)

nrepeats = 0
nnew = 0
nmatches = 0
ngames = 0

rats = dict()
devs = dict()
oppc = dict()
oppr = dict()
opps = dict()
W = dict()
L = dict()
prev_rats = dict()

pls = Player.objects.filter(Q(match_pla__period=cur) | Q(match_plb__period=cur)).distinct()
for p in pls:
    found = False

    if prev != None:
        prev_rating = Rating.objects.filter(period=prev, player=p)
        if len(prev_rating) > 0:
            prev_rating = prev_rating[0]
            rats[prev_rating.player.id] = prev_rating.ratings()

            (k, dtemp, l, m) = update([], array(prev_rating.devs()), [], [], [], [], [], '')
            devs[prev_rating.player.id] = list(dtemp)

            found = True
            nrepeats += 1
            prev_rats[prev_rating.player.id] = prev_rating

    if not found:
        rats[p.id] = [0, 0, 0, 0]
        devs[p.id] = [0.6, 0.6, 0.6, 0.6]
        nnew += 1

    oppc[p.id] = []
    oppr[p.id] = []
    opps[p.id] = []
    W[p.id] = []
    L[p.id] = []

ms = Match.objects.filter(period=cur)
for m in ms:
    m.treated = False
    m.save()

    cata = ['P','T','Z'].index(m.rca)
    catb = ['P','T','Z'].index(m.rcb)
    
    oppc[m.pla.id].append(catb)
    oppc[m.plb.id].append(cata)

    oppr[m.pla.id].append(rats[m.plb.id][0] + rats[m.plb.id][cata+1])
    oppr[m.plb.id].append(rats[m.pla.id][0] + rats[m.pla.id][catb+1])

    opps[m.pla.id].append(sqrt(devs[m.plb.id][0]**2 + devs[m.plb.id][cata+1]**2))
    opps[m.plb.id].append(sqrt(devs[m.pla.id][0]**2 + devs[m.pla.id][catb+1]**2))

    W[m.pla.id].append(m.sca)
    L[m.pla.id].append(m.scb)
    W[m.plb.id].append(m.scb)
    L[m.plb.id].append(m.sca)

    nmatches += 1
    ngames += m.scb + m.sca

print '%i repeating and %i new players played %i games in %i matches' % (nrepeats, nnew, ngames, nmatches)

print 'Updating ratings for %i players...' % (nrepeats+nnew)

for p in pls:
    (newr, news, compr, comps) = update(array(rats[p.id]), array(devs[p.id]),\
            array(oppr[p.id]), array(opps[p.id]), array(oppc[p.id]), array(W[p.id]), array(L[p.id]),\
            p.tag, False)

    r = Rating()
    r.player = p
    r.rating = newr[0]
    r.rating_vp = newr[1]
    r.rating_vt = newr[2]
    r.rating_vz = newr[3]
    r.dev = news[0]
    r.dev_vp = news[1]
    r.dev_vt = news[2]
    r.dev_vz = news[3]
    r.comp_rat = compr[0]
    r.comp_rat_vp = compr[1]
    r.comp_rat_vt = compr[2]
    r.comp_rat_vz = compr[3]
    r.com_dev = comps[0]
    r.com_dev_vp = comps[1]
    r.com_dev_vt = comps[2]
    r.com_dev_vz = comps[3]
    r.period = cur
    r.decay = 0

    if p.id in prev_rats.keys():
        r.prev = prev_rats[p.id]

    r.save()

print 'Decaying existing ratings...'

ndecay = 0
if prev != None:
    ratings = Rating.objects.filter(period=prev)
    for rat in ratings:
        if rat.player_id not in rats.keys():
            (k, news, f, e) = update([], array(rat.devs()), [], [], [], [], [], '')

            r = Rating()
            r.player = rat.player
            r.rating = rat.rating
            r.rating_vp = rat.rating_vp
            r.rating_vt = rat.rating_vt
            r.rating_vz = rat.rating_vz
            r.dev = news[0]
            r.dev_vp = news[1]
            r.dev_vt = news[2]
            r.dev_vz = news[3]
            r.period = cur
            r.prev = rat
            r.decay = rat.decay + 1
            r.save()

            ndecay += 1

print 'Decayed %i ratings' % ndecay

print 'Bookkeeping (this may take a while)...'

Match.objects.filter(period=cur).update(treated=True)

ratings = Rating.objects.filter(period=cur, decay__lt=4)
for rat in ratings:
    rat.position = Rating.objects.filter(period=cur, decay__lt=4, rating__gt=rat.rating).count() + 1
    rat.position_vp = Rating.objects.filter(period=cur, decay__lt=4, rating__gt=rat.rating+rat.rating_vp-F('rating_vp')).\
            exclude(Q(player=rat.player)).count() + 1
    rat.position_vt = Rating.objects.filter(period=cur, decay__lt=4, rating__gt=rat.rating+rat.rating_vt-F('rating_vt')).\
            exclude(Q(player=rat.player)).count() + 1
    rat.position_vz = Rating.objects.filter(period=cur, decay__lt=4, rating__gt=rat.rating+rat.rating_vz-F('rating_vz')).\
            exclude(Q(player=rat.player)).count() + 1
    rat.save()

def mean(a):
    return sum([f.rating for f in a])/len(a)

rp = mean(Rating.objects.filter(period=cur, player__race='P', decay__lt=4).order_by('-rating')[:5])
rt = mean(Rating.objects.filter(period=cur, player__race='T', decay__lt=4).order_by('-rating')[:5])
rz = mean(Rating.objects.filter(period=cur, player__race='Z', decay__lt=4).order_by('-rating')[:5])
sp = norm.cdf(rp-rt) + norm.cdf(rp-rz)
st = norm.cdf(rt-rp) + norm.cdf(rt-rz)
sz = norm.cdf(rz-rp) + norm.cdf(rz-rt)
cur.dom_p = sp
cur.dom_t = st
cur.dom_z = sz

cur.num_retplayers = nrepeats
cur.num_newplayers = nnew
cur.num_games = ngames
cur.computed = True
cur.save()

top = Rating.objects.filter(period=cur, decay__lt=4).order_by('-rating')
n1 = top[0]
n2 = top[1]
n1.domination = n1.rating - n2.rating
n1.save()
for i in range(1,top.count()):
    r = top[i]
    r.domination = r.rating - n1.rating
    r.save()

os.system('./domination.py')

print 'Period %i computed and published' % cur.id
