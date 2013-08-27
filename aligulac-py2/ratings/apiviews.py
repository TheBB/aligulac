import os
import string
import random
import shlex
from datetime import datetime

from django.contrib.auth import logout
from django.shortcuts import render_to_response, redirect, get_object_or_404
from django.template.loader import render_to_string
from django.http import HttpResponse, HttpResponseNotFound
from django.core.context_processors import csrf
from django.db.models import Sum, Q
from django.contrib.auth.models import User

from aligulac.settings import DEBUG, PATH_TO_DIR
from ratings.models import Rating, Period, Player, Group, Match, Event, Earnings
import ratings.tools
from ratings.templatetags.ratings_extras import urlfilter

import simplejson

from countries import transformations

def player_object(p, sparse=False):
    dp = {'id': p.id, 'tag': p.tag, 'race': p.race}

    if p.country is not None and p.country != '':
        dp['country'] = transformations.cc_to_cn(p.country)
        dp['country-iso'] = p.country

    if sparse:
        return dp

    if p.name is not None:
        dp['name'] = p.name

    if p.birthday is not None:
        dp['birthday'] = str(p.birthday)

    dp['aliases'] = [a.name for a in p.alias_set.all()]

    try:
        team = p.groupmembership_set.filter(current=True, group__is_team=True)[0].group
        dp['team'] = team_object(team, sparse=True)
    except:
        pass

    return dp


def team_object(t, sparse=False):
    dt = {'id': t.id, 'name': t.name}

    if t.shortname is not None:
        dt['shortname'] = t.shortname

    if sparse:
        return dt

    dt['aliases'] = [a.name for a in t.alias_set.all()]

    dt['players'] = []
    for tm in t.groupmembership_set.filter(current=True, group__is_team=True):
        dt['players'].append(player_object(tm.player, sparse=True))

    return dt


def event_object(e, sparse=False):
    de = {'id': e.id, 'fullname': e.fullname, 'type': e.type}

    if sparse:
        return de

    if e.earliest is not None:
        de['earliest'] = str(e.earliest)

    if e.latest is not None:
        de['latest'] = str(e.latest)

    matches = Match.objects.filter(eventobj__lft__gte=e.lft, eventobj__rgt__lte=e.rgt)
    de['matches'] = matches.count()

    try:
        agg = matches.aggregate(Sum('sca'), Sum('scb'))
        de['games'] = agg['sca__sum'] + agg['scb__sum']
    except:
        de['games'] = 0

    if matches.values('game').distinct().count() == 1:
        de['game'] = matches[0].game

    totalearnings = Earnings.objects.filter(event__in=e.get_children(id=True))
    prizepool = totalearnings.aggregate(Sum('earnings'))['earnings__sum']
    de['prizepool'] = prizepool

    return de


def search_players(request, q='', soft=None, ret_object=False):
    if q == '':
        q = request.GET['q']
    if soft is None:
        soft = 'soft' in request.GET

    terms = shlex.split(q.encode())
    ret = []

    players = ratings.tools.find_player(terms, make=False, soft=soft)
    for p in players:
        ret.append(player_object(p))

    if ret_object:
        return ret
    else:
        return HttpResponse(simplejson.dumps(ret), mimetype='application/json')


def search_teams(request, q='', soft=None, ret_object=False):
    if q == '':
        q = request.GET['q']
    if soft is None:
        soft = 'soft' in request.GET

    terms = shlex.split(q.encode())
    ret = []

    teams = Group.objects.filter(is_team=True)
    for qpart in terms:
        if qpart.strip() == '':
            continue
        query = Q(name__icontains=qpart) | Q(alias__name__icontains=qpart) if soft else\
                Q(name=qpart) | Q(alias__name=qpart)
        teams = teams.filter(query)
    teams = teams.distinct()
    
    for t in teams:
        ret.append(team_object(t))

    if ret_object:
        return ret
    else:
        return HttpResponse(simplejson.dumps(ret), mimetype='application/json')


def search_events(request, q='', soft=None, ret_object=False):
    if q == '':
        q = request.GET['q']
    if soft is None:
        soft = 'soft' in request.GET

    terms = shlex.split(q.encode())
    ret = []

    events = Event.objects.filter(type__in=['category', 'event'])
    for qpart in terms:
        if qpart.strip() == '':
            continue
        query = Q(fullname__icontains=qpart) if soft else Q(fullname=qpart)
        events = events.filter(query)

    for e in events:
        ret.append(event_object(e))

    if ret_object:
        return ret
    else:
        return HttpResponse(simplejson.dumps(ret), mimetype='application/json')


def search(request, q='', soft=None):
    if soft is None:
        soft = 'soft' in request.GET

    ret = {'players': search_players(request, q, soft, ret_object=True),
           'teams':   search_teams(request, q, soft, ret_object=True),
           'events':  search_events(request, q, soft, ret_object=True)}

    return HttpResponse(simplejson.dumps(ret), mimetype='application/json')


def rating_list(request, period=None):
    if period is not None:
        period = get_object_or_404(Period, id=period, computed=True)
    else:
        period = Period.objects.filter(computed=True).order_by('-start')[0]

    ret = {'id': period.id, 'start': str(period.start), 'end': str(period.end),
            'retplayers': period.num_retplayers, 'newplayers': period.num_newplayers,
            'games': period.num_games, 'list': []}

    rats = ratings.tools.filter_active_ratings(Rating.objects.filter(period=period))
    rats = rats.select_related('player').order_by('-rating')

    number = 1
    for r in rats:
        ret['list'].append({'number': number, 'player': player_object(r.player, sparse=True),
            'rating': r.rating, 'rating_vp': r.rating_vp, 'rating_vt': r.rating_vt, 'rating_vz': r.rating_vz,
            'dev': r.dev, 'dev_vp': r.dev_vp, 'dev_vt': r.dev_vt, 'dev_vz': r.dev_vz, 'decay': r.decay})
        number += 1

    return HttpResponse(simplejson.dumps(ret), mimetype='application/json')
