# -*- coding: utf-8 -*-
import os


os.environ['HOME'] = '/root'

from aligulac.cache import cache_page
from aligulac.views import base_ctx, Message, NotUniquePlayerMessage
from ratings.tools import find_player, cdf
from simul.playerlist import make_player
from simul.formats import match, mslgroup, sebracket, rrgroup, teampl
from ratings.templatetags.ratings_extras import ratscale

from django.shortcuts import render_to_response, get_object_or_404, redirect
from django.http import HttpResponse
from django.db.models import Q, Sum
from models import Period, Rating, Player, Match
from django.contrib.auth import authenticate, login
from django.core.context_processors import csrf

from countries import transformations, data

from math import sqrt, log
from collections import namedtuple

TL_HEADER = '[center][code]'
TL_FOOTER = '[/code][/center]\n'\
            '[small]Estimated by [url=http://aligulac.com/]Aligulac[/url]. '\
            '[url=%s]Modify[/url].[/small]'

TL_SEBRACKET_HEADER = '[center][code]'
TL_SEBRACKET_MIDDLE = '[/code][/center][b]Median Outcome Bracket[/b]\n'\
                      '[spoiler][code]'
TL_SEBRACKET_FOOTER = '[/code][/spoiler]\n'\
                      '[small]Estimated by [url=http://aligulac.com/]Aligulac[/url]. '\
                      '[url=%s]Modify[/url].[/small]'

REDDIT_HEADER = ''
REDDIT_FOOTER = '\n\n^Estimated ^by [^Aligulac](http://aligulac.com/)^. [^Modify](%s)^.'

@cache_page
def predict(request):
    base = base_ctx('Predict', 'Predict', request)

    formats = ['Best-of-N match', 'Four-player Swiss group', 'Single elimination bracket',\
               'Round robin group', 'Proleague team match']
    base['formats'] = formats

    if 'format' not in request.GET:
        return render_to_response('predict.html', base)

    try:
        fmt = int(request.GET['format'])
        formats[fmt]
    except:
        base['messages'].append(Message('Unrecognized format ID: %s.' % request.GET['format'],
                                type=Message.ERROR))
    base['fmt'] = fmt

    try:
        bo = [int(k.strip()) for k in request.GET['bo'].split(',') if k.strip() != '']
        assert(len(bo) != 0)
        for i in bo:
            assert(i % 2 == 1)
            assert(i > 0)
    except:
        base['messages'].append(Message(
            '\'Best of\' must be a comma-separated list of positive odd integers (1,3,5,...).',
            type=Message.ERROR))
    base['bo'] = request.GET['bo']

    failures, players, lineno = [], [], -1
    for line in request.GET['players'].splitlines():
        lineno += 1
        if line.strip() == '':
            continue
        elif line.strip() == '-' or line.strip().upper() == 'BYE':
            players.append(None)
            continue

        dbplayer = find_player(line.strip().split(' '), make=False)
        if dbplayer.count() > 1:
            base['messages'].append(NotUniquePlayerMessage(line, dbplayer, update='players',
                                                           updateline=lineno))
        elif not dbplayer.exists():
            base['messages'].append(Message('No such player found.', line, Message.ERROR))
        else:
            players.append(dbplayer[0])
    base['pls'] = request.GET['players']

    if len(base['messages']) != 0:
        return render_to_response('predict.html', base)

    if fmt == 0: 
        if len(players) != 2:
            base['messages'].append(Message('Expected exactly two players.', type=Message.ERROR))
        if len(bo) != 1:
            base['messages'].append(Message('Expected exactly one \'best of\'.', type=Message.ERROR))
    elif fmt == 1:
        if len(players) != 4:
            base['messages'].append(Message('Expected exactly four players.', type=Message.ERROR))
        if len(bo) != 1:
            base['messages'].append(Message('Expected exactly one \'best of\'.', type=Message.ERROR))
    elif fmt == 2:
        if len(players) not in [2,4,8,16,32,64,128,256,512,1024]:
            base['messages'].append(Message('Expected number of players to be a power of two'\
                                          + ' (2,4,8,...), got %i' % len(players), type=Message.ERROR))
        else:
            nrounds = int(log(len(players),2))
            if len(bo) != nrounds and len(bo) != 1:
                base['messages'].append(Message('Expected exactly one or %i \'best of\'.' % nrounds,
                                                type=Message.ERROR))
    elif fmt == 3:
        if len(players) < 3:
            base['messages'].append(Message('Expected at least three players.', type=Message.ERROR))
        if len(bo) != 1:
            base['messages'].append(Message('Expected exactly one \'best of\'.', type=Message.ERROR))
    elif fmt == 4:
        if len(players) % 2 != 0:
            base['messages'].append(Message('Expected an even number of players.', type=Message.ERROR))
        if len(bo) != 1:
            base['messages'].append(Message('Expected exactly one \'best of\'.', type=Message.ERROR))

    if len(base['messages']) != 0:
        return render_to_response('predict.html', base)

    bo = '%2C'.join([str(b) for b in bo])
    ps = '%2C'.join([(str(p.id) if p is not None else '0') for p in players])
    if fmt == 0:
        return redirect('/predict/match/?bo=%s&ps=%s' % (bo, ps))
    elif fmt == 1:
        return redirect('/predict/4pswiss/?bo=%s&ps=%s' % (bo, ps))
    elif fmt == 2:
        return redirect('/predict/sebracket/?bo=%s&ps=%s' % (bo, ps))
    elif fmt == 3:
        return redirect('/predict/rrgroup/?bo=%s&ps=%s' % (bo, ps))
    elif fmt == 4:
        return redirect('/predict/proleague/?bo=%s&ps=%s' % (bo, ps))

    return render_to_response('predict.html', base)

@cache_page
def pred_match(request):
    base = base_ctx('Predict', 'Predict', request=request)
    base['short_url_button'] = True


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

    base.update({'p1': dbpl[0], 'p2': dbpl[1], 
                 'r1': sipl[0].elo_vs_opponent(sipl[1]),
                 'r2': sipl[1].elo_vs_opponent(sipl[0])})
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

    # Winrates
    base['w1'] = {}
    base['w2'] = {}


    def ntz(n):
        return n if n is not None else 0

    matches_a = Match.objects.filter(pla=dbpl[0])
    matches_b = Match.objects.filter(plb=dbpl[0])

    a = matches_a.aggregate(Sum('sca'), Sum('scb'))
    b = matches_b.aggregate(Sum('sca'), Sum('scb'))
    base['w1']['total'] = (ntz(a['sca__sum']) + ntz(b['scb__sum']), ntz(a['scb__sum']) + ntz(b['sca__sum']))

    a = matches_a.filter(rcb='P').aggregate(Sum('sca'), Sum('scb'))
    b = matches_b.filter(rca='P').aggregate(Sum('sca'), Sum('scb'))
    base['w1']['vp'] = (ntz(a['sca__sum']) + ntz(b['scb__sum']), ntz(a['scb__sum']) + ntz(b['sca__sum']))

    a = matches_a.filter(rcb='T').aggregate(Sum('sca'), Sum('scb'))
    b = matches_b.filter(rca='T').aggregate(Sum('sca'), Sum('scb'))
    base['w1']['vt'] = (ntz(a['sca__sum']) + ntz(b['scb__sum']), ntz(a['scb__sum']) + ntz(b['sca__sum']))

    a = matches_a.filter(rcb='Z').aggregate(Sum('sca'), Sum('scb'))
    b = matches_b.filter(rca='Z').aggregate(Sum('sca'), Sum('scb'))
    base['w1']['vz'] = (ntz(a['sca__sum']) + ntz(b['scb__sum']), ntz(a['scb__sum']) + ntz(b['sca__sum']))

    base['w1']['max'] = int(round(100 * max(
        (float(base['w1']['vp'][0]) / float(sum(base['w1']['vp'])) if (sum(base['w1']['vp']) > 0) else 0),
        (float(base['w1']['vt'][0]) / float(sum(base['w1']['vt'])) if (sum(base['w1']['vt']) > 0) else 0),
        (float(base['w1']['vz'][0]) / float(sum(base['w1']['vz'])) if (sum(base['w1']['vz']) > 0) else 0)
    )))

    base['w1']['min'] = int(round(100 * min(
        (float(base['w1']['vp'][0]) / float(sum(base['w1']['vp'])) if (sum(base['w1']['vp']) > 0) else 0),
        (float(base['w1']['vt'][0]) / float(sum(base['w1']['vt'])) if (sum(base['w1']['vt']) > 0) else 0),
        (float(base['w1']['vz'][0]) / float(sum(base['w1']['vz'])) if (sum(base['w1']['vz']) > 0) else 0)
    )))

    a = matches_a.filter(plb=dbpl[1]).aggregate(Sum('sca'), Sum('scb'))
    b = matches_b.filter(pla=dbpl[1]).aggregate(Sum('sca'), Sum('scb'))
    base['w1']['vo'] = (ntz(a['sca__sum']) + ntz(b['scb__sum']), ntz(a['scb__sum']) + ntz(b['sca__sum']))

    matches_a = Match.objects.filter(pla=dbpl[1])
    matches_b = Match.objects.filter(plb=dbpl[1])

    a = matches_a.aggregate(Sum('sca'), Sum('scb'))
    b = matches_b.aggregate(Sum('sca'), Sum('scb'))
    base['w2']['total'] = (ntz(a['sca__sum']) + ntz(b['scb__sum']), ntz(a['scb__sum']) + ntz(b['sca__sum']))

    a = matches_a.filter(rcb='P').aggregate(Sum('sca'), Sum('scb'))
    b = matches_b.filter(rca='P').aggregate(Sum('sca'), Sum('scb'))
    base['w2']['vp'] = (ntz(a['sca__sum']) + ntz(b['scb__sum']), ntz(a['scb__sum']) + ntz(b['sca__sum']))

    a = matches_a.filter(rcb='T').aggregate(Sum('sca'), Sum('scb'))
    b = matches_b.filter(rca='T').aggregate(Sum('sca'), Sum('scb'))
    base['w2']['vt'] = (ntz(a['sca__sum']) + ntz(b['scb__sum']), ntz(a['scb__sum']) + ntz(b['sca__sum']))

    a = matches_a.filter(rcb='Z').aggregate(Sum('sca'), Sum('scb'))
    b = matches_b.filter(rca='Z').aggregate(Sum('sca'), Sum('scb'))
    base['w2']['vz'] = (ntz(a['sca__sum']) + ntz(b['scb__sum']), ntz(a['scb__sum']) + ntz(b['sca__sum']))

    a = matches_a.filter(plb=dbpl[0]).aggregate(Sum('sca'), Sum('scb'))
    b = matches_b.filter(pla=dbpl[0]).aggregate(Sum('sca'), Sum('scb'))
    base['w2']['vo'] = (ntz(a['sca__sum']) + ntz(b['scb__sum']), ntz(a['scb__sum']) + ntz(b['sca__sum']))

    base['w2']['max'] = int(round(100 * max(
        (float(base['w2']['vp'][0]) / float(sum(base['w2']['vp'])) if (sum(base['w2']['vp']) > 0) else 0),
        (float(base['w2']['vt'][0]) / float(sum(base['w2']['vt'])) if (sum(base['w2']['vt']) > 0) else 0),
        (float(base['w2']['vz'][0]) / float(sum(base['w2']['vz'])) if (sum(base['w2']['vz']) > 0) else 0)
    )))

    base['w2']['min'] = int(round(100 * min(
        (float(base['w2']['vp'][0]) / float(sum(base['w2']['vp'])) if (sum(base['w2']['vp']) > 0) else 0),
        (float(base['w2']['vt'][0]) / float(sum(base['w2']['vt'])) if (sum(base['w2']['vt']) > 0) else 0),
        (float(base['w2']['vz'][0]) / float(sum(base['w2']['vz'])) if (sum(base['w2']['vz']) > 0) else 0)
    )))

    
    base['ps'] = request.GET['ps']
    base['bo'] = request.GET['bo']
    base['s1'] = s1
    base['s2'] = s2

    match_postable(base, obj, r1, r2,
                   url='http://aligulac.com/predict/match/?bo=%s&ps=%s' % (base['bo'], base['ps']))
    return render_to_response('pred_match.html', base)

@cache_page
def pred_4pswiss(request):
    base = base_ctx('Predict', 'Predict', request=request)

    dbpl = [get_object_or_404(Player, id=int(i)) for i in request.GET['ps'].split(',')]
    sipl = [make_player(pl) for pl in dbpl]
    num = (int(request.GET['bo'])+1)/2
    obj = mslgroup.MSLGroup(num)
    obj.set_players(sipl)

    def update(request, obj, match, r1, r2):
        if r1 in request.GET and r2 in request.GET:
            try:
                if obj.get_match(match).can_modify():
                    obj.get_match(match).modify(int(request.GET[r1]), int(request.GET[r2]))
            except:
                pass

    update(request, obj, 'first',   '11', '12')
    update(request, obj, 'second',  '21', '22')
    update(request, obj, 'winners', '31', '32')
    update(request, obj, 'losers',  '41', '42')
    update(request, obj, 'final',   '51', '52')

    obj.compute()
    tally = obj.get_tally()

    players = list(sipl)
    for p in players:
        p.tally = tally[p]

    for i in range(0, 4):
        players.sort(key=lambda p: p.tally[i], reverse=True)

    base['players'] = players

    MatchObj = namedtuple('MatchObj', 'obj pla plb modded canmod fixed sca scb')
    matches = []
    for mname in ['first', 'second', 'winners', 'losers', 'final']:
        match = obj.get_match(mname)
        matches.append(MatchObj(match, match.get_player(0).dbpl, match.get_player(1).dbpl,\
                match.is_modified(), match.can_modify(), match.is_fixed(), match._result[0], match._result[1]))
    base['matches'] = matches

    MeanRes = namedtuple('MeanRes', 'pla plb sca scb')
    meanres = []
    for mname in ['first', 'second', 'winners', 'losers', 'final']:
        match = obj.get_match(mname)
        match.compute()
        lsup = match.find_lsup()
        meanres.append(MeanRes(match.get_player(0).dbpl, match.get_player(1).dbpl, lsup[1], lsup[2]))
        match.broadcast_instance((0, [lsup[4], lsup[3]], match))
    base['meanres'] = meanres

    base['ps'] = request.GET['ps']
    base['bo'] = request.GET['bo']

    fpswiss_postable(base, obj, players,
                     url='http://aligulac.com/predict/4pswiss/?bo=%s&ps=%s' % (base['bo'], base['ps']))
    return render_to_response('pred_4pswiss.html', base)

@cache_page
def pred_sebracket(request):
    base = base_ctx('Predict', 'Predict', request=request)

    dbpl = []
    for i in request.GET['ps'].split(','):
        id = int(i)
        if id > 0:
            dbpl.append(get_object_or_404(Player, id=id))
        else:
            dbpl.append(None)
    sipl = [make_player(pl) for pl in dbpl]
    nrounds = int(log(len(sipl),2))
    num = [(int(bo)+1)/2 for bo in request.GET['bo'].split(',')]
    if len(num) == 1:
        num = num * nrounds
    obj = sebracket.SEBracket(num)
    obj.set_players(sipl)

    def update(request, obj, match, r1, r2):
        if r1 in request.GET and r2 in request.GET:
            try:
                if obj.get_match(match).can_modify():
                    obj.get_match(match).modify(int(request.GET[r1]), int(request.GET[r2]))
            except:
                pass

    for rnd in range(1, nrounds+1):
        for j in range(1, 2**(nrounds-rnd)+1):
            s = '%i-%i' % (rnd, j)
            update(request, obj, s, 'm' + s + '-1', 'm' + s + '-2')

    obj.compute()
    tally = obj.get_tally()

    players = list(sipl)
    for p in players:
        p.tally = tally[p][::-1]

    for i in range(len(players[0].tally)-1, -1, -1):
        players.sort(key=lambda p: p.tally[i], reverse=True)

    base['players'] = [p for p in players if p.dbpl is not None]
    base['nrounds'] = nrounds

    MatchObj = namedtuple('MatchObj', 'obj pla plb modded canmod fixed sca scb id')
    matches = []
    for rnd in range(1, nrounds+1):
        matches.append('Round %i' % rnd)
        for j in range(1, 2**(nrounds-rnd)+1):
            match = obj.get_match('%i-%i' % (rnd, j))
            if match.get_player(0).dbpl is not None and match.get_player(1).dbpl is not None:
                matches.append(MatchObj(match, match.get_player(0).dbpl, match.get_player(1).dbpl,
                               match.is_modified(), match.can_modify(), match.is_fixed(),
                               match._result[0], match._result[1], '%i-%i' % (rnd, j)))
    base['matches'] = matches

    MeanRes = namedtuple('MeanRes', 'pla plb sca scb')
    meanres = []
    bracket = []
    for rnd in range(1, nrounds+1):
        meanres.append('Round %i' % rnd)
        bracket.append([])
        for j in range(1, 2**(nrounds-rnd)+1):
            match = obj.get_match('%i-%i' % (rnd, j))
            match.compute()
            lsup = match.find_lsup()
            meanres.append(MeanRes(match.get_player(0).dbpl, match.get_player(1).dbpl, lsup[1], lsup[2]))
            bracket[-1].append(meanres[-1])
            match.broadcast_instance((0, [lsup[4], lsup[3]], match))
    base['meanres'] = meanres

    base['ps'] = request.GET['ps']
    base['bo'] = request.GET['bo']

    sebracket_postable(base, obj, players, bracket,
                       url='http://aligulac.com/predict/sebracket/?bo=%s&ps=%s' % (base['bo'], base['ps']))
    return render_to_response('pred_sebracket.html', base)

@cache_page
def pred_rrgroup(request):
    base = base_ctx('Predict', 'Predict', request=request)

    dbpl = [get_object_or_404(Player, id=int(i)) for i in request.GET['ps'].split(',')]
    sipl = [make_player(pl) for pl in dbpl]
    num = (int(request.GET['bo'])+1)/2
    nplayers = len(sipl)
    obj = rrgroup.RRGroup(len(sipl), num, ['mscore', 'sscore', 'imscore', 'isscore', 'ireplay'], 1)
    obj.set_players(sipl)
    obj.compute()

    MeanRes = namedtuple('MeanRes', 'pla plb sca scb')
    meanres = []
    for i in range(0, (nplayers-1)*nplayers/2):
        match = obj.get_match(i)
        match.compute()
        lsup = match.find_lsup()
        meanres.append(MeanRes(match.get_player(0).dbpl, match.get_player(1).dbpl, lsup[1], lsup[2]))
        match.modify(lsup[1], lsup[2])
    base['meanres'] = meanres
    obj.compute()

    mtally = obj.get_tally()
    for p in sipl:
        p.mtally = mtally[p]

    base['mplayers'] = obj.table

    def update(request, obj, match, r1, r2):
        if r1 in request.GET and r2 in request.GET:
            try:
                if obj.get_match(match).can_modify():
                    obj.get_match(match).modify(int(request.GET[r1]), int(request.GET[r2]))
            except:
                pass
        else:
            obj.get_match(match).modify(0, 0)

    for i in range(0, (nplayers-1)*nplayers/2):
        update(request, obj, i, 'm%i-1' % i, 'm%i-2' % i)

    obj.compute()
    tally = obj.get_tally()

    players = list(sipl)
    for p in players:
        p.tally = tally[p][::-1]

    for i in range(len(players[0].tally)-1, -1, -1):
        players.sort(key=lambda p: p.tally[i], reverse=True)

    base['players'] = players

    MatchObj = namedtuple('MatchObj', 'obj pla plb modded canmod fixed sca scb')
    matches = []
    for i in range(0, (nplayers-1)*nplayers/2):
        match = obj.get_match(i)
        matches.append(MatchObj(match, match.get_player(0).dbpl, match.get_player(1).dbpl,\
                    match.is_modified(), match.can_modify(), match.is_fixed(),\
                    match._result[0], match._result[1]))
    base['matches'] = matches

    base['ps'] = request.GET['ps']
    base['bo'] = request.GET['bo']

    rrgroup_postable(base, obj, players, 
                     url='http://aligulac.com/predict/rrgroup/?bo=%s&ps=%s' % (base['bo'], base['ps']))
    return render_to_response('pred_rrgroup.html', base)

@cache_page
def pred_proleague(request):
    base = base_ctx('Predict', 'Predict', request=request)

    dbpl = [get_object_or_404(Player, id=int(i)) for i in request.GET['ps'].split(',')]
    sipl = [make_player(pl) for pl in dbpl]
    num = (int(request.GET['bo'])+1)/2
    nplayers = len(sipl)
    obj = teampl.TeamPL(num)
    obj.set_players(sipl)

    def update(request, obj, match, r1, r2):
        if r1 in request.GET and r2 in request.GET:
            try:
                if obj.get_match(match).can_modify():
                    obj.get_match(match).modify(int(request.GET[r1]), int(request.GET[r2]))
            except:
                pass
        else:
            obj.get_match(match).modify(0, 0)

    for i in range(0, obj._nplayers):
        update(request, obj, i, 'm%i-1' % i, 'm%i-2' % i)

    obj.compute()

    ResObj = namedtuple('ResObj', 'scl scw proba probb')
    base['results'] = []
    base['prob_draw'] = 0.0
    for score in range(0,obj._nplayers+1):
        if 2*score < obj._nplayers:
            base['results'].append(ResObj(score, obj._nplayers-score,
                        obj.get_tally()[1][score], obj.get_tally()[0][score]))
        elif 2*score == obj._nplayers:
            base['prob_draw'] = obj.get_tally()[0][score]
        if 2*score >= obj._nplayers:
            break
    base['t1'] = sum([r.proba for r in base['results']])
    base['t2'] = sum([r.probb for r in base['results']])

    MatchObj = namedtuple('MatchObj', 'obj pla plb modded canmod fixed sca scb')
    matches = []
    base['s1'], base['s2'] = 0, 0
    for i in range(0, obj._nplayers):
        match = obj.get_match(i)
        matches.append(MatchObj(match, match.get_player(0).dbpl, match.get_player(1).dbpl,\
                    match.is_modified(), match.can_modify(), match.is_fixed(),\
                    match._result[0], match._result[1]))
        if match.is_fixed():
            base['s1'] += 1 if match._result[0] > match._result[1] else 0
            base['s2'] += 1 if match._result[1] > match._result[0] else 0
    base['matches'] = matches

    base['ps'] = request.GET['ps']
    base['bo'] = request.GET['bo']

    proleague_postable(base, obj, base['results'], base['prob_draw'], 
                     url='http://aligulac.com/predict/proleague/?bo=%s&ps=%s' % (base['bo'], base['ps']))
    return render_to_response('pred_proleague.html', base)

def left_center_right(strings, gap=2, justify=True, indent=0):
    left_width = max([len(s[0]) for s in strings if s != None]) + 4
    center_width = max([len(s[1]) for s in strings if s != None])
    right_width = max([len(s[2]) for s in strings if s != None]) + 4
    
    if justify:
        left_width = max(left_width, right_width)
        right_width = left_width

    left_width += indent

    out = ''
    for s in strings:
        if s == None:
            out += ' '*indent
            out += '-'*(left_width + right_width + center_width + 2*gap - indent) + '\n'
            continue
        
        out += ' '*(left_width-len(s[0])) + s[0]

        R = (center_width-len(s[1]))/2
        L = center_width-len(s[1])-R
        out += ' '*(L+gap) + s[1] + ' '*(R+gap)

        out += s[2] + ' '*(right_width-len(s[2]))

        out += '\n'

    return out[:-1]

def match_postable(base, obj, r1, r2, url):
    pa = obj.get_player(0)
    pb = obj.get_player(1)

    numlen = len(str(obj._num))

    strings = [('({rat}) {name}'.format(rat=ratscale(pa.elo_vs_opponent(pb)), name=pa.name),\
                '{sca: >{nl}}-{scb: <{nl}}'.format(sca=obj._result[0], scb=obj._result[1], nl=numlen),\
                '{name} ({rat})'.format(rat=ratscale(pb.elo_vs_opponent(pa)), name=pb.name))]
    strings.append(None)
    
    for i in range(0, len(r1)):
        try:
            L = '{pctg: >6.2f}% {sca}-{scb: >{nl}}'.format(pctg=100*r1[i][2], sca=r1[i][0], scb=r1[i][1], nl=numlen)
        except:
            L = ''
        
        try:
            R = '{sca: >{nl}}-{scb} {pctg: >6.2f}%'.format(pctg=100*r2[i][2], sca=r2[i][0], scb=r2[i][1], nl=numlen)
        except:
            R = ''

        strings.append((L, '', R))

    strings += [None, ('{pctg: >6.2f}%'.format(pctg=100*base['t1']), '',\
                       '{pctg: >6.2f}%'.format(pctg=100*base['t2']))]

    ls = obj.find_lsup()

    postable_tl = left_center_right(strings)
    postable_tl += '\n\nMedian outcome: {pla} {sca}-{scb} {plb}'\
            .format(pla=pa.name, sca=ls[1], plb=pb.name, scb=ls[2])
    base['postable_tl'] = TL_HEADER + postable_tl + TL_FOOTER % url

    postable_reddit = left_center_right(strings, justify=False, indent=4)
    postable_reddit += '\n\n    Median outcome: {pla} {sca}-{scb} {plb}'\
            .format(pla=pa.name, sca=ls[1], plb=pb.name, scb=ls[2])
    base['postable_reddit'] = REDDIT_HEADER + postable_reddit + REDDIT_FOOTER % url

def fpswiss_postable(base, obj, players, url):
    nl = max([len(p.dbpl.tag) for p in players])

    strings = [('Top 2      1st      2nd      3rd      4th', '', ''), None]

    for p in players:
        strings.append(('{name: >{nl}}   {top2: >7.2f}% {p1: >7.2f}% {p2: >7.2f}% {p3: >7.2f}% {p4: >7.2f}%'\
                .format(top2=100*(p.tally[2]+p.tally[3]), p1=100*p.tally[3], p2=100*p.tally[2],\
                        p3=100*p.tally[1], p4=100*p.tally[0], name=p.dbpl.tag, nl=nl), '', ''))

    postable_tl = left_center_right(strings, justify=False, gap=0)
    base['postable_tl'] = TL_HEADER + postable_tl + TL_FOOTER % url

    postable_reddit = left_center_right(strings, justify=False, gap=0, indent=4)
    base['postable_reddit'] = REDDIT_HEADER + postable_reddit + REDDIT_FOOTER % url

def create_postable_bracket(bracket):
    nrounds = len(bracket)

    # result holds an array of lines for each
    # round. These are added together at the end.
    result = []

    for r in range(nrounds):
        result.append([])
        result[r].extend([u""] * (2 ** r - 1))
        
        for i in range(len(bracket[r])):
            (pla, plb, plascore, plbscore) = tuple(bracket[r][i])
            if pla is not None:
                pla = unicode(pla.tag)
            else:
                plascore = u""
                pla = u""
            if plb is not None:
                plb = unicode(plb.tag)
            else:
                plbscore = u""
                plb = u""

            if r != 0:
                pla = (u" " + pla).rjust(12, u"─")
                plb = (u" " + plb).rjust(12, u"─")
            else:
                pla = (u" " + pla).rjust(12)
                plb = (u" " + plb).rjust(12)
            result[r].append(u"{0} {1:>1} ┐ ".format(pla, plascore))
            result[r].extend([u"               │ "] * (2 ** r - 1))
            result[r].append(u"               ├─")
            result[r].extend([u"               │ "] * (2 ** r - 1))
            result[r].append(u"{0} {1:>1} ┘ ".format(plb, plbscore))

            if i < len(bracket[r]):
                result[r].extend([u"                 "] * int(2 ** (r + 1) - 1))

    result.append([u""] * (2 ** (r + 1) - 1))
    result[-1].append(u" " + (bracket[-1][0][0].tag
                              if bracket[-1][0][2] > bracket[-1][0][3] 
                              else bracket[-1][0][1].tag))

    postable_result = ""
    for line in range(len(result[0])):
        postable_result += ''.join(block[line] 
                                   for block in result 
                                   if line < len(block))
        postable_result += '\n'

    return postable_result.rstrip()

def sebracket_postable(base, obj, players, bracket, url):
    nl = max([len(p.dbpl.tag) for p in players if p.dbpl is not None])

    s =   'Win    '
    for i in range(1, int(log(len(players),2))+1):
        if i == int(log(len(players),2)):
            s +=  'Top {i}'.format(i=2**i)
        else:
            s +=  'Top {i: <5}'.format(i=2**i)
    strings = [(s, '', ''), None]

    for p in players:
        if p.dbpl is None:
            continue
        s = '{name: >{nl}}  '.format(name=p.dbpl.tag, nl=nl)
        for t in p.tally:
            s += ' {p: >7.2f}%'.format(p=100*t)
        strings.append((s, '', ''))

    tl_bracket = create_postable_bracket(bracket)

    postable_tl = left_center_right(strings, justify=False, gap=0)
    base['postable_tl'] = TL_SEBRACKET_HEADER + \
                          postable_tl + \
                          TL_SEBRACKET_MIDDLE + \
                          tl_bracket + \
                          (TL_SEBRACKET_FOOTER % url)

    postable_reddit = left_center_right(strings, justify=False, gap=0, indent=4)
    base['postable_reddit'] = REDDIT_HEADER + postable_reddit + REDDIT_FOOTER % url

def rrgroup_postable(base, obj, players, url):
    nl = max([len(p.dbpl.tag) for p in players])

    s =   ''
    for i in range(0, len(players)):
        if i == len(players)-1:
            s += ordinal(i+1) 
        else:
            s +=  '{s: <9}'.format(s=ordinal(i+1))
    strings = [(s, '', ''), None]

    for p in players:
        s = '{name: >{nl}}  '.format(name=p.dbpl.tag, nl=nl)
        for t in p.tally:
            s += ' {p: >7.2f}%'.format(p=100*t)
        strings.append((s, '', ''))

    postable_tl = left_center_right(strings, justify=False, gap=0)
    base['postable_tl'] = TL_HEADER + postable_tl + TL_FOOTER % url

    postable_reddit = left_center_right(strings, justify=False, gap=0, indent=4)
    base['postable_reddit'] = REDDIT_HEADER + postable_reddit + REDDIT_FOOTER % url

def proleague_postable(base, obj, res, pdraw, url):
    numlen = len(str(obj._nplayers))
    strings = [('{p} et al.'.format(p=obj._pla[0].dbpl.tag),
                '{sca: >{nl}}-{scb: <{nl}}'.format(sca=base['s1'], scb=base['s2'], nl=numlen),
                '{p} et al.'.format(p=obj._plb[0].dbpl.tag))]
    strings.append(None)

    for r in res:
        if r.proba == 0.0 and r.probb == 0.0:
            continue

        if r.proba > 0.0:
            L = '{pctg: >6.2f}% {sca}-{scb: >{nl}}'.format(pctg=100*r.proba, sca=r.scw, scb=r.scl, nl=numlen)
        else:
            L = ''

        if r.probb > 0.0:
            R = '{pctg: >6.2f}% {sca}-{scb: >{nl}}'.format(pctg=100*r.probb, sca=r.scl, scb=r.scw, nl=numlen)
        else:
            R = ''

        strings.append((L, '', R))

    strings += [None, ('{pctg: >6.2f}%'.format(pctg=100*base['t1']), '',
                       '{pctg: >6.2f}%'.format(pctg=100*base['t2']))]

    postable_tl = left_center_right(strings)
    if pdraw > 0.0:
        postable_tl += '\n\nProbability of draw/ace match: {pctg: >6.2f}%'.format(pctg=100*pdraw)
    base['postable_tl'] = TL_HEADER + postable_tl + TL_FOOTER % url

    postable_reddit = left_center_right(strings, justify=False, indent=4)
    if pdraw > 0.0:
        postable_reddit += '\n\n    Probability of draw/ace match: {pctg: >6.2f}%'.format(pctg=100*pdraw)
    base['postable_reddit'] = REDDIT_HEADER + postable_reddit + REDDIT_FOOTER % url

def ordinal(value):
    """
    Converts an integer to its ordinal as a string. 1 is '1st', 2 is '2nd',
    3 is '3rd', etc. Works for any integer.
    """
    try:
        value = int(value)
    except (TypeError, ValueError):
        return value
    suffixes = ('th', 'st', 'nd', 'rd', 'th', 'th', 'th', 'th', 'th', 'th')
    if value % 100 in (11, 12, 13): # special case
        return u"%d%s" % (value, suffixes[0])
    return u"%d%s" % (value, suffixes[value % 10])

def compare(request):
    base = base_ctx('Predict', 'Compare', request=request)

    if 'pla' not in request.GET and 'plb' not in request.GET:
        return render_to_response('compare.html', base)
    
    pla = find_player(request.GET['pla'].strip().split(' '), make=False)
    plb = find_player(request.GET['plb'].strip().split(' '), make=False)
    base['plas'] = request.GET['pla']
    base['plbs'] = request.GET['plb']

    for p, ps, id in [(pla, request.GET['pla'], 'pla'), (plb, request.GET['plb'], 'plb')]:
        if p.count() > 1:
            base['messages'].append(NotUniquePlayerMessage(ps, p, update=id))
        elif not p.exists():
            base['messages'].append(Message('No such player found.', ps, Message.ERROR))

    if len(base['messages']) > 0:
        return render_to_response('compare.html', base)

    pla, plb = pla[0], plb[0]
    base['pla'] = pla
    base['plb'] = plb

    rata = pla.rating_set.order_by('-period__id')[0]
    ratb = plb.rating_set.order_by('-period__id')[0]

    def analyze(pla, rata, plb, ratb, race):
        diff = rata.get_totalrating(race) - ratb.get_totalrating(race)
        dev = sqrt(rata.get_totaldev(race)**2 + ratb.get_totaldev(race)**2)
        if diff > 0:
            return pla, plb, cdf(-diff, scale=dev)
        else:
            return plb, pla, cdf(diff, scale=dev)

    base['winner'],    base['loser'],    base['sig'] =    analyze(pla, rata, plb, ratb, None)
    base['winner_vp'], base['loser_vp'], base['sig_vp'] = analyze(pla, rata, plb, ratb, 'P')
    base['winner_vt'], base['loser_vt'], base['sig_vt'] = analyze(pla, rata, plb, ratb, 'T')
    base['winner_vz'], base['loser_vz'], base['sig_vz'] = analyze(pla, rata, plb, ratb, 'Z')


    return render_to_response('compare.html', base)
