import os, datetime
from pyparsing import nestedExpr

from aligulac.settings import RATINGS_INIT_DEV
from aligulac.views import base_ctx
from ratings.tools import find_player, sort_matches, group_by_events, cdf

from django.shortcuts import render_to_response, get_object_or_404, redirect
from django.http import HttpResponse
from django.db.models import Q, F, Sum, Max
from models import Period, Rating, Player, Match, Team, TeamMembership, Event
from django.contrib.auth import authenticate, login
from django.core.context_processors import csrf

from countries import transformations, data

from numpy import linspace, array
from math import sqrt

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

    entries = Rating.objects.filter(period=period, decay__lt=4, dev__lte=0.2)

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

    try:
        base['team'] = Team.objects.filter(active=True, teammembership__player=player, teammembership__current=True)[0]
    except:
        pass

    try:
        base['first'] = Match.objects.filter(Q(pla=player) | Q(plb=player)).order_by('date')[0]
    except:
        pass

    try:
        base['last'] = Match.objects.filter(Q(pla=player) | Q(plb=player)).order_by('-date')[0]
    except:
        pass

    # Winrates
    matches_a = Match.objects.filter(pla=player)
    matches_b = Match.objects.filter(plb=player)

    def ntz(n):
        return n if n is not None else 0

    try:
        a = matches_a.aggregate(Sum('sca'), Sum('scb'))
        b = matches_b.aggregate(Sum('sca'), Sum('scb'))
        base['total'] = (ntz(a['sca__sum']) + ntz(b['scb__sum']), ntz(a['scb__sum']) + ntz(b['sca__sum']))
    except:
        pass

    try:
        a = matches_a.filter(rcb='P').aggregate(Sum('sca'), Sum('scb'))
        b = matches_b.filter(rca='P').aggregate(Sum('sca'), Sum('scb'))
        base['vp'] = (ntz(a['sca__sum']) + ntz(b['scb__sum']), ntz(a['scb__sum']) + ntz(b['sca__sum']))
    except:
        pass

    try:
        a = matches_a.filter(rcb='T').aggregate(Sum('sca'), Sum('scb'))
        b = matches_b.filter(rca='T').aggregate(Sum('sca'), Sum('scb'))
        base['vt'] = (ntz(a['sca__sum']) + ntz(b['scb__sum']), ntz(a['scb__sum']) + ntz(b['sca__sum']))
    except:
        pass

    try:
        a = matches_a.filter(rcb='Z').aggregate(Sum('sca'), Sum('scb'))
        b = matches_b.filter(rca='Z').aggregate(Sum('sca'), Sum('scb'))
        base['vz'] = (ntz(a['sca__sum']) + ntz(b['scb__sum']), ntz(a['scb__sum']) + ntz(b['sca__sum']))
    except:
        pass

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

    rating = Rating.objects.filter(player=player).order_by('-period')
    if rating.count() < 2:
        base['noimage'] = True

    recentchange = Rating.objects.filter(player=player, decay=0).order_by('-period')
    if recentchange.exists():
        base['recentchange'] = recentchange[0]

    firstrating = Rating.objects.filter(player=player).order_by('period')
    if firstrating.exists():
        base['firstrating'] = firstrating[0]

    if not rating.exists():
        base.update({'player': player, 'countryfull': countryfull})
        return render_to_response('player.html', base)
    rating = rating[0]

    matches = Match.objects.filter(Q(pla=player) | Q(plb=player))\
            .select_related('pla__rating').select_related('plb__rating')\
            .select_related('period')\
            .extra(where=['abs(datediff(date,\'%s\')) < 90' % datetime.datetime.now()])\
            .order_by('-date', '-id')[0:10]

    if matches.exists():
        sort_matches(matches, player, add_ratings=True)
        base.update({'matches': matches})

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

def player_plot(request, player_id):
    os.environ['MPLCONFIGDIR'] = '/home/efonn/.matplotlib/'

    from matplotlib.figure import Figure
    from matplotlib.backends.backend_agg import FigureCanvasAgg
    from matplotlib.dates import MonthLocator, DateFormatter
    from matplotlib.ticker import MultipleLocator, NullLocator
    from pychip import pchip

    if 'big' in request.GET:
        fig = Figure(figsize=(20,4), facecolor='white')
    else:
        fig = Figure(figsize=(10,2), facecolor='white')
    rect = 0.05, 0.11, 0.90, 0.85
    ax = fig.add_axes(rect)
    axt = ax.twinx()

    def update_ax(ax1):
        y1, y2 = ax1.get_ylim()
        axt.set_ylim(y1, y2)

    ax.callbacks.connect('ylim_changed', update_ax)

    player = get_object_or_404(Player, id=player_id)
    lastper = Rating.objects.filter(player=player, decay__lt=4).aggregate(Max('period__id'))['period__id__max']
    ratings = Rating.objects.filter(player=player, period__computed=True, period_id__lte=lastper)

    if 'before' in request.GET:
        try:
            ints = [int(x) for x in request.GET['before'].split('-')]
            td = datetime.date(ints[0], ints[1], ints[2])
            ratings = ratings.filter(period__end__lte=td)
        except:
            pass

    if 'after' in request.GET:
        try:
            ints = [int(x) for x in request.GET['after'].split('-')]
            td = datetime.date(ints[0], ints[1], ints[2])
            ratings = ratings.filter(period__end__gte=td)
        except:
            pass

    ratings = list(ratings.order_by('period__id'))

    if len(ratings) == 0:
        ratings = Rating.objects.filter(player=player, period__computed=True, period_id__lte=lastper)
        ratings = list(ratings.order_by('period__id'))

    if len(ratings) > 0:
        t = [r.period.end.toordinal() for r in ratings]
        rtg = [1000*(1.0+r.bf_rating) for r in ratings]
        rtgp = [1000*(1.0+r.bf_rating+1.96*r.bf_dev) for r in ratings]
        rtgm = [1000*(1.0+r.bf_rating-1.96*r.bf_dev) for r in ratings]
        rvp = [1000*(1.0+r.bf_rating+r.bf_rating_vp) for r in ratings]
        rvt = [1000*(1.0+r.bf_rating+r.bf_rating_vt) for r in ratings]
        rvz = [1000*(1.0+r.bf_rating+r.bf_rating_vz) for r in ratings]

        newt = linspace(t[0], t[-1], 7*len(t))
        rtgnew = pchip(array(t), array(rtg), array(newt))
        rtgnewp = pchip(array(t), array(rtgp), array(newt))
        rtgnewm = pchip(array(t), array(rtgm), array(newt))
        rvpnew = pchip(array(t), array(rvp), array(newt))
        rvtnew = pchip(array(t), array(rvt), array(newt))
        rvznew = pchip(array(t), array(rvz), array(newt))

        t = [datetime.datetime.fromordinal(int(k)) for k in newt]
        ax.plot_date(t[:-1], rvpnew[:-1], 'g--', lw=1)
        ax.plot_date(t[:-1], rvtnew[:-1], 'b--', lw=1)
        ax.plot_date(t[:-1], rvznew[:-1], 'r--', lw=1)
        ax.fill_between(t[:-1], rtgnewm[:-1], rtgnewp[:-1], facecolor='#dddddd', edgecolor='#bbbbbb')
        ax.plot_date(t[:-1], rtgnew[:-1], 'k', lw=1.5)
    
        ax.set_xlim(t[0], t[-2])
        btm = min(rtg+rvp+rvt+rvz)-200
        top = max(rtg+rvp+rvt+rvz)+200
        ax.set_ylim(btm, top)
        ax.xaxis.set_major_formatter(DateFormatter('%b %y'))
        ax.yaxis.set_major_locator(MultipleLocator(100*round((top-btm)/500.)))
        axt.yaxis.set_major_locator(MultipleLocator(100*round((top-btm)/500.)))
        numpts = ratings[-1].period.id - ratings[0].period.id
        K = 16 if 'big' in request.GET else 8
        delta = max(numpts / (K * 2), 1)
        months = range(1,13)[0::delta]
        ax.xaxis.set_major_locator(MonthLocator(months))

        for tl in axt.get_xticklabels():
            tl.set_visible(False)

    response = HttpResponse(content_type='image/png')
    canvas = FigureCanvasAgg(fig)
    canvas.print_png(response)
    return response

def results(request):
    base = base_ctx('Results', 'By Date', request)

    from django.db import connection
    cur = connection.cursor()

    try:
        ints = [int(x) for x in request.GET['d'].split('-')]
        td = datetime.date(ints[0], ints[1], ints[2])
    except:
        td = datetime.date.today()

    cur.execute('''SELECT DISTINCT date, event FROM ratings_match WHERE date=\'%i-%i-%i\' AND eventobj_id IS
                NULL ORDER BY id DESC''' % (td.year, td.month, td.day))
    rows_str = cur.fetchall()

    cur.execute('''SELECT DISTINCT m.date, m.eventobj_id FROM ratings_match AS m, ratings_event AS e WHERE date=\'%i-%i-%i\'
                   AND eventobj_id IS NOT NULL AND e.id=m.eventobj_id ORDER BY e.lft DESC, m.id DESC'''\
                           % (td.year, td.month, td.day))
    rows_obj = cur.fetchall()

    matches = []
    matches += [Match.objects.filter(date=r[0], eventobj_id=r[1]).order_by('-id') for r in rows_obj]
    matches += [Match.objects.filter(date=r[0], event=r[1], eventobj__isnull=True).order_by('-id') for r in rows_str]

    base['matches'] = matches
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
                if request.POST['date'].strip() != '':
                    match.date = request.POST['date']
                if request.POST['type'] != 'nochange':
                    match.offline = (request.POST['type'] == 'offline')
                if request.POST['game'] != 'nochange':
                    match.game = request.POST['game']
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
        matches = matches.order_by('-date')

        if base['count'] > 1000:
            base['errs'].append('Too many results (%i). Please add restrictions.' % base['count'])
            return render_to_response('results_search.html', base)

        if 1 <= len(pls) <= 2:
            base['sort_player'] = pls[0]
            sc_my, sc_op, ta, tb = sort_matches(matches, pls[0], add_ratings=False)
            if len(pls) == 2:
                base.update({'sc_my': sc_my, 'sc_op': sc_op, 'left': pls[0], 'right': pls[1]})

        matches = group_by_events(matches)
        base['matches'] = matches

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

    # Get parent, ancestors and siblings
    base['event'] = event
    base['path'] = Event.objects.filter(lft__lte=event.lft, rgt__gte=event.rgt).order_by('lft')
    base['children'] = Event.objects.filter(parent=event).order_by('lft')
    if event.parent != None:
        siblings = event.parent.event_set.exclude(id=event.id).order_by('lft')
        base['siblings'] = siblings

    # Number of matches (set event to big if too large)
    matches = Match.objects.filter(eventobj__lft__gte=event.lft, eventobj__rgt__lte=event.rgt)
    if matches.count() > 200 and not event.big:
        event.big = True
        event.save()
    
    # Make modifications if neccessary
    if 'op' in request.POST and request.POST['op'] == 'Modify' and base['adm'] == True:
        if request.POST['type'] != 'nochange':
            event.change_type(request.POST['type'])
            if 'siblings' in request.POST.keys() and siblings:
                for sibling in siblings:
                    sibling.change_type(request.POST['type'])

        if request.POST['date'].strip() != '':
            matches.update(date=request.POST['date'])
            base['message'] = 'Modified all matches.'
        if request.POST['offline'] != 'nochange':
            matches.update(offline=(request.POST['offline'] == 'offline'))
            base['message'] = 'Modified all matches.'
        if request.POST['game'] != 'nochange':
            matches.update(game=request.POST['game'])
            base['message'] = 'Modified all matches.'

    # Determine WoL/HotS and Online/Offline and event type
    if matches.values("game").distinct().count() == 1:
        base['game'] = matches[0].game
        if base['game'] == 'WoL':
            base['game'] = 'Wings of Liberty'
        elif base['game'] == 'HotS':
            base['game'] = 'Heart of the Swarm'
        #elif base['game'] = 'LotV':
            #base['game'] = 'Legacy of the Void'
    
    if event.type:
        base['eventtype'] = event.type

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

    # Match list
    subtree = Event.objects.filter(lft__gte=event.lft, rgt__lte=event.rgt)
    if event.closed:
        subtree = subtree.order_by('lft')
    else:
        subtree = subtree.order_by('-lft')
        
    matchesArray = []
    for e in subtree:
        if event.big and len(matchesArray) == 20:
            break
        mset = Match.objects.filter(eventobj=e).order_by('-date', '-id')
        if mset.exists():
            matchesArray.append(mset)
    base['matches'] = matchesArray
    base['subtree'] = subtree

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
    
    matches = matches.order_by('-date', '-eventobj__lft', 'event', '-id')
    matches = matches.select_related('pla__rating').select_related('plb__rating').select_related('period')

    prev_date = None
    prev_event = 'qwerty'
    prev_eventobj = -1

    base['sc_my'], base['sc_op'], base['msc_my'], base['msc_op'] = sort_matches(matches, player, add_ratings=True)

    base['matches'] = matches
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

    tot_rating = [0.0, {'P': 0.0, 'T': 0.0, 'Z': 0.0}]
    ngames = [0, {'P': 0, 'T': 0, 'Z': 0}]
    nwins = [0, {'P': 0, 'T': 0, 'Z': 0}]
    nlosses = [0, {'P': 0, 'T': 0, 'Z': 0}]
    expwins = [0.0, {'P': 0.0, 'T': 0.0, 'Z': 0.0}]

    nontreated = False
    matches = Match.objects.filter(Q(pla=player) | Q(plb=player)).filter(period=period)\
            .select_related('pla__rating').select_related('plb__rating').order_by('-date', '-id')
    if not matches.exists():
        base.update({'period': period, 'player': player, 'prevlink': prevlink, 'nextlink': nextlink})
        return render_to_response('ratingdetails.html', base)

    sort_matches(matches, player, add_ratings=True)

    treated = False
    for m in matches:
        if m.treated:
            treated = True
            tot_rating[0] += m.rt_op * (m.sca + m.scb)
            ngames[0] += m.sca + m.scb
            nwins[0] += m.sc_my
            nlosses[0] += m.sc_op

            scale = 1 + m.dev_op**2 + m.dev_my**2

            races = [m.rc_op] if m.rc_op in ['P','T','Z'] else ['P','T','Z']
            weight = float(1)/len(races)
            for sr in races:
                ew = (m.sca + m.scb) * cdf(prevrat[1][sr] - m.rt_op, scale=sqrt(scale))
                expwins[0] += weight * ew
                expwins[1][sr] += weight * ew

                tot_rating[1][sr] += weight * m.rt_op * (m.sca + m.scb)
                ngames[1][sr] += weight * (m.sca + m.scb)
                nwins[1][sr] += weight * m.sc_my
                nlosses[1][sr] += weight * m.sc_op
        else:
            nontreated = True

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
