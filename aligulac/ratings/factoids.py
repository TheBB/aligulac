import os

os.environ['HOME'] = '/root'

from aligulac.views import base_ctx, Message
from ratings.tools import find_player, cdf, display_matches
from simul.playerlist import make_player
from simul.formats import match

from django.shortcuts import render_to_response, get_object_or_404, redirect
from django.http import HttpResponse
from django.db.models import Q, Sum
from models import Period, Rating, Player, Match
from django.contrib.auth import authenticate, login

from countries import transformations, data

from math import sqrt, log
from collections import namedtuple

def factoids(request):
    base = base_ctx('Predict', 'Factoids', request=request)

    if 'pla' not in request.GET and 'plb' not in request.GET:
        return render_to_response('factoids.html', base)
    
    pla = find_player(request.GET['pla'].strip().split(' '), make=False)
    plb = find_player(request.GET['plb'].strip().split(' '), make=False)
    base['plas'] = request.GET['pla']
    base['plbs'] = request.GET['plb']

    base['errs'] = []
    for p, ps in [(pla, request.GET['pla']), (plb, request.GET['plb'])]:
        if p.count() > 1:
            base['messages'].append(Message('Player not unique, add more information.', ps, Message.ERROR))
        elif not p.exists():
            base['messages'].append(Message('No such player found.', ps, Message.ERROR))

    if len(base['messages']) > 0:
        return render_to_response('factoids.html', base)

    pla, plb = pla[0], plb[0]
    base['pla'] = pla
    base['plb'] = plb

    # P-VALUES: WHO IS BETTER RIGHT NOW?

    rata = pla.rating_set.order_by('-period__id')[0]
    ratb = plb.rating_set.order_by('-period__id')[0]

    base['highest'] = pla if rata.rating > ratb.rating else plb
    base['diff'] = abs(rata.rating - ratb.rating)

    base['phighest'], base['plowest'] = (pla, plb)\
                if rata.get_totalrating(plb.race if plb.race in 'PTZ' else None)\
                 > ratb.get_totalrating(pla.race if pla.race in 'PTZ' else None)\
                else (plb, pla)

    base['pdiff'] = abs(rata.get_totalrating(plb.race if plb.race in 'PTZ' else None)\
                      - ratb.get_totalrating(pla.race if pla.race in 'PTZ' else None))

    def analyze(rata, ratb, rca, rcb):
        diff = rata.get_totalrating(rcb) - ratb.get_totalrating(rca)
        dev = sqrt(rata.get_totaldev(rcb)**2 + ratb.get_totaldev(rca)**2)
        return cdf(-diff, scale=dev)

    sigs = [analyze(rata, ratb, rca, rcb) for (rca,rcb) in 
            [(None,None),('P','P'),('T','T'),('Z','Z'),(pla.race if pla.race in 'PTZ' else None,
                                                        plb.race if plb.race in 'PTZ' else None)]]
    sigs_a = [s <= 0.05 for s in sigs]
    sigs_b = [s >= 0.95 for s in sigs]
    if not False in sigs_a:
        base['sig_full_a'] = True
    elif not False in sigs_b:
        base['sig_full_b'] = True
    elif not False in sigs_a[:-1]:
        base['sig_mu_a'] = True
    elif not False in sigs_b[:-1]:
        base['sig_mu_a'] = True
    elif sigs_a[0]:
        base['sig_overall_a'] = True
    elif sigs_b[0]:
        base['sig_overall_b'] = True

    base['sig_face'] = (sigs_a[-1] if base['phighest'] == pla else sigs_b[-1])

    # MATCH PREDICTIONS

    sipl = [make_player(pl) for pl in [pla, plb]]
    num = 1
    while num <= 300:
        obj = match.Match(num)
        obj.set_players(sipl)
        obj.compute()
        if num == 1:
            base['p_1'] = max(obj.get_tally()[sipl[0]][1], obj.get_tally()[sipl[1]][1])
        elif num == 3:
            base['p_5'] = max(obj.get_tally()[sipl[0]][1], obj.get_tally()[sipl[1]][1])
        if max(obj.get_tally()[sipl[0]][1], obj.get_tally()[sipl[1]][1]) >= 0.8:
            base['num_8'] = 2*num - 1
            break
        num += 1
    if not 'num_8' in base:
        base['p_601'] = max(obj.get_tally()[sipl[0]][1], obj.get_tally()[sipl[1]][1])

    # PAST RESULTS

    ntz = lambda x: x if x is not None else 0

    matches = Match.objects.filter(Q(pla=pla, plb=plb) | Q(pla=plb, plb=pla))
    matches = matches.order_by('-date', '-id')
    base['matches'] = display_matches(matches, date=True, fix_left=pla)
    try:
        base['lastmatch'] = base['matches'][0]
    except:
        pass
    base['matchcount'] = len(base['matches'])
    base['gamecount'] = sum([m.pla_score + m.plb_score for m in base['matches']])

    plamcount = sum([1 if m.pla_score > m.plb_score else 0 for m in base['matches']])
    plbmcount = sum([1 if m.plb_score > m.pla_score else 0 for m in base['matches']])
    plagcount = sum([m.pla_score for m in base['matches']])
    plbgcount = base['gamecount'] - plagcount

    if plamcount > plbmcount:
        base['hmhighest'] = pla
    elif plbmcount > plamcount:
        base['hmhighest'] = plb
    base['smhighest'], base['smlowest'] = max(plamcount, plbmcount), min(plamcount, plbmcount)

    if plagcount > plbgcount:
        base['hghighest'] = pla
    elif plbgcount > plagcount:
        base['hghighest'] = plb
    base['sghighest'], base['sglowest'] = max(plagcount, plbgcount), min(plagcount, plbgcount)

    return render_to_response('factoids.html', base)
