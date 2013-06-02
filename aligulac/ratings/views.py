import os, datetime
import ccy
import operator
import shlex
from pyparsing import nestedExpr

from aligulac.parameters import RATINGS_INIT_DEV
from aligulac.views import base_ctx, Message, NotUniquePlayerMessage, generate_messages
from ratings.tools import find_player, display_matches, cdf, filter_active_ratings, event_shift,\
                          get_placements, PATCHES
from ratings.templatetags.ratings_extras import datemax, datemin

from django.shortcuts import render_to_response, get_object_or_404, redirect
from django.db.models import Q, F, Sum, Max
from models import Period, Rating, Player, Match, Team, TeamMembership, Event, Alias, Earnings,\
                   BalanceEntry, Story
from django.contrib.auth import authenticate, login
from django.core.context_processors import csrf

from countries import transformations, data

from math import sqrt
from numpy import zeros, array

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
    base = base_ctx('Ranking', 'Current', request)
    psize = 40

    try:
        page = int(request.GET['page'])
    except:
        page = 1

    period = get_object_or_404(Period, id=period_id, computed=True)
    if period.is_preview():
        base['messages'].append(Message(
            'This is a <em>preview</em> of the next rating list. It will not be finalized until '\
                    + period.end.strftime('%B %d') + '.',
            type=Message.INFO))

    # Best and most specialised players
    best = filter_active_ratings(Rating.objects.filter(period=period)).order_by('-rating')[0]
    bestvp = filter_active_ratings(Rating.objects.filter(period=period))\
            .extra(select={'d':'rating+rating_vp'}).order_by('-d')[0]
    bestvt = filter_active_ratings(Rating.objects.filter(period=period))\
            .extra(select={'d':'rating+rating_vt'}).order_by('-d')[0]
    bestvz = filter_active_ratings(Rating.objects.filter(period=period))\
            .extra(select={'d':'rating+rating_vz'}).order_by('-d')[0]
    specvp = filter_active_ratings(Rating.objects.filter(period=period))\
            .extra(select={'d':'rating_vp/dev_vp*rating'}).order_by('-d')[0]
    specvt = filter_active_ratings(Rating.objects.filter(period=period))\
            .extra(select={'d':'rating_vt/dev_vt*rating'}).order_by('-d')[0]
    specvz = filter_active_ratings(Rating.objects.filter(period=period))\
            .extra(select={'d':'rating_vz/dev_vz*rating'}).order_by('-d')[0]

    # Matchup statistics
    ntz = lambda k: k if k is not None else 0

    def wl(rca, rcb):
        ms = Match.objects.filter(period=period, rca=rca, rcb=rcb).aggregate(Sum('sca'), Sum('scb'))
        w = ntz(ms['sca__sum'])
        l = ntz(ms['scb__sum'])
        ms = Match.objects.filter(period=period, rca=rcb, rcb=rca).aggregate(Sum('sca'), Sum('scb'))
        w += ntz(ms['scb__sum'])
        l += ntz(ms['sca__sum'])
        return w, l
    
    pvt_wins, pvt_loss = wl('P', 'T')
    pvz_wins, pvz_loss = wl('P', 'Z')
    tvz_wins, tvz_loss = wl('T', 'Z')

    # Build country list
    countriesDict = []
    countries = []
    for p in Player.objects.filter(rating__period_id=period.id, rating__decay__lt=4).distinct().values('country'):
        if p['country'] not in countriesDict and p['country'] is not None and p['country'] != '':
            countriesDict.append(p['country'])
    for country in countriesDict:
        d = {'cc': country, 'name': data.ccn_to_cn[data.cca2_to_ccn[country]]}
        countries.append(d)
    countries.sort(key=lambda a: a['name'])

    # Filtering the ratings
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
    if nats == 'foreigners':
        entries = entries.exclude(player__country='KR')
    elif nats != 'all':
        entries = entries.filter(player__country=nats)

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

    # Pages
    nperiods = Period.objects.filter(computed=True).count()
    nitems = entries.count()
    npages = nitems/psize + (1 if nitems % psize > 0 else 0)
    page = min(max(page, 1), npages)

    try:
        entries = entries[(page-1)*psize:page*psize]
    except:
        pass

    # Collect team data
    for entry in entries:
        teams = entry.player.teammembership_set.filter(current=True)
        if teams.exists():
            entry.team = teams[0].team.shortname
            entry.teamfull = teams[0].team.name
            entry.teamid = teams[0].team.id

    # Render
    base.update({'period': period, 'entries': entries, 'page': page, 'npages': npages, 'nperiods': nperiods,
            'best': best, 'bestvp': bestvp, 'bestvt': bestvt, 'bestvz': bestvz, 'specvp': specvp,
            'specvt': specvt, 'specvz': specvz, 'sortable': True, 'startcount': (page-1)*psize,
            'localcount': True, 'sort': sort, 'race': race, 'nats': nats,
            'pvt_wins': pvt_wins, 'pvt_loss': pvt_loss, 'pvz_wins': pvz_wins,
            'pvz_loss': pvz_loss, 'tvz_wins': tvz_wins, 'tvz_loss': tvz_loss,
            'countries': countries})
    if period.id != base['curp'].id:
        base['curpage'] = ''

    return render_to_response('period.html', base)

def player(request, player_id):
    player = get_object_or_404(Player, id=player_id)
    base = base_ctx('Ranking', '%s:' % player.tag, request, context=player)
    base.update(csrf(request)) 

    base['messages'] += generate_messages(player)
    
    # Make modifications
    if 'op' in request.POST and request.POST['op'] == 'Submit' and base['adm'] == True:
        tag = request.POST['tag']
        if tag != '' and tag != player.tag:
            player.set_tag(tag)
            base['messages'].append(Message('Changed tag.', Message.SUCCESS))
        
        country = request.POST['country']
        if country != player.country:
            player.set_country(country)
            base['messages'].append(Message('Changed country.', Message.SUCCESS))
        
        name = request.POST['fullname']
        if name != player.name:
            if player.name or name != '':
                player.set_name(name)
                base['messages'].append(Message('Changed name.', Message.SUCCESS))

        akas = request.POST['AKA']
        if akas != '':
            aka = [s.strip() for s in akas.split(',')]
        else:
            aka = None
        player.set_aliases(aka)
        #base['message'] += "Changed player's aliases. "

        birthday = request.POST['birthday']
        if birthday != str(player.birthday):
            if player.birthday or birthday != '':
                player.set_birthday(birthday)
                base['messages'].append(Message('Changed birthday.', Message.SUCCESS))

        sc2c = request.POST['SC2C']
        if sc2c != str(player.sc2c_id):
            if player.sc2c_id or sc2c != '':
                player.set_sc2c_id(sc2c)
                base['messages'].append(Message('Changed SC2Charts.net ID.', Message.SUCCESS))
        
        tlpdid = request.POST['TLPD']
        tlpddb = 0
        if request.POST.get('TLPDKR'):
            tlpddb += 0b1
        if request.POST.get('TLPDIN'):
            tlpddb += 0b10
        if request.POST.get('TLPDHOTS'):
            tlpddb += 0b100
        if request.POST.get('TLPDHOTSBETA'):
            tlpddb += 0b1000
        if request.POST.get('TLPDWOLBETA'):
            tlpddb += 0b10000

        if tlpdid != str(player.tlpd_id) or tlpddb != player.tlpd_db:
            if player.tlpd_id or tlpdid != '':
                player.set_tlpd_id(tlpdid, tlpddb)
                if tlpdid == '' or tlpddb == 0:
                    base['messages'].append(Message('Removed TLPD information.', Message.SUCCESS))
                else:
                    base['messages'].append(Message('Changed TLPD information.', Message.SUCCESS))
        
        sc2e = request.POST['SC2E']
        if sc2e != str(player.sc2e_id):
            if player.sc2e_id or sc2e != '':
                player.set_sc2e_id(sc2e)
                base['messages'].append(Message('Changed SC2Earnings.com ID.', Message.SUCCESS))

        lp = request.POST['LP']
        if lp != str(player.lp_name):
            if player.lp_name or lp != '':
                player.set_lp_name(lp)
                base['messages'].append(Message('Changed Liquipedia title.', Message.SUCCESS))

    def meandate(tm):
        if tm.start != None and tm.end != None:
            return (tm.start.toordinal() + tm.end.toordinal())/2
        elif tm.start != None:
            return tm.start.toordinal()
        elif tm.end != None:
            return tm.end.toordinal()
        else:
            return 1000000

    def interp_rating(date, ratings):
        for ind, r in enumerate(ratings):
            if (r.period.end - date).days >= 0:
                try:
                    right = (r.period.end - date).days
                    left = (date - ratings[ind-1].period.end).days
                    return (left*r.bf_rating + right*ratings[ind-1].bf_rating) / (left+right)
                except:
                    return r.bf_rating
        return ratings[-1].bf_rating

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
        base['highs'] = (Rating.objects.filter(player=player).order_by('-rating')[0],
             Rating.objects.filter(player=player).extra(select={'d':'rating+rating_vp'}).order_by('-d')[0],
             Rating.objects.filter(player=player).extra(select={'d':'rating+rating_vt'}).order_by('-d')[0],
             Rating.objects.filter(player=player).extra(select={'d':'rating+rating_vz'}).order_by('-d')[0])
    except:
        pass

    try:
        countryfull = transformations.cc_to_cn(player.country)
    except:
        countryfull = ''

    teammems = list(TeamMembership.objects.filter(player=player).extra(select={'mid': '(start+end)/2'}))
    teammems = sorted(teammems, key=lambda t: t.id, reverse=True)
    teammems = sorted(teammems, key=meandate, reverse=True)
    teammems = sorted(teammems, key=lambda t: t.current, reverse=True)

    rating = Rating.objects.filter(player=player).order_by('period').select_related('period')
    try:
        last_adjust = Rating.objects.filter(player=player, decay=0).order_by('-period')[0]
        base['charts'] = last_adjust.period_id > rating[0].period_id
    except:
        # No rating
        base['messages'].append(Message('%s has no rating yet.' % player.tag, type=Message.INFO))
        base['charts'] = False

    if base['charts']:
        last_adjust = Rating.objects.filter(player=player, decay=0).order_by('-period')[0]
        rating = rating.filter(period_id__lte=last_adjust.period_id)
        base['ratings'] = rating
        base['patches'] = PATCHES

        # Add points to graph when player left or joined a team.
        # Creates an array if dictionaries in the form of date:date, rating:rating, data:[{date:date, team:team, jol:jol}, {...}]
        latest = Rating.objects.filter(player=player, decay=0).order_by('-period')
        if latest:
            latest = latest[0]
            earliest = Rating.objects.filter(player=player, decay=0).order_by('period')[0]
            teampoints = []
            for teammem in teammems:
                dict = {}
                if teammem.start:
                    if earliest.period.start < teammem.start < latest.period.start:
                        dict['date'] = teammem.start
                        dict['rating'] = interp_rating(teammem.start, base['ratings'])
                        dict['data'] = []
                        dict['data'].append({'date':teammem.start, 'team':teammem.team, 'jol':'joins'})
                        teampoints.append(dict)
                dict = {}
                if teammem.end:
                    if earliest.period.start < teammem.end < latest.period.start:
                        dict['date'] = teammem.end
                        dict['rating'] = interp_rating(teammem.end, base['ratings'])
                        dict['data'] = []
                        dict['data'].append({'date':teammem.end, 'team':teammem.team, 'jol':'leaves'})
                        teampoints.append(dict)
            teampoints.sort(key=lambda a: a['date'])
            # Condense items if team switches happened within 14 days.
            days = 14
            if len(teampoints) > 1:
                search = True
                cur = 0
                while search:
                    timediff = teampoints[cur+1]['date'] - teampoints[cur]['date']
                    if timediff.days <= days:
                        teampoints[cur]['data'].append(teampoints[cur+1]['data'][0])
                        teampoints.remove(teampoints[cur+1])
                    else:
                        cur += 1
                    if not cur < len(teampoints)-1:
                        search = False
            # Sort data in array, first by date, then by joined/left
            for point in teampoints:
                point['data'].sort(key=lambda a: a['jol'], reverse=True)
                point['data'].sort(key=lambda a: a['date'])
            base['teampoints'] = teampoints

            # Add stories
            stories = player.story_set.all()
            for s in stories:
                if earliest.period.start < s.date < latest.period.start:
                    s.rating = interp_rating(s.date, base['ratings'])
                else:
                    s.skip = True
            base['stories'] = stories
    else:
        # No charts
        base['messages'].append(Message(
            '%s has no rating chart on account of having played matches in fewer than two periods.'\
                    % player.tag, type=Message.INFO))

    recentchange = Rating.objects.filter(player=player, decay=0).order_by('-period')
    if recentchange.exists():
        base['recentchange'] = recentchange[0]

    firstrating = Rating.objects.filter(player=player).order_by('period')
    if firstrating.exists():
        base['firstrating'] = firstrating[0]

    r = Rating.objects.filter(player=player)
    if not r.exists():
        base.update({'player': player, 'countryfull': countryfull})
        return render_to_response('player.html', base)
    rating = r.order_by('-period')[0]

    matches = Match.objects.filter(Q(pla=player) | Q(plb=player))\
            .select_related('pla__rating').select_related('plb__rating')\
            .select_related('period')\
            .prefetch_related('message_set')\
            .extra(where=['abs(datediff(date,\'%s\')) < 90' % datetime.datetime.now()])\
            .order_by('-date', '-id')[0:10]

    if matches.exists():
        base['matches'] = display_matches(matches, fix_left=player, ratings=True)

    base.update({'player': player, 'countryfull': countryfull, 'rating': rating,
                 'teammems': teammems})
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

    base['mindate'] = datetime.date(year=2010, month=2, day=25)
    base['maxdate'] = datetime.date.today()
    td = datemax(td, base['mindate'])
    td = datemin(td, base['maxdate'])
    base['td'] = td

    matches = Match.objects.filter(date=td).order_by('eventobj__lft', 'event', 'id')
    matches = matches.prefetch_related('message_set')
    base['matches'] = display_matches(matches, date=False, ratings=True)

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
                    match.set_event(event)
                    base['markevent'] = event
                if request.POST['date'].strip() != '':
                    match.set_date(request.POST['date'])
                    base['markdate'] = request.POST['date']
                if request.POST['type'] != 'nochange':
                    match.offline = (request.POST['type'] == 'offline')
                    base['markoffline'] = request.POST['type']
                if request.POST['game'] != 'nochange':
                    match.game = request.POST['game']
                    base['markgame'] = request.POST['game']
                match.save()
                num += 1

        base['messages'].append(Message('Successfully modified %i matches.' % num, type=Message.SUCCESS))

    if 'op' in request.GET and request.GET['op'] == 'search':
        matches = Match.objects.all().prefetch_related('message_set')

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
            queries = [f.strip() for f in shlex.split(request.GET['eventtext'].strip()) if f.strip() != '']
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
        ok = True
        base['pls'] = request.GET['players']
        lineno = -1
        for line in request.GET['players'].splitlines():
            lineno += 1
            if line.strip() == '':
                continue
            pls = find_player(line.strip().split(' '), make=False)
            if not pls.exists():
                base['messages'].append(Message('No players matching this query.', line.strip(),
                                                type=Message.ERROR))
                ok = False
            else:
                if pls.count() > 1:
                    base['messages'].append(NotUniquePlayerMessage(line.strip(), pls, update='players',
                                                                   updateline=lineno, type=Message.WARNING))
                players.append(pls)

        if not ok:
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
            base['messages'].append(Message(
                'Too many results (%i). Please add restrictions.' % base['count'], type=Message.ERROR))
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

    base['messages'] += generate_messages(event)

    # Number of matches (set event to big if too large)
    matches = Match.objects.filter(eventobj__lft__gte=event.lft, eventobj__rgt__lte=event.rgt)
    matches = matches.select_related('pla', 'plb', 'eventobj')
    if matches.count() > 200 and not event.big:
        event.big = True
        event.save()
        
    # Get parent, ancestors and siblings
    if event.parent != None:
        siblings = event.parent.event_set.exclude(id=event.id).order_by('lft')
    else:
        siblings = None

    # Make modifications if neccessary
    # TODO: This block is way too long and should be moved somewhere else.
    if base['adm'] == True:

        if 'op' in request.POST and request.POST['op'] == 'Modify':
            if request.POST['name'] != '' and request.POST['name'] != event.name:
                event.name = request.POST['name']
                event.update_name()
                event.save()
                for e in event.get_children():
                    e.update_name()
                base['messages'].append(Message('Changed event name.', type=Message.SUCCESS))

            if request.POST['date'].strip() != 'No change':
                mcounter = 0
                for match in matches:
                    match.set_date(request.POST['date'])
                    mcounter += 1
                base['messages'].append(Message('Changed date for %i matches.' % mcounter, 
                                        type=Message.SUCCESS))

            if request.POST['game'] != 'nochange':

                opgame = None
                if matches.values("game").distinct().count() == 1:
                    opgame = matches[0].game
                
                if request.POST['game'] != opgame or not opgame:
                    matches.update(game=request.POST['game'])
                    base['messages'].append(Message('Set game version to %s for %i matches.'
                        % (request.POST['game'], matches.count()), type=Message.SUCCESS))

            if request.POST['offline'] != 'nochange':
                
                opoffline = None
                if matches.values("offline").distinct().count() == 1:
                    if matches[0].offline:
                        opoffline = 'offline'
                    else:
                        opoffline = 'online'
                
                if request.POST['offline'] != opoffline or not opoffline:
                    matches.update(offline=(request.POST['offline'] == 'offline'))
                    base['messages'].append(Message('Set match type to %s for %i matches.'
                        % (request.POST['offline'], matches.count()), type=Message.SUCCESS))

            #Set new type if new type is != old type or sibling checkbox is set. 
            if request.POST['type'] != 'nochange' and\
                            (request.POST['type'] != event.type or 'siblings' in request.POST.keys()):
                event.change_type(request.POST['type'])
                mtext = 'Set new event type'
                base['messages'].append(Message('Set new event type.', type=Message.SUCCESS))
                if 'siblings' in request.POST.keys() and siblings is not None:
                    mtext += ' for this and sibling events'
                    for sibling in siblings:
                        sibling.change_type(request.POST['type'])
                mtext += '. This may have affected child- and parent events.'
                base['messages'].append(Message(mtext, type=Message.SUCCESS))

            #Check if new ID is not the same as old ID
            if request.POST['homepage'] != event.get_homepage():
                #Special case: Make sure not to delete already empty old ID.
                if event.get_homepage() or request.POST['homepage'] != '':
                    event.set_homepage(request.POST['homepage'])
                    base['messages'].append(Message('Changed homepage.', type=Message.SUCCESS))

            if 'TLPDDB' in request.POST:
                tlpdid = request.POST['TLPD']
                tlpddbstr = request.POST['TLPDDB']
                if tlpddbstr  == 'TLPDKR':
                    tlpddb = 0b1
                elif tlpddbstr == 'TLPDIN':
                    tlpddb = 0b10
                elif tlpddbstr == 'TLPDHOTS':
                    tlpddb = 0b100
                elif tlpddbstr == 'TLPDHOTSBETA':
                    tlpddb = 0b1000
                elif tlpddbstr == 'TLPDWOLBETA':
                    tlpddb = 0b10000
    
                if tlpdid != str(event.tlpd_id) or tlpddb != event.tlpd_db:
                    if event.tlpd_id or tlpdid != '':
                        event.set_tlpd_id(tlpdid, tlpddb)
                        if tlpdid == '' or tlpddb == 0:
                            base['messages'].append(Message('Removed TLPD info.', type=Message.SUCCESS))
                        else:
                            base['messages'].append(Message('Changed TLPD info.', type=Message.SUCCESS))
                    
            if request.POST['tl_thread'] != str(event.get_tl_thread()):
                if event.get_tl_thread() or request.POST['tl_thread'] != '':
                    event.set_tl_thread(request.POST['tl_thread'])
                    base['messages'].append(Message('Changed TL.net thread ID.', type=Message.SUCCESS))

            if request.POST['lp_name'] != event.get_lp_name():
                if event.get_lp_name() or request.POST['lp_name'] != '':
                    event.set_lp_name(request.POST['lp_name'])
                    base['messages'].append(Message('Changed Liquipedia page title.', type=Message.SUCCESS))
            
            #event.get_prizepool()
            if request.POST.get("prizepoolselect") and event.get_prizepool() is not False:
                event.set_prizepool(False)
                Earnings.objects.filter(event=event).delete()
                base['messages'].append(Message('Marked this event as having no prize pool.',
                                                type=Message.SUCCESS))
            elif event.get_prizepool() is False:
                event.set_prizepool(None) 
                base['messages'].append(Message('Marked this event as having  prize pool.',
                                                type=Message.SUCCESS))
                        
        elif 'add' in request.POST and request.POST['add'] == 'Add':
            parent = event
            nadd = 0
            for q in request.POST['subevent'].strip().split(','):
                addtype = request.POST['type']
                parent.add_child(q.strip(), addtype, 'noprint' in request.POST, 'closed' in request.POST)
                nadd += 1
            base['messages'].append(Message('Added %i children events.' % nadd, type=Message.SUCCESS))
                
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
            # This is very slow if used for many matches, but that should rarely happen.
            for e in event.get_parents(id=True):
                e.update_dates()


            base['messages'].append(Message('Moved this event under \'%s\'' % newparent.fullname,
                                            type=Message.SUCCESS))

        elif 'movepp' in request.POST and request.POST['movepp'] == 'Move':
            neweventid = request.POST['moveprizepool']
            newevent = Event.objects.get(id=neweventid)
            event.move_earnings(newevent)
            base['messages'].append(Message('Moved prize pool to \'%s\'' % newevent.fullname,
                                            type=Message.SUCCESS))

        elif 'earnings' in request.POST and request.POST['earnings'] == 'Add':
            amount = int(request.POST['amount'])
            currency = request.POST['currency']
            
            players = []
            amounts = []
            placements = []
            
            for i in range(0, amount):
                player = request.POST['player-' + str(i)]
                player = Player.objects.get(id=player)
                
                amount = request.POST['amount-' + str(i)]
                amount = amount.replace(',', '').replace('.', '').replace(' ', '')
                
                players.append(player)
                amounts.append(amount)
                if request.POST['un-ranked'] == "ranked":
                    placements.append(i)
                elif request.POST['un-ranked'] == "unranked":
                    placements.append(-1)
            
            success = Earnings.set_earnings(event, players, amounts, currency, placements)
            
            if success:
                base['messages'].append(Message('Successfully updated prize pool.', type=Message.SUCCESS))
            else:
                base['messages'].append(Message('Unable to update prize pool.', type=Message.ERROR))
                
        elif 'deleteearnings' in request.POST and request.POST['deleteearnings'] == 'Delete':
            if request.POST['un-ranked'] == "ranked":
                event.delete_earnings()
                base['messages'].append(Message('Successfully deleted ranked prize pool', 
                                                type=Message.SUCCESS))
            elif request.POST['un-ranked'] == "unranked":
                event.delete_earnings(ranked=False)
                base['messages'].append(Message('Successfully deleted unranked prize pool', 
                                                type=Message.SUCCESS))

        elif 'addstory' in request.POST and request.POST['addstory'] == 'Add story':
            player = Player.objects.get(id=int(request.POST['player']))
            date = request.POST['date']
            text = request.POST['text']
            if not Story.objects.filter(player=player, event=event, date=date).exists():
                new = Story(player=player, event=event, date=date, text=text)
                new.save()
                base['messages'].append(Message('Added a story for %s.' % player.tag, type=Message.SUCCESS))
            else:
                base['messages'].append(Message('Story not added, a duplicate exists.', type=Message.ERROR))

    base['event'] = event
    base['path'] = Event.objects.filter(lft__lte=event.lft, rgt__gte=event.rgt).order_by('lft')
    base['children'] = Event.objects.filter(parent=event).order_by('lft')
    if event.parent != None:
        base['siblings'] = event.parent.event_set.exclude(id=event.id).order_by('lft')

    # Used for moving events
    base['surroundingevents'] = event.get_parent(1).get_children().exclude(lft__gte=event.lft,
                                                                           rgt__lte=event.rgt)
    
    # Used for moving prize pools
    base['childevents'] = event.get_children()

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
    
    # earnings for this event
    totalearningsevent = Earnings.objects.filter(event=event).order_by('placement')

    # earnings for this event + all child events
    totalearnings = Earnings.objects.filter(event__in=event.get_children(id=True)).order_by('placement')
    
    # ranked earnings
    rearnings = totalearningsevent.exclude(placement__exact=0)
    base['rearnings'] = rearnings
    
    # unranked earnings
    urearnings = totalearningsevent.filter(placement__exact=0)
    base['urearnings'] = urearnings

    # total prizepool in dollars
    base['prizepool'] = totalearnings.aggregate(Sum('earnings'))['earnings__sum']

    # get number of currencies used
    numcur = {}
    for earning in totalearnings:
        numcur[earning.currency] = True
    # total prizepool in original currencies. 
    # Gives out an array of dictionaries in the form of [{pp: prize pool, cur: currecy}, ...]
    # also sets nousdpp to True if there is a non-USD prize pool currency
    prizepoolorig = []
    if len(numcur) > 0:
        for k,v in numcur.items():
             prizepoolorig.append({"pp": totalearnings.filter(currency=k).aggregate(Sum('origearnings'))['origearnings__sum'], "cur": k})
             if k != "USD":
                 base['nousdpp'] = True
        base['prizepoolorig'] = prizepoolorig
    
    #prize pool currency for current event
    try:
        base['prizepoolcur'] = totalearningsevent[0].currency
    except:
        base['prizepoolcur'] = "USD"
    
    # Get list of currencies
    currencies = []
    sortedcurrencies = sorted(ccy.currencydb(), key=operator.itemgetter(0))

    for currency in sortedcurrencies:
        dict = {}
        dict["name"] = ccy.currency(currency).name
        dict["code"] = ccy.currency(currency).code
        currencies.append(dict)
    base['currencies'] = currencies
    
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
    base['earliest'] = event.earliest
    base['latest'] = event.latest

    matches = matches.prefetch_related('message_set').order_by('-date', '-eventobj__lft', '-id')[0:200]
    base['matches'] = display_matches(matches)

    return render_to_response('eventres.html', base)

def player_results(request, player_id):
    player = get_object_or_404(Player, id=int(player_id))
    matches = Match.objects.filter(Q(pla=player) | Q(plb=player)).prefetch_related('message_set')

    base = base_ctx('Ranking', 'Match history', request, context=player)

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

def player_earnings(request, player_id):
    player = get_object_or_404(Player, id=int(player_id))

    base = base_ctx('Ranking', 'Earnings', request, context=player)

    # Get earnings and total earnings.
    earnings = Earnings.objects.filter(player=player)
    totalearnings = earnings.aggregate(Sum('earnings'))['earnings__sum']
    
    # Get placements for events. 
    for event in earnings:
        dict = get_placements(event.event)
        for earning, placement in dict.items():
            if event.placement in placement:
                event.min = min(placement)
                event.max = max(placement)
    
    # Get dictionary of earnings in the form of Currency:TotalEarnings.
    earningsByCurrency = {}
    for earning in earnings:
        try:
            earningsByCurrency[earning.currency] += earning.origearnings
        except:
            earningsByCurrency[earning.currency] = earning.origearnings
    
    # Set earningsByCurrency to None when there is only one currency: USD.
    if len(earningsByCurrency) == 1 and 'USD' in earningsByCurrency:
        earningsByCurrency = None
    
    # Sort earnings by latest date.
    def getLatest( e ):
        return e.event.latest
    earnings = list(earnings)
    earnings.sort( key=getLatest, reverse=True )

    base.update({'player': player, 'earnings': earnings, 'totalearnings': totalearnings, 'earningsByCurrency': earningsByCurrency})
    
    return render_to_response('player_earnings.html', base)

def earnings(request):
    base = base_ctx('Ranking', 'Earnings', request)

    try:
        page = int(request.GET['page'])
    except:
        page = 1

    # Get list of countries of players that earned money.
    # Creates two arrays: countries, an array of dictionaries in the form of cc:countryCode, name:countryName,
    # used for the dropdown selection in the html, and countriesDict, an array of country codes, used
    # in the main query when the filter is set to "all".
    countriesDict = []
    countries = []
    for player in Player.objects.filter(earnings__player__isnull=False).distinct().values('country'):
        if player['country'] not in countriesDict and player['country'] is not None and player['country'] != '':
            countriesDict.append(player['country'])
    for country in countriesDict:
            dict = {}
            dict['cc'] = country
            dict['name'] = data.ccn_to_cn[data.cca2_to_ccn[country]]
            countries.append(dict)
    countries.sort(key=lambda a: a['name'])

    # Get currencies used.
    # Usage see above.
    currenciesDict = []
    currencies = []
    for currency in Earnings.objects.values('currency').distinct().order_by('currency'):
        dict = {}
        dict["name"] = ccy.currency(currency['currency']).name
        dict["code"] = ccy.currency(currency['currency']).code
        currencies.append(dict)
        currenciesDict.append(currency['currency'])

    # Filters
    filters = {}
    # Filter by year
    if 'year' in request.GET and request.GET['year'] != 'all':
        year = int(request.GET['year'])
        fromdate = datetime.date(year, 1, 1)
        todate = datetime.date(year+1, 1, 1)
        filters["year"] = year
    else:
        fromdate = datetime.date(1900, 1, 1)
        todate = datetime.date(2100, 1, 1)
        filters["year"] = 'all'
    # Filter by country
    if 'country' in request.GET and request.GET['country'] != 'all'  and request.GET['country'] != 'foreigners':
        filters['country'] = request.GET['country']
        countriesQuery = [request.GET['country']]
    elif 'country' in request.GET and request.GET['country'] == 'foreigners':
        filters['country'] = request.GET['country']
        countriesQuery = countriesDict
        countriesQuery.remove('KR')
    else:
        filters['country'] = 'all'
        countriesQuery = countriesDict
    # Filter by currency
    if 'currency' in request.GET and request.GET['currency'] != 'all':
        filters['currency'] = request.GET['currency']
        currenciesQuery = [request.GET['currency']]
    else: 
        filters['currency'] = 'all'
        currenciesQuery = currenciesDict

    # Create ranking and total prize pool amount based on filters.
    ranking = Earnings.objects.filter(event__latest__gte=fromdate, event__latest__lt=todate, currency__in=currenciesQuery, player__country__in=countriesQuery).\
    values('player').annotate(totalorigearnings=Sum('origearnings')).annotate(totalearnings=Sum('earnings')).order_by('-totalearnings', 'player')
    totalorigprizepool = Earnings.objects.filter(event__latest__gte=fromdate, event__latest__lt=todate, currency__in=currenciesQuery, player__country__in=countriesQuery)\
    .aggregate(Sum('origearnings'))['origearnings__sum']
    totalprizepool = Earnings.objects.filter(event__latest__gte=fromdate, event__latest__lt=todate, currency__in=currenciesQuery, player__country__in=countriesQuery)\
    .aggregate(Sum('earnings'))['earnings__sum']

    # Add player and team objects to ranking.
    for player in ranking:
        player["playerobj"] = Player.objects.get(id=player["player"])
        try:
            player["teamobj"] = player["playerobj"].teammembership_set.get(current=True)
        except:
            pass
    
    # Split ranking into 40 player sized pages
    psize = 40
    nitems = ranking.count()
    npages = nitems/psize + (1 if nitems % psize > 0 else 0)
    page = min(max(page, 1), npages)
    startcount = (page-1)*psize

    # If totalprizepool does not exist, the filters filtered out all players.
    if totalprizepool:
        ranking = ranking[(page-1)*psize:page*psize]
    else:
        base['empty'] = True

    base.update({'ranking': ranking, 'totalprizepool': totalprizepool, 'totalorigprizepool': totalorigprizepool, 'filters':filters,
                  'currencies':currencies, 'countries':countries, 'page': page, 'npages': npages, 'startcount': startcount})
    
    return render_to_response('earnings.html', base)

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
            .select_related('pla__rating').select_related('plb__rating').order_by('-date', '-id')\
            .prefetch_related('message_set')
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
        for r in ['P','T','Z']:
            explosses[1][r] = ngames[1][r] - expwins[1][r]
            if ngames[1][r] > 0:
                exppctg[1][r] = expwins[1][r]/ngames[1][r]*100
                pctg[1][r] = float(nwins[1][r])/ngames[1][r]*100
            diff[1][r] = rating.get_totalrating(r) - prevrat[1][r]

        base.update({'tot_rating': tot_rating, 'ngames': ngames, 'nwins': nwins, 'nlosses': nlosses,\
                     'prevrat': prevrat, 'pctg': pctg,\
                     'exppctg': exppctg, 'diff': diff, 'expwins': expwins, 'explosses': explosses,\
                     'prevdev': prevdev})
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
        high = filter_active_ratings(Rating.objects.extra(select={'rat': 'rating'}))\
                .filter(period__id__gt=24)
        highp = filter_active_ratings(Rating.objects.extra(select={'rat': 'rating+rating_vp'}))\
                .filter(period__id__gt=24)
        hight = filter_active_ratings(Rating.objects.extra(select={'rat': 'rating+rating_vt'}))\
                .filter(period__id__gt=24)
        highz = filter_active_ratings(Rating.objects.extra(select={'rat': 'rating+rating_vz'}))\
                .filter(period__id__gt=24)
        dom = filter_active_ratings(Rating.objects.extra(select={'rat': 'domination'}))\
                .filter(domination__gt=0.0, period__id__gt=24)

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

    nti = lambda x: 0 if x is None else x
    def get_data(qset, rc1, rc2):
        temp = qset.filter(rca=rc1, rcb=rc2).aggregate(Sum('sca'), Sum('scb'))
        ret1, ret2 = nti(temp['sca__sum']), nti(temp['scb__sum'])
        temp = qset.filter(rca=rc2, rcb=rc1).aggregate(Sum('sca'), Sum('scb'))
        ret1 += nti(temp['scb__sum'])
        ret2 += nti(temp['sca__sum'])
        return ret1, ret2

    # Update all months every month
    if not BalanceEntry.objects.filter(date=datetime.date(year=last[0], month=last[1], day=15)).exists():
        while first[0] < last[0] or (first[0] == last[0] and first[1] <= last[1]):
            matches = Match.objects.filter(date__gte='%i-%i-01' % first)
            if first[1] < 12:
                matches = matches.filter(date__lt='%i-%i-01' % (first[0], first[1]+1))
            else:
                matches = matches.filter(date__lt='%i-%i-01' % (first[0]+1, 1))

            pvtw, pvtl = get_data(matches, 'P', 'T')
            pvzw, pvzl = get_data(matches, 'P', 'Z')
            tvzw, tvzl = get_data(matches, 'T', 'Z')
            try:
                be = BalanceEntry.objects.get(date=datetime.date(year=first[0], month=first[1], day=15))
                be.pvt_wins = pvtw
                be.pvt_losses = pvtl
                be.pvz_wins = pvzw
                be.pvz_losses = pvzl
                be.tvz_wins = tvzw
                be.tvz_losses = tvzl
                be.save()
            except:
                new = BalanceEntry(pvt_wins=pvtw, pvt_losses=pvtl, pvz_wins=pvzw, pvz_losses=pvzl,
                                   tvz_wins=tvzw, tvz_losses=tvzl,
                                   date=datetime.date(year=first[0], month=first[1], day=15))
                new.save()

            first = (first[0], first[1]+1)
            if first[1] == 13:
                first = (first[0]+1, 1)

    N = BalanceEntry.objects.count()

    pvt_scores = zeros((2,N))
    pvz_scores = zeros((2,N))
    tvz_scores = zeros((2,N))

    entries = BalanceEntry.objects.all().order_by('date')

    pvt_scores[0,:] = array([e.pvt_wins for e in entries])
    pvt_scores[1,:] = array([e.pvt_losses for e in entries])
    pvz_scores[0,:] = array([e.pvz_wins for e in entries])
    pvz_scores[1,:] = array([e.pvz_losses for e in entries])
    tvz_scores[0,:] = array([e.tvz_wins for e in entries])
    tvz_scores[1,:] = array([e.tvz_losses for e in entries])

    time = [e.date for e in entries]

    base['pvt'] = zip(100*pvt_scores[0,:]/(pvt_scores[0,:] + pvt_scores[1,:]), time)
    base['pvz'] = zip(100*pvz_scores[0,:]/(pvz_scores[0,:] + pvz_scores[1,:]), time)
    base['tvz'] = zip(100*tvz_scores[0,:]/(tvz_scores[0,:] + tvz_scores[1,:]), time)

    base['charts'] = True
    base['patches'] = PATCHES
    return render_to_response('reports_balance.html', base)
