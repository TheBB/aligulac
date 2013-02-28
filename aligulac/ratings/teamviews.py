import os
from pyparsing import nestedExpr

from aligulac.views import base_ctx
from tools import filter_active_ratings, filter_inactive_ratings

from django.shortcuts import render_to_response, get_object_or_404
from django.http import HttpResponse
from django.db.models import Q, Sum
from models import Player, Team, Rating, TeamMembership
from django.contrib.auth import authenticate, login
from django.core.context_processors import csrf

from countries import transformations, data

def teams(request):
    base = base_ctx('Teams', 'Ranking', request)

    base['teams'] = Team.objects.filter(active=True)
    if 'sort' in request.GET and request.GET['sort'] == 'pl':
        base['teams'] = base['teams'].order_by('-scorepl', '-scoreak')
    else:
        base['teams'] = base['teams'].order_by('-scoreak', '-scorepl')

    base['inactive'] = Team.objects.filter(active=False).order_by('name')

    return render_to_response('teams.html', base)

def team(request, team_id):
    base = base_ctx('Teams', None, request)

    team = get_object_or_404(Team, id=team_id)
    base['team'] = team

    base['active'] = Rating.objects.filter(player__teammembership__team=team,\
            player__teammembership__current=True, player__teammembership__playing=True,\
            period=base['curp']).order_by('-rating')
    base['active'] = filter_active_ratings(base['active'])
    base['inactive'] = Rating.objects.filter(player__teammembership__team=team,\
            player__teammembership__current=True, player__teammembership__playing=True,\
            period=base['curp']).order_by('-rating')
    base['inactive'] = filter_inactive_ratings(base['inactive'])
    base['nonplaying'] = TeamMembership.objects.filter(team=team, current=True, playing=False).order_by('player__tag')
    base['past'] = TeamMembership.objects.filter(team=team, current=False).order_by('-end', 'player__tag')

    return render_to_response('team.html', base)

def player_transfers(request):
    base = base_ctx('Teams', 'Transfers', request)
    
    trades = TeamMembership.objects.filter(Q(start__isnull=False) | Q(end__isnull=False))
    trades = trades.extra(select={'cdate':'CASE\
                                            WHEN start IS NULL THEN end\
                                            WHEN end IS NULL THEN start\
                                            WHEN start > end THEN start\
                                            ELSE end\
                                            END'})
    trades = trades.order_by('-cdate')[0:25]

    base["trades"] = trades
    
    return render_to_response('player_transfers.html', base)
