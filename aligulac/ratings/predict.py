import os

os.environ['HOME'] = '/root'

from aligulac.views import base_ctx
from ratings.tools import find_player
from simul.playerlist import make_player
from simul.formats import match
from ratings.templatetags.ratings_extras import ratscale

from django.shortcuts import render_to_response, get_object_or_404, redirect
from django.http import HttpResponse
from django.db.models import Q, Sum
from models import Period, Rating, Player, Match
from django.contrib.auth import authenticate, login
from django.core.context_processors import csrf

from countries import transformations, data

from scipy.stats import norm

from math import sqrt

def predict(request):
    base = base_ctx()
    base['curpage'] = 'Predict'

    formats = ['Best-of-N match']
    base['formats'] = formats

    if 'format' not in request.GET:
        return render_to_response('predict.html', base)

    base['errs'] = []

    try:
        fmt = int(request.GET['format'])
        formats[fmt]
    except:
        base['errs'].append('Unrecognized format ID: %s' % request.GET['format'])
    base['fmt'] = fmt

    try:
        bo = [int(k.strip()) for k in request.GET['bo'].split(',') if k.strip() != '']
        assert(len(bo) != 0)
        for i in bo:
            assert(i % 2 == 1)
            assert(i > 0)
    except:
        base['errs'].append('\'Best of\' must be a comma-separated list of positive odd integers (1,3,5,...)')
    base['bo'] = request.GET['bo']

    failures, players = [], []
    for line in request.GET['players'].splitlines():
        if line.strip() == '':
            continue
        dbplayer = find_player(line.strip().split(' '), make=False)
        if dbplayer.count() > 1:
            base['errs'].append('Player \'%s\' not unique, add more information.' % line)
        elif not dbplayer.exists():
            base['errs'].append('No such player \'%s\' found.' % line)
        else:
            players.append(dbplayer[0])
    base['pls'] = request.GET['players']

    if len(base['errs']) != 0:
        return render_to_response('predict.html', base)

    if fmt == 0: 
        if len(players) != 2:
            base['errs'].append('Expected exactly two players')
        if len(bo) != 1:
            base['errs'].append('Expected exactly one \'best of\'')
    elif fmt in [1, 2] :
        if (len(players) % 2 != 0 or len(players) == 0):
            base['errs'].append('Expected an even number of players (equal for each team)')
        if len(bo) != 1:
            base['errs'].append('Expected exactly one \'best of\'')

    if len(base['errs']) != 0:
        return render_to_response('predict.html', base)

    bo = '%2C'.join([str(b) for b in bo])
    ps = '%2C'.join([str(p.id) for p in players])
    if fmt == 0:
        return redirect('/predict/match/?bo=%s&ps=%s' % (bo, ps))

    return render_to_response('predict.html', base)

def pred_match(request):
    dbpl = [get_object_or_404(Player, id=int(i)) for i in request.GET['ps'].split(',')]
    sipl = [make_player(pl) for pl in dbpl]
    num = (int(request.GET['bo'])+1)/2
    obj = match.Match(num)
    obj.set_players(sipl)

    s1, s2 = 0, 0
    if 's1' in request.GET:
        try:
            s1 = max(min(int(request.GET['s1']), num), 0)
        except:
            pass
    if 's2' in request.GET:
        try:
            s2 = max(min(int(request.GET['s2']), num), 0)
        except:
            pass

    obj.modify(s1, s2)
    obj.compute()

    base = base_ctx()
    base.update({'p1': dbpl[0], 'p2': dbpl[1], 'r1': sipl[0].elo + sipl[0].elo_race[sipl[1].race],\
                 'r2': sipl[1].elo + sipl[1].elo_race[sipl[0].race]})
    tally = obj.get_tally()
    base.update({'t1': tally[sipl[0]][1], 't2': tally[sipl[1]][1]})
    base['max'] = max(base['t1'], base['t2'])
    base['fav'] = dbpl[0] if base['t1'] > base['t2'] else dbpl[1]
    r1, r2 = [], []
    for oc in obj._outcomes:
        if oc[1] > oc[2]:
            r1.append((oc[1], oc[2], oc[0]))
        else:
            r2.append((oc[1], oc[2], oc[0]))

    while len(r1) < len(r2):
        r1 = [None] + r1
    while len(r2) < len(r1):
        r2 = [None] + r2
    base['res'] = zip(r1, r2)
    
    base['ps'] = request.GET['ps']
    base['bo'] = request.GET['bo']
    base['s1'] = s1
    base['s2'] = s2

    def fill(s, l, left=True):
        if left:
            return ' '*(l-len(s)) + s
        else:
            return s + ' '*(l-len(s))

    numlen = len(str(num))
    strL = '({rat}) {name} {score: >{nl}}'.format(rat=ratscale(sipl[0].elo + sipl[0].elo_race[sipl[1].race]),\
            name=sipl[0].name, score=s1, nl=numlen)
    strR = '{score: <{nl}} {name} ({rat})'.format(rat=ratscale(sipl[1].elo + sipl[1].elo_race[sipl[0].race]),\
            name=sipl[1].name, score=s2, nl=numlen)
    totlen = max(len(strL), len(strR), 10+numlen)

    strL = fill(strL, totlen, True)
    strR = fill(strR, totlen, False)
    postable = '[center][code]' + strL + '-' + strR
    postable += '\n' + '-'*(8+1+2*totlen)

    ilen = totlen - numlen - 1

    for i in range(0, len(r1)):
        try:
            strL = '{pctg: >6.2f}% {sca}-{scb: >{nl}}'.format(pctg=100*r1[i][2], sca=r1[i][0], scb=r1[i][1], nl=numlen)
        except:
            strL = ''
        try:
            strR = '{sca: >{nl}}-{scb} {pctg: >6.2f}%'.format(pctg=100*r2[i][2], sca=r2[i][0], scb=r2[i][1], nl=numlen)
        except:
            strR = ''
        postable += '\n' + fill(strL, ilen, True) + ' '*(3+2*numlen) + fill(strR, ilen, False)

    postable += '\n' + '-'*(8+1+2*totlen)
    
    strL = fill('{pctg: >6.2f}%'.format(pctg=100*base['t1']), ilen-3-numlen, True)
    strR = fill('{pctg: >6.2f}%'.format(pctg=100*base['t2']), ilen-3-numlen, False)

    postable += '\n' + strL + ' '*(9+4*numlen) + strR

    postable += '\n\n' + 'Median outcome'
    ls = obj.find_lsup()
    strL = '{name} {sc}'.format(name=sipl[0].name, sc=ls[1])
    strR = '{sc} {name}'.format(name=sipl[1].name, sc=ls[2])
    postable += '\n' + strL + '-' + strR

    postable += '[/code]'

    postable += '[small]Estimated by [url=http://aligulac.com/]Aligulac[/url]. '\
              + '[url=http://aligulac.com/predict/]Make another[/url].[/small][/center]'

    base['postable'] = postable
    base['curpage'] = 'Predict'
    return render_to_response('pred_match.html', base)

def pred_rrgroup(request):
    dbpl = [get_object_or_404(Player, id=int(i)) for i in request.GET['ps'].split(',')]
    sipl = [make_player(pl) for pl in dbpl]
    num = (int(request.GET['bo'])+1)/2
    obj = rrgroup.RRGroup(len(sipl), num, ['mscore', 'sscore', 'imscore', 'isscore', 'ireplay'], 1)
    obj.set_players(sipl)
    obj.compute()

    base = base_ctx()

    for i in range(0,len(sipl)):
        tally = obj.get_tally()[sipl[i]]
        dbp = dbpl[i]

    base['sipl'] = sipl
    
    return render_to_response('pred_rrgroup.html', base)

def binomial(n, k):
    if k == 0:
        return 1
    else:
        return float(n)/k * binomial(n-1, k-1)
