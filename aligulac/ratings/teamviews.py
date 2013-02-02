import os
from pyparsing import nestedExpr

from aligulac.views import base_ctx

from django.shortcuts import render_to_response, get_object_or_404
from django.http import HttpResponse
from django.db.models import Q, Sum
from models import Player, Team, Rating, TeamMembership
from django.contrib.auth import authenticate, login
from django.core.context_processors import csrf

from countries import transformations, data

from scipy.stats import norm

def teams(request):
    base = base_ctx('Teams', request=request)

    base['teams'] = Team.objects.filter(active=True)
    if 'sort' in request.GET and request.GET['sort'] == 'pl':
        base['teams'] = base['teams'].order_by('-scorepl', '-scoreak')
    else:
        base['teams'] = base['teams'].order_by('-scoreak', '-scorepl')

    base['inactive'] = Team.objects.filter(active=False).order_by('name')

    return render_to_response('teams.html', base)

def team(request, team_id):
    base = base_ctx('Teams', request=request)

    team = get_object_or_404(Team, id=team_id)
    base['team'] = team

    base['active'] = Rating.objects.filter(player__teammembership__team=team,\
            player__teammembership__current=True, player__teammembership__playing=True,\
            period=base['curp'], decay__lt=4, dev__lte=0.2).order_by('-rating')
    base['inactive'] = Rating.objects.filter(player__teammembership__team=team,\
            player__teammembership__current=True, player__teammembership__playing=True,\
            period=base['curp']).exclude(decay__lt=4, dev__lte=0.2).order_by('-rating')
    base['past'] = TeamMembership.objects.filter(team=team, current=False).order_by('-end', 'player__tag')

    return render_to_response('team.html', base)
