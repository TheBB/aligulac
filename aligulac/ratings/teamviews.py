import os
from pyparsing import nestedExpr

from aligulac.views import base_ctx
from tools import filter_active_ratings, filter_inactive_ratings

from django.shortcuts import render_to_response, get_object_or_404
from django.http import HttpResponse
from django.db.models import Q, Sum
from models import Player, Team, Rating, TeamMembership, Match, Alias
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
    base.update(csrf(request)) 

    team = get_object_or_404(Team, id=team_id)
    base['team'] = team

    # Make modifications
    if 'op' in request.POST and request.POST['op'] == 'Submit' and base['adm'] == True:

        name = request.POST['name']

        akas = request.POST['AKA']
        if akas != '':
            aka = [s for s in akas.split(',')]
        else:
            aka = None

        shortname = request.POST['shortname']
        if shortname == '':
            shortname = None

        homepage = request.POST['homepage']
        if homepage == '':
            homepage = None

        lp_name = request.POST['lp_name']
        if lp_name == '':
            lp_name = None

        if name!= '':
            team.set_name(name)
        team.set_aliases(aka)
        team.set_shortname(shortname)
        team.set_homepage(homepage)
        team.set_lp_name(lp_name)

    players = TeamMembership.objects.filter(team__name=team, current=True, playing=True)
    base['players'] = players 
    base['zerg'] = players.filter(player__race__exact='Z') 
    base['protoss'] = players.filter(player__race__exact='P') 
    base['terran'] = players.filter(player__race__exact='T')

    try: 
        base['aliases'] = Alias.objects.filter(team=team)
    except:
        pass
        
    total = 0
    offline = 0
    if players:
        for p in players:
            total += Match.objects.filter(Q(pla=p.player) | Q(plb=p.player)).count()
            offline += Match.objects.filter((Q(pla=p.player) | Q(plb=p.player)), offline=True).count()
        base['offline'] = round((100*float(offline)/float(total)),2)
     
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
