import os
from pyparsing import nestedExpr

from aligulac.views import base_ctx, Message, generate_messages
from tools import filter_active_ratings, filter_inactive_ratings

from django.shortcuts import render_to_response, get_object_or_404
from django.http import HttpResponse
from django.db.models import Q, Sum
from models import Player, Group, Rating, GroupMembership, Match, Alias, Earnings
from django.contrib.auth import authenticate, login
from django.core.context_processors import csrf

from countries import transformations, data

def teams(request):
    base = base_ctx('Teams', 'Ranking', request)

    base['teams'] = Group.objects.filter(active=True, is_team=True)
    if 'sort' in request.GET and request.GET['sort'] == 'pl':
        base['teams'] = base['teams'].order_by('-scorepl', '-scoreak')
    else:
        base['teams'] = base['teams'].order_by('-scoreak', '-scorepl')

    base['inactive'] = Group.objects.filter(active=False, is_team=True).order_by('name')

    return render_to_response('teams.html', base)

def team(request, team_id):
    base = base_ctx('Teams', None, request)
    base.update(csrf(request)) 

    team = get_object_or_404(Group, id=team_id)
    base['team'] = team

    base['messages'] += generate_messages(team)

    # Make modifications
    if 'op' in request.POST and request.POST['op'] == 'Submit' and base['adm'] == True:

        name = request.POST['name']
        if name!= '' and name != team.name:
            team.set_name(name)
            base['messages'].append(Message('Changed team name.', type=Message.SUCCESS))

        akas = request.POST['AKA']
        if akas != '':
            aka = [s.strip() for s in akas.split(',')]
        else:
            aka = None
        team.set_aliases(aka)

        shortname = request.POST['shortname']
        if shortname != team.shortname:
            if team.shortname or shortname != '':
                team.set_shortname(shortname)
                base['messages'].append(Message('Changed short name.', type=Message.SUCCESS))

        homepage = request.POST['homepage']
        if homepage != team.homepage:
            if team.homepage or homepage != '':
                team.set_homepage(homepage)
                base['messages'].append(Message('Changed short homepage.', type=Message.SUCCESS))

        lp_name = request.POST['lp_name']
        if lp_name != team.lp_name:
            if team.lp_name or lp_name != '':
                team.set_lp_name(lp_name)
                base['messages'].append(Message('Changed Liquipedia title.', type=Message.SUCCESS))


    players = GroupMembership.objects.filter(group=team, current=True, playing=True)
    base['players'] = players 
    base['zerg'] = players.filter(player__race__exact='Z') 
    base['protoss'] = players.filter(player__race__exact='P') 
    base['terran'] = players.filter(player__race__exact='T')

    earnings = Earnings.objects.filter(player__in=players.values('player'))
    base['earnings'] = earnings.aggregate(Sum('earnings'))['earnings__sum']

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
     
    base['active'] = Rating.objects.filter(player__groupmembership__group=team,\
            player__groupmembership__current=True, player__groupmembership__playing=True,\
            period=base['curp']).order_by('-rating')
    base['active'] = filter_active_ratings(base['active'])
    base['inactive'] = Rating.objects.filter(player__groupmembership__group=team,\
            player__groupmembership__current=True, player__groupmembership__playing=True,\
            period=base['curp']).order_by('-rating')
    base['inactive'] = filter_inactive_ratings(base['inactive'])
    base['nonplaying'] = GroupMembership.objects.filter(group=team, 
            current=True, playing=False).order_by('player__tag')
    base['past'] = GroupMembership.objects.filter(group=team, current=False).order_by('-end', 'player__tag')

    return render_to_response('team.html', base)

def player_transfers(request):
    base = base_ctx('Teams', 'Transfers', request)
    
    trades = GroupMembership.objects.filter(Q(start__isnull=False) | Q(end__isnull=False))
    trades = trades.filter(group__is_team=True)
    trades = trades.extra(select={'cdate':'CASE\
                                            WHEN start IS NULL THEN end\
                                            WHEN end IS NULL THEN start\
                                            WHEN start > end THEN start\
                                            ELSE end\
                                            END'})
    trades = trades.order_by('-cdate')[0:25]

    base['trades'] = trades
    
    return render_to_response('player_transfers.html', base)
