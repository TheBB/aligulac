import os, datetime
from pyparsing import nestedExpr

from aligulac.parameters import RATINGS_INIT_DEV
from aligulac.views import base_ctx
from ratings.tools import find_player, display_matches, cdf, filter_active_ratings, event_shift, PATCHES

from django.shortcuts import render_to_response, get_object_or_404, redirect
from django.db.models import Q, F, Sum, Max
from models import Period, Rating, Player, Match, Team, TeamMembership, Event, Alias, Earnings
from django.contrib.auth import authenticate, login
from django.core.context_processors import csrf

from countries import transformations, data

from math import sqrt
from numpy import zeros

def collect(lst, n=2):
    ret, part = [], []
    for elem in lst:
        part.append(elem)
        if len(part) == n:
            ret.append(part)
            part = []
    
    while len(part) > 0 and len(part) < n:
        part.append(None)

    if len(part) > 0:
        ret.append(part)

    return ret

def periods(request):
    periods = Period.objects.filter(computed=True).order_by('-start')

    base = base_ctx('Ranking', 'History', request)
    base.update({'periods': periods})

    return render_to_response('periods.html', base)

def period(request, period_id, page='1'):
    psize = 40

    try:
        page = int(request.GET['page'])
    except:
        page = 1
    period = get_object_or_404(Period, id=period_id, computed=True)

    best = Rating.objects.filter(period=period, decay__lt=4, dev__lte=0.2).order_by('-rating')[0]
    bestvp = Rating.objects.filter(period=period, decay__lt=4, dev__lte=0.2)\
            .extra(select={'d':'rating+rating_vp'}).order_by('-d')[0]
    bestvt = Rating.objects.filter(period=period, decay__lt=4, dev__lte=0.2)\
            .extra(select={'d':'rating+rating_vt'}).order_by('-d')[0]
    bestvz = Rating.objects.filter(period=period, decay__lt=4, dev__lte=0.2)\
            .extra(select={'d':'rating+rating_vz'}).order_by('-d')[0]
    specvp = Rating.objects.filter(period=period, decay__lt=4, dev__lte=0.2)\
            .extra(select={'d':'rating_vp/dev_vp*rating'}).order_by('-d')[0]
    specvt = Rating.objects.filter(period=period, decay__lt=4, dev__lte=0.2)\
            .extra(select={'d':'rating_vt/dev_vt*rating'}).order_by('-d')[0]
    specvz = Rating.objects.filter(period=period, decay__lt=4, dev__lte=0.2)\
            .extra(select={'d':'rating_vz/dev_vz*rating'}).order_by('-d')[0]

    entries = Rating.objects.filter(period=period).select_related('team','teammembership')
    entries = filter_active_ratings(entries)

    try:
        race = request.GET['race']
    except:
        race = 'ptzrs'
    q = None
    for r in race:
        qt = Q(player__race=r.upper())
        if q == None:
            q = qt
        else:
            q = q | qt
    entries = entries.filter(q)

    try:
        nats = request.GET['nats']
    except:
        nats = 'all'
    if nats == 'kr':
        entries = entries.filter(player__country='KR')
    elif nats == 'foreigners':
        entries = entries.exclude(player__country='KR')

    try:
        sort = request.GET['sort']
    except:
        sort = ''
    if sort not in ['', 'vp', 'vt', 'vz']:
        sort = ''
    if sort == '':
        entries = entries.order_by('-rating', 'player__tag')
    elif sort == 'vp':
        entries = entries.extra(select={'d':'rating+rating_vp'}).order_by('-d', 'player__tag')
    elif sort == 'vt':
        entries = entries.extra(select={'d':'rating+rating_vt'}).order_by('-d', 'player__tag')
    elif sort == 'vz':
        entries = entries.extra(select={'d':'rating+rating_vz'}).order_by('-d', 'player__tag')

    nperiods = Period.objects.filter(computed=True).count()
    nitems = entries.count()
    npages = nitems/psize + (1 if nitems % psize > 0 else 0)
    page = min(max(page, 1), npages)

    entries = entries[(page-1)*psize:page*psize]

    for entry in entries:
        teams = entry.player.teammembership_set.filter(current=True)
        if teams.exists():
            entry.team = teams[0].team.shortname
            entry.teamfull = teams[0].team.name
            entry.teamid = teams[0].team.id

    base = base_ctx('Ranking', 'Current', request)
    base.update({'period': period, 'entries': entries, 'page': page, 'npages': npages, 'nperiods': nperiods,\
            'best': best, 'bestvp': bestvp, 'bestvt': bestvt, 'bestvz': bestvz, 'specvp': specvp,\
            'specvt': specvt, 'specvz': specvz, 'sortable': True, 'startcount': (page-1)*psize,
            'localcount': True, 'sort': sort, 'race': race, 'nats': nats})
    if period.id != base['curp'].id:
        base['curpage'] = ''

    return render_to_response('period.html', base)

def player(request, player_id):
    player = get_object_or_404(Player, id=player_id)
    base = base_ctx('Ranking', '%s:' % player.tag, request, context=player)
    base.update(csrf(request)) 
    
    # Make modifications
    if 'op' in request.POST and request.POST['op'] == 'Submit' and base['adm'] == True:
        tag = request.POST['tag']
        country = request.POST['country']
        name = request.POST['fullname']
        if name == '':
            name = None
        akas = request.POST['AKA']
        if akas != '':
            aka = [s for s in akas.split(',')]
        else:
            aka = None
        birthday = request.POST['birthday']
        if birthday == '':
            birthday = None
        sc2c = request.POST['SC2C']
        if sc2c == '':
            sc2c = None
        tlpdkr = request.POST['TLPDKR']
        if tlpdkr == '':
            tlpdkr = None
        tlpdin = request.POST['TLPDIN']
        if tlpdin == '':
            tlpdin = None
        sc2e = request.POST['SC2E']
        if sc2e == '':
            sc2e = None
        lp = request.POST['LP']
        if lp == '':
            lp = None

        if tag != '':
            player.set_tag(tag)        
        player.set_country(country)
        player.set_name(name)
        player.set_birthday(birthday)
        player.set_aliases(aka)
        player.update_external_links(sc2c, tlpdkr, tlpdin, sc2e, lp)

    countries = []
    for k, v in data.ccn_to_cn.iteritems():
        countries.append([k, v, data.ccn_to_cca2[k]])
    countries.sort(key=lambda a: a[1])
    base['countries'] = countries

    try:
        base['team'] = Team.objects.filter(active=True, teammembership__player=player, teammembership__current=True)[0]
    except:
        pass

    try:
        base['first'] = Match.objects.filter(Q(pla=player) | Q(plb=player)).order_by('date')[0]
        base['last'] = Match.objects.filter(Q(pla=player) | Q(plb=player)).order_by('-date')[0]
    except:
        pass

    base['totalmatches'] = Match.objects.filter(Q(pla=player) | Q(plb=player)).count()
    base['offlinematches'] = Match.objects.filter(Q(pla=player) | Q(plb=player), offline=True).count()
    base['aliases'] = Alias.objects.filter(player=player)
    
    earnings = Earnings.objects.filter(player=player)
    base['earnings'] = earnings.aggregate(Sum('earnings'))['earnings__sum']

    # Winrates
    matches_a = Match.objects.filter(pla=player)
    matches_b = Match.objects.filter(plb=player)

    def ntz(n):
        return n if n is not None else 0

    a = matches_a.aggregate(Sum('sca'), Sum('scb'))
    b = matches_b.aggregate(Sum('sca'), Sum('scb'))
    base['total'] = (ntz(a['sca__sum']) + ntz(b['scb__sum']), ntz(a['scb__sum']) + ntz(b['sca__sum']))

    a = matches_a.filter(rcb='P').aggregate(Sum('sca'), Sum('scb'))
    b = matches_b.filter(rca='P').aggregate(Sum('sca'), Sum('scb'))
    base['vp'] = (ntz(a['sca__sum']) + ntz(b['scb__sum']), ntz(a['scb__sum']) + ntz(b['sca__sum']))

    a = matches_a.filter(rcb='T').aggregate(Sum('sca'), Sum('scb'))
    b = matches_b.filter(rca='T').aggregate(Sum('sca'), Sum('scb'))
    base['vt'] = (ntz(a['sca__sum']) + ntz(b['scb__sum']), ntz(a['scb__sum']) + ntz(b['sca__sum']))

    a = matches_a.filter(rcb='Z').aggregate(Sum('sca'), Sum('scb'))
    b = matches_b.filter(rca='Z').aggregate(Sum('sca'), Sum('scb'))
    base['vz'] = (ntz(a['sca__sum']) + ntz(b['scb__sum']), ntz(a['scb__sum']) + ntz(b['sca__sum']))

    # Career highs
    try:
        base['highs'] = (Rating.objects.filter(player=player).order_by('-rating')[0],\
                 Rating.objects.filter(player=player).extra(select={'d':'rating+rating_vp'}).order_by('-d')[0],\
                 Rating.objects.filter(player=player).extra(select={'d':'rating+rating_vt'}).order_by('-d')[0],\
                 Rating.objects.filter(player=player).extra(select={'d':'rating+rating_vz'}).order_by('-d')[0])
    except:
        pass

    try:
        countryfull = transformations.cc_to_cn(player.country)
    except:
        countryfull = ''

    rating = Rating.objects.filter(player=player).order_by('period').select_related('period')
    base['charts'] = rating.count >= 2
    if base['charts']:
        base['ratings'] = rating
        base['patches'] = PATCHES

    recentchange = Rating.objects.filter(player=player, decay=0).order_by('-period')
    if recentchange.exists():
        base['recentchange'] = recentchange[0]

    firstrating = Rating.objects.filter(player=player).order_by('period')
    if firstrating.exists():
        base['firstrating'] = firstrating[0]

    if not rating.exists():
        base.update({'player': player, 'countryfull': countryfull})
        return render_to_response('player.html', base)
    rating = rating.order_by('-period')[0]

    matches = Match.objects.filter(Q(pla=player) | Q(plb=player))\
            .select_related('pla__rating').select_related('plb__rating')\
            .select_related('period')\
            .extra(where=['abs(datediff(date,\'%s\')) < 90' % datetime.datetime.now()])\
            .order_by('-date', '-id')[0:10]

    if matches.exists():
        base['matches'] = display_matches(matches, fix_left=player, ratings=True)

    def meandate(tm):
        if tm.start != None and tm.end != None:
            return (tm.start.toordinal() + tm.end.toordinal())/2
        elif tm.start != None:
            return tm.start.toordinal()
        elif tm.end != None:
            return tm.end.toordinal()
        else:
            return 1000000

    teammems = list(TeamMembership.objects.filter(player=player).extra(select={'mid': '(start+end)/2'}))
    teammems = sorted(teammems, key=lambda t: t.id, reverse=True)
    teammems = sorted(teammems, key=meandate, reverse=True)
    teammems = sorted(teammems, key=lambda t: t.current, reverse=True)

    base.update({'player': player, 'countryfull': countryfull, 'rating': rating, 'teammems': teammems})
    return render_to_response('player.html', base)

def player_historical(request, player_id):
    player = get_object_or_404(Player, id=player_id)
    base = base_ctx('Ranking', 'Rating history', request, context=player)

    hist = list(Rating.objects.filter(player=player, period__computed=True).order_by('period__end'))
    historical = []

    init = 0
    search = 1
    while True:
        while init < len(hist) and hist[init].decay > 0:
            init += 1
        if init >= len(hist):
            break
        search = init + 1

        while search < len(hist) and hist[search].decay < 4:
            search += 1
        fin = search
        if search < len(hist):
            fin = search - 3
        
        if len(historical) > 0:
            historical.append(None)
        historical += hist[init:fin]

        init = search + 1

    historical = historical[::-1]

    base.update({'player': player, 'historical': historical})
    return render_to_response('historical.html', base)

def results(request):
    base = base_ctx('Results', 'By Date', request)

    try:
        ints = [int(x) for x in request.GET['d'].split('-')]
        td = datetime.date(ints[0], ints[1], ints[2])
    except:
        td = datetime.date.today()

    matches = Match.objects.filter(date=td).order_by('eventobj__lft', 'event', 'id')

    base['matches'] = display_matches(matches, date=False, ratings=True)
    base['td'] = td

    return render_to_response('results.html', base)

def results_search(request):
    base = base_ctx('Results', 'Search', request)
    base.update(csrf(request))

    if 'op' in request.POST and request.POST['op'] == 'Modify' and base['adm'] == True:
        num = 0
        if request.POST['event'] != 'nochange' and int(request.POST['event']) != 2:
            event = Event.objects.get(id=int(request.POST['event']))
        else:
            event = None

        for key in request.POST:
            if request.POST[key] != 'y':
                continue
            if key[0:6] == 'match-':
                match = Match.objects.get(id=int(key.split('-')[-1]))
                if request.POST['event'] != 'nochange':
                    match.eventobj = event
                    base['markevent'] = event
                if request.POST['date'].strip() != '':
                    match.date = request.POST['date']
                    base['markdate'] = request.POST['date']
                if request.POST['type'] != 'nochange':
                    match.offline = (request.POST['type'] == 'offline')
                    base['markoffline'] = request.POST['type']
                if request.POST['game'] != 'nochange':
                    match.game = request.POST['game']
                    base['markgame'] = request.POST['game']
                match.save()
                num += 1

        base['message'] = 'Modified %i matches.' % num

    if 'op' in request.GET and request.GET['op'] == 'search':
        matches = Match.objects.all()

        try:
            ints = [int(x) for x in request.GET['after'].split('-')]
            td = datetime.date(ints[0], ints[1], ints[2])
            matches = matches.filter(date__gte=td)
            base['after'] = request.GET['after']
        except:
            pass

        try:
            ints = [int(x) for x in request.GET['before'].split('-')]
            td = datetime.date(ints[0], ints[1], ints[2])
            matches = matches.filter(date__lte=td)
            base['before'] = request.GET['before']
        except:
            pass

        if 'unassigned' in request.GET and request.GET['unassigned'] == 'yes' and base['adm']:
            base['unassigned'] = True
            base['unassigned_get'] = 'yes'
            matches = matches.filter(eventobj__isnull=True)

        if 'eventtext' in request.GET and request.GET['eventtext'].strip() != '':
            base['eventtext'] = request.GET['eventtext'].strip()
            queries = [f.strip() for f in request.GET['eventtext'].strip().split(' ') if f.strip() != '']
            for query in queries:
                q = Q(eventobj__isnull=True, event__icontains=query) |\
                    Q(eventobj__isnull=False, eventobj__fullname__icontains=query)
                matches = matches.filter(q)

        if 'bo' in request.GET:
            if request.GET['bo'] == '3':
                matches = matches.filter(Q(sca__gte=2) | Q(scb__gte=2))
            elif request.GET['bo'] == '5':
                matches = matches.filter(Q(sca__gte=3) | Q(scb__gte=3))
            base['bo'] = request.GET['bo']
        else:
            base['bo'] = 'all'
        
        if 'offline' in request.GET:
            if request.GET['offline'] == 'online':
                matches = matches.filter(offline=0)
            elif request.GET['offline'] == 'offline':
                matches = matches.filter(offline=1)
            base['offline'] = request.GET['offline']
        else:
            base['offline'] = 'both'

        if 'game' in request.GET:
            if request.GET['game'] != 'all':
                matches = matches.filter(game=request.GET['game'])
            base['game'] = request.GET['game']
        else:
            base['game'] = 'all'

        players, failures = [], []
        base['errs'] = []
        base['pls'] = request.GET['players']
        for line in request.GET['players'].splitlines():
            if line.strip() == '':
                continue
            pls = find_player(line.strip().split(' '), make=False)
            if not pls.exists():
                base['errs'].append('No players matching the query \'%s\'.' % line.strip())
            else:
                players.append(pls)

        if len(base['errs']) > 0:
            return render_to_response('results_search.html', base)

        pls = []
        for p in players:
            pls += p

        if len(pls) > 1:
            qa, qb = Q(), Q()
            for p in pls:
                qa |= Q(pla=p)
                qb |= Q(plb=p)
            matches = matches.filter(qa & qb)
        elif len(pls) == 1:
            q = Q(pla=pls[0]) | Q(plb=pls[0])
            matches = matches.filter(q)

        base['count'] = matches.count()

        if base['count'] > 1000:
            base['errs'].append('Too many results (%i). Please add restrictions.' % base['count'])
            return render_to_response('results_search.html', base)

        matches = matches.order_by('-date', 'eventobj__lft', 'event', 'id')

        if 1 <= len(pls) <= 2:
            base['matches'] = display_matches(matches, date=True, fix_left=pls[0])
            base['sc_my'] = sum([m.pla_score for m in base['matches']])
            base['sc_op'] = sum([m.plb_score for m in base['matches']])
            base['msc_my'] = sum([(1 if m.pla_score > m.plb_score else 0) for m in base['matches']])
            base['msc_op'] = sum([(1 if m.pla_score < m.plb_score else 0) for m in base['matches']])
            base['left'] = pls[0]
            if len(pls) == 2:
                base['right'] = pls[1]
        else:
            base['matches'] = display_matches(matches, date=True)

        if base['adm']:
            base['events'] = Event.objects.filter(closed=False, rgt=F('lft')+1).order_by('lft')

    return render_to_response('results_search.html', base)

def events(request, event_id=None):
    # Redirect to proper URL if there's a ?goto=... present
    if 'goto' in request.GET:
        return redirect('/results/events/' + request.GET['goto'])

    base = base_ctx('Results', 'By Event', request)
    base.update(csrf(request))
    
    try:
        event = Event.objects.get(id=int(event_id))
    except:
        # This is executed for invalid event IDs or the root table
        ind_bigs = collect(Event.objects.filter(parent__isnull=True, big=True, category='individual').\
                select_related('event').order_by('lft'), 2)
        ind_smalls = Event.objects.filter(parent__isnull=True, big=False, category='individual').\
                select_related('event').order_by('name')

        team_bigs = collect(Event.objects.filter(parent__isnull=True, big=True, category='team').\
                select_related('event').order_by('lft'), 2)
        team_smalls = Event.objects.filter(parent__isnull=True, big=False, category='team').\
                select_related('event').order_by('name')

        freq_bigs = collect(Event.objects.filter(parent__isnull=True, big=True, category='frequent').\
                select_related('event').order_by('lft'), 2)
        freq_smalls = Event.objects.filter(parent__isnull=True, big=False, category='frequent').\
                select_related('event').order_by('name')

        base.update({'ind_bigs': ind_bigs,   'ind_smalls': ind_smalls,\
                     'team_bigs': team_bigs, 'team_smalls': team_smalls,\
                     'freq_bigs': freq_bigs, 'freq_smalls': freq_smalls})
        return render_to_response('events.html', base)

    # Number of matches (set event to big if too large)
    matches = Match.objects.filter(eventobj__lft__gte=event.lft, eventobj__rgt__lte=event.rgt)
    if matches.count() > 200 and not event.big:
        event.big = True
        event.save()
        
    # Get parent, ancestors and siblings
    if event.parent != None:
        siblings = event.parent.event_set.exclude(id=event.id).order_by('lft')
    else:
        siblings = None

    # Make modifications if neccessary
    if base['adm'] == True:
        if 'op' in request.POST and request.POST['op'] == 'Modify':
            if request.POST['type'] != 'nochange':
                event.change_type(request.POST['type'])
                if 'siblings' in request.POST.keys() and siblings is not None:
                    for sibling in siblings:
                        sibling.change_type(request.POST['type'])
                        
            if request.POST['name'] != '' and request.POST['name'] != event.name:
                event.name = request.POST['name']
                event.update_name()
                event.save()
                for e in event.get_children():
                    e.update_name()

            if request.POST['date'].strip() != 'No change':
                matches.update(date=request.POST['date'])
                base['message'] = 'Modified all matches.'

            if request.POST['offline'] != 'nochange':
                matches.update(offline=(request.POST['offline'] == 'offline'))
                base['message'] = 'Modified all matches.'

            if request.POST['game'] != 'nochange':
                matches.update(game=request.POST['game'])
                base['message'] = 'Modified all matches.'

            if request.POST['homepage'] != event.get_homepage():
                event.set_homepage(request.POST['homepage'])

            if request.POST['lp_name'] != event.get_lp_name():
                event.set_lp_name(request.POST['lp_name'])
                        
        elif 'add' in request.POST and request.POST['add'] == 'Add':
            parent = event
            for q in request.POST['subevent'].strip().split(','):
                type = request.POST['type']
                parent.add_child(q.strip(), type, 'noprint' in request.POST, 'closed' in request.POST)
                
        elif 'move' in request.POST and request.POST['move'] == 'Move':
            eventid = request.POST['moveevent']
            newparent = Event.objects.get(id=eventid)

            if event.lft > newparent.rgt:
                diff = newparent.rgt - event.lft
            else:
                diff = newparent.rgt - event.rgt - 1
            event_shift(event, diff)

            event.set_parent(newparent)
            event.update_name()

            for e in event.get_children():
                e.update_name()

        elif 'earnings' in request.POST and request.POST['earnings'] == 'Add':
            amount = int(request.POST['amount'])
            
            players = []
            amounts = []
            placements = []
            
            for i in range(0, amount):
                player = request.POST['player-' + str(i)]
                player = Player.objects.get(id=player)
                
                amount = request.POST['amount-' + str(i)]
                amount = amount.replace(',', '').replace('.', '').strip()
                
                players.append(player)
                amounts.append(amount)
                placements.append(i)
            
            success = Earnings.set_earnings(event, players, amounts, placements)
            if success:
                base['message'] = 'Updated tournament prizepool.'
            else:
                base['message'] = 'There was an error updating the tournament prizepool.'

    base['event'] = event
    base['path'] = Event.objects.filter(lft__lte=event.lft, rgt__gte=event.rgt).order_by('lft')
    base['children'] = Event.objects.filter(parent=event).order_by('lft')
    if event.parent != None:
        base['siblings'] = event.parent.event_set.exclude(id=event.id).order_by('lft')

    # Used for moving events
    base['surroundingevents'] = event.get_parent(1).get_children()

    # Determine WoL/HotS and Online/Offline and event type
    if matches.values("game").distinct().count() == 1:
        base['game'] = matches[0].game
        if base['game'] == 'WoL':
            base['game'] = 'Wings of Liberty'
        elif base['game'] == 'HotS':
            base['game'] = 'Heart of the Swarm'
        #elif base['game'] = 'LotV':
            #base['game'] = 'Legacy of the Void'
    
    # Get list of players and earnings for prizepools
    base['players'] = Player.objects.filter(Q(id__in=matches.values('pla')) | Q(id__in=matches.values('plb')))
    
    earnings = Earnings.objects.filter(event=event).order_by('placement')
    base['earnings'] = earnings
    
    base['prizepool'] = earnings.aggregate(Sum('earnings'))['earnings__sum']
    
    
    if event.type:
        base['eventtype'] = event.type
        
    if event.get_homepage():
        base['homepage'] = event.get_homepage()
    if event.get_lp_name():
        base['lp_name'] = event.get_lp_name()

    base['offline'] = None
    if matches.values("offline").distinct().count() == 1:
        base['offline'] = matches[0].offline

    # Statistics
    base['nmatches'] = matches.count()
    if base['nmatches'] > 0:
        qset = matches.aggregate(Sum('sca'), Sum('scb'))
        base['ngames'] = qset['sca__sum'] + qset['scb__sum']
    else:
        base['ngames'] = 0

    # Matchup wins and losses
    nti = lambda x: 0 if x is None else x
    qseta = matches.filter(rca='P', rcb='T').aggregate(Sum('sca'), Sum('scb'))
    qsetb = matches.filter(rcb='P', rca='T').aggregate(Sum('sca'), Sum('scb'))
    base['pvt_wins'] = nti(qseta['sca__sum']) + nti(qsetb['scb__sum'])
    base['pvt_loss'] = nti(qsetb['sca__sum']) + nti(qseta['scb__sum'])

    qseta = matches.filter(rca='P', rcb='Z').aggregate(Sum('sca'), Sum('scb'))
    qsetb = matches.filter(rcb='P', rca='Z').aggregate(Sum('sca'), Sum('scb'))
    base['pvz_wins'] = nti(qseta['sca__sum']) + nti(qsetb['scb__sum'])
    base['pvz_loss'] = nti(qsetb['sca__sum']) + nti(qseta['scb__sum'])

    qseta = matches.filter(rca='T', rcb='Z').aggregate(Sum('sca'), Sum('scb'))
    qsetb = matches.filter(rcb='T', rca='Z').aggregate(Sum('sca'), Sum('scb'))
    base['tvz_wins'] = nti(qseta['sca__sum']) + nti(qsetb['scb__sum'])
    base['tvz_loss'] = nti(qsetb['sca__sum']) + nti(qseta['scb__sum'])

    # Dates
    try:
        base['earliest'] = matches.order_by('date')[0].date
        base['latest'] = matches.order_by('-date')[0].date
    except:
        pass

    # This is too slow. What to do?
    # base['nplayers'] = Player.objects.filter(
    #         Q(match_pla__eventobj__lft__gte=event.lft, match_pla__eventobj__rgt__lte=event.rgt)\
    #       | Q(match_plb__eventobj__lft__gte=event.lft, match_plb__eventobj__rgt__lte=event.rgt))\
    #         .distinct().count()

    matches = matches.order_by('-date', '-eventobj__lft', '-id')[0:200]
    base['matches'] = display_matches(matches)

    return render_to_response('eventres.html', base)

def player_results(request, player_id):
    player = get_object_or_404(Player, id=int(player_id))
    matches = Match.objects.filter(Q(pla=player) | Q(plb=player))

    base = base_ctx('Ranking', 'Match history', request, context=player)

    if 'race' in request.GET:
        q = None
        for r in request.GET['race']:
            try:
                q |= Q(pla=player, rcb=r)
                q |= Q(plb=player, rca=r)
            except:
                q = Q(pla=player, rcb=r)
                q |= Q(plb=player, rca=r)
        matches = matches.filter(q)
        base['race'] = request.GET['race']
    else:
        base['race'] = 'ptzr'

    if 'nats' in request.GET:
        if request.GET['nats'] == 'foreigners':
            matches = matches.exclude(Q(pla=player, plb__country='KR') | Q(plb=player, pla__country='KR'))
        elif request.GET['nats'] == 'kr':
            matches = matches.filter(Q(pla=player, plb__country='KR') | Q(plb=player, pla__country='KR'))
        base['nats'] = request.GET['nats']
    else:
        base['nats'] = 'all'

    if 'bo' in request.GET:
        if request.GET['bo'] == '3':
            matches = matches.filter(Q(sca__gte=2) | Q(scb__gte=2))
        elif request.GET['bo'] == '5':
            matches = matches.filter(Q(sca__gte=3) | Q(scb__gte=3))
        base['bo'] = request.GET['bo']
    else:
        base['bo'] = 'all'
    
    if 'offline' in request.GET:
        if request.GET['offline'] == 'online':
            matches = matches.filter(offline=0)
        elif request.GET['offline'] == 'offline':
            matches = matches.filter(offline=1)
        base['offline'] = request.GET['offline']
    else:
        base['offline'] = 'both'

    if 'game' in request.GET:
        if request.GET['game'] != 'all':
            matches = matches.filter(game=request.GET['game'])
        base['game'] = request.GET['game']
    else:
        base['game'] = 'all'
    
    matches = matches.order_by('-date', '-eventobj__lft', 'event', '-id')
    matches = matches.select_related('pla__rating').select_related('plb__rating').select_related('period')

    base['matches'] = display_matches(matches, fix_left=player, ratings=True)
    
    base['sc_my'] = sum([m.pla_score for m in base['matches']])
    base['sc_op'] = sum([m.plb_score for m in base['matches']])
    base['msc_my'] = sum([1 if m.pla_score > m.plb_score else 0 for m in base['matches']])
    base['msc_op'] = sum([1 if m.plb_score > m.pla_score else 0 for m in base['matches']])
    
    base['player'] = player
    
    return render_to_response('player_results.html', base)

def rating_details(request, player_id, period_id):
    period_id = int(period_id)
    player_id = int(player_id)

    period = get_object_or_404(Period, id=period_id, computed=True)
    player = get_object_or_404(Player, id=player_id, rating__period=period)
    rating = get_object_or_404(Rating, player=player, period=period)

    base = base_ctx('Ranking', 'Adjustments', request, context=player)

    try:
        nextlink = Rating.objects.filter(player=player, period__id__gt=period_id,\
                decay=0).order_by('period__id')[0]
    except:
        nextlink = None

    try:
        prevlink = Rating.objects.filter(player=player, period__id__lt=period_id,\
                decay=0).order_by('-period__id')[0]
    except:
        prevlink = None

    races = ['P','T','Z']

    prev = rating.get_prev()
    if prev != None:
        prevrat = [prev.get_rating(), {}]
        prevdev = [prev.get_dev(), {}]
        for r in races:
            prevrat[1][r] = prev.get_totalrating(r)
            prevdev[1][r] = prev.get_totaldev(r)
    else:
        prevrat = [0., {'P': 0., 'T': 0., 'Z': 0.}]
        prevdev = [RATINGS_INIT_DEV, {'P': RATINGS_INIT_DEV, 'T': RATINGS_INIT_DEV, 'Z': RATINGS_INIT_DEV}]

    matches = Match.objects.filter(Q(pla=player) | Q(plb=player)).filter(period=period)\
            .select_related('pla__rating').select_related('plb__rating').order_by('-date', '-id')
    if not matches.exists():
        base.update({'period': period, 'player': player, 'prevlink': prevlink, 'nextlink': nextlink})
        return render_to_response('ratingdetails.html', base)

    matches = display_matches(matches, fix_left=player, ratings=True)

    tot_rating = [0.0, {'P': 0.0, 'T': 0.0, 'Z': 0.0}]
    ngames = [0, {'P': 0, 'T': 0, 'Z': 0}]
    nwins = [0, {'P': 0, 'T': 0, 'Z': 0}]
    nlosses = [0, {'P': 0, 'T': 0, 'Z': 0}]
    expwins = [0.0, {'P': 0.0, 'T': 0.0, 'Z': 0.0}]

    treated = False
    nontreated = False
    for m in matches:
        if not m.treated:
            nontreated = True
            continue
        treated = True

        tot_rating[0] += m.plb_rating * (m.pla_score + m.plb_score)
        ngames[0] += m.pla_score + m.plb_score
        nwins[0] += m.pla_score
        nlosses[0] += m.plb_score

        scale = sqrt(1 + m.pla_dev**2 + m.pla_dev**2)

        races = [m.plb_race] if m.plb_race in ['P','T','Z'] else ['P','T','Z']
        weight = float(1)/len(races)
        for sr in races:
            ew = (m.pla_score + m.plb_score) * cdf(m.pla_rating - m.plb_rating, scale=scale)
            expwins[0] += weight * ew
            expwins[1][sr] += weight * ew

            tot_rating[1][sr] += weight * m.plb_rating * (m.pla_score + m.plb_score)
            ngames[1][sr] += weight * (m.pla_score + m.plb_score)
            nwins[1][sr] += weight * m.pla_score
            nlosses[1][sr] += weight * m.plb_score

    base.update({'period': period, 'player': player, 'rating': rating, 'matches': matches, 'treated': treated,\
            'nontreated': nontreated, 'prevlink': prevlink, 'nextlink': nextlink})
    if not treated:
        return render_to_response('ratingdetails.html', base)
    else:
        tot_rating[0] /= ngames[0]
        for r in ['P','T','Z']:
            if ngames[1][r] > 0:
                tot_rating[1][r] /= ngames[1][r]
        explosses = [ngames[0]-expwins[0], {}]
        exppctg = [expwins[0]/ngames[0]*100, {}]
        pctg = [float(nwins[0])/ngames[0]*100, {}]
        diff = [rating.rating-prevrat[0], {}]
        modded = False
        for r in ['P','T','Z']:
            explosses[1][r] = ngames[1][r] - expwins[1][r]
            if ngames[1][r] > 0:
                exppctg[1][r] = expwins[1][r]/ngames[1][r]*100
                pctg[1][r] = float(nwins[1][r])/ngames[1][r]*100
            diff[1][r] = rating.get_totalrating(r) - prevrat[1][r]
            if (nwins[1][r] != 0) != (nlosses[1][r] != 0):
                modded = True

        base.update({'tot_rating': tot_rating, 'ngames': ngames, 'nwins': nwins, 'nlosses': nlosses,\
                     'prevrat': prevrat, 'pctg': pctg,\
                     'exppctg': exppctg, 'diff': diff, 'expwins': expwins, 'explosses': explosses,\
                     'prevdev': prevdev, 'modded': modded})
        return render_to_response('ratingdetails.html', base)

def records(request):
    try:
        race = request.GET['race']
        sub = ['HoF','All','Protoss','Terran','Zerg'][['hof','all','P','T','Z'].index(race)]
    except:
        race = 'hof'
        sub = 'HoF'

    base = base_ctx('Records', sub, request)

    if race in ['all', 'T', 'P', 'Z']:
        high = Rating.objects.extra(select={'rat': 'rating'})\
                .filter(period__id__gt=24, decay__lt=4, dev__lte=0.2)
        highp = Rating.objects.extra(select={'rat': 'rating+rating_vp'})\
                .filter(period__id__gt=24, decay__lt=4, dev__lte=0.2)
        hight = Rating.objects.extra(select={'rat': 'rating+rating_vt'}).\
                filter(period__id__gt=24, decay__lt=4, dev__lte=0.2)
        highz = Rating.objects.extra(select={'rat': 'rating+rating_vz'}).\
                filter(period__id__gt=24, decay__lt=4, dev__lte=0.2)
        dom = Rating.objects.extra(select={'rat': 'domination'}).\
                filter(domination__gt=0.0, period__id__gt=24, decay__lt=4, dev__lte=0.2)

        if race in ['P','T','Z']:
            high = high.filter(player__race=request.GET['race'])
            highp = highp.filter(player__race=request.GET['race'])
            hight = hight.filter(player__race=request.GET['race'])
            highz = highz.filter(player__race=request.GET['race'])
            dom = dom.filter(player__race=request.GET['race'])
            base.update({'race': request.GET['race']})
        else:
            base.update({'race': ''})

        def sift(lst, num=5):
            ret = []
            pls = []
            for r in lst:
                if not r.player.id in pls:
                    pls.append(r.player.id)
                    ret.append(r)
                if len(ret) == num:
                    return ret
            return ret

        high = sift(high.order_by('-rat')[0:200])
        highp = sift(highp.order_by('-rat')[0:200])
        hight = sift(hight.order_by('-rat')[0:200])
        highz = sift(highz.order_by('-rat')[0:200])
        dom = sift(dom.order_by('-rat')[0:200])

        base.update({'hightot': high, 'highp': highp, 'hight': hight, 'highz': highz, 'dom': dom})
        return render_to_response('records.html', base)

    elif race in ['hof'] or True:
        base['high'] = Player.objects.filter(dom_val__isnull=False, dom_start__isnull=False,\
                dom_end__isnull=False, dom_val__gt=0).order_by('-dom_val')
        return render_to_response('hof.html', base)

def balance(request):
    base = base_ctx('Reports', 'Balance', request)

    first = (2010,7)
    last = (datetime.date.today().year, datetime.date.today().month-1)
    if last[1] == 0:
        last[0] -= 1
        last[1] = 12

    N = (last[0]-first[0])*12 + last[1]-first[1] + 1

    def nti(x):
        return 0 if x is None else x

    def add_to_array(qset, rc1, rc2, ar, col):
        temp = qset.filter(rca=rc1, rcb=rc2).aggregate(Sum('sca'), Sum('scb'))
        ar[0, col] += nti(temp['sca__sum'])
        ar[1, col] += nti(temp['scb__sum'])
        temp = qset.filter(rca=rc2, rcb=rc1).aggregate(Sum('sca'), Sum('scb'))
        ar[0, col] += nti(temp['scb__sum'])
        ar[1, col] += nti(temp['sca__sum'])

    pvt_scores = zeros((2,N))
    pvz_scores = zeros((2,N))
    tvz_scores = zeros((2,N))
    time = []

    ind = 0
    delta = datetime.timedelta(days=15)
    while first[0] < last[0] or (first[0] == last[0] and first[1] <= last[1]):
        matches = Match.objects.filter(date__gte='%i-%i-01' % first)
        if first[1] < 12:
            matches = matches.filter(date__lt='%i-%i-01' % (first[0], first[1]+1))
        else:
            matches = matches.filter(date__lt='%i-%i-01' % (first[0]+1, 1))

        add_to_array(matches, 'P', 'T', pvt_scores, ind)
        add_to_array(matches, 'P', 'Z', pvz_scores, ind)
        add_to_array(matches, 'T', 'Z', tvz_scores, ind)
        time.append(datetime.date(month=first[1], year=first[0], day=15))

        first = (first[0], first[1]+1)
        if first[1] == 13:
            first = (first[0]+1, 1)
        ind += 1

    base['pvt'] = zip(100*pvt_scores[0,:]/(pvt_scores[0,:] + pvt_scores[1,:]), time)
    base['pvz'] = zip(100*pvz_scores[0,:]/(pvz_scores[0,:] + pvz_scores[1,:]), time)
    base['tvz'] = zip(100*tvz_scores[0,:]/(tvz_scores[0,:] + tvz_scores[1,:]), time)

    base['charts'] = True
    base['patches'] = PATCHES
    return render_to_response('reports_balance.html', base)
