# {{{ Imports
from django.shortcuts import (
    get_object_or_404,
    render_to_response,
)
from django.db.models import (
    F,
    Q,
    Sum,
)
from django.template.defaultfilters import (
    date as django_date_filter
)
from django.utils.translation import ugettext_lazy as _

from ratings.models import (
    Earnings,
    P,
    Period,
    Player,
    Rating,
    T,
    Z,
)
from ratings.tools import (
    count_matchup_games,
    count_mirror_games,
    country_list,
    currency_list,
    filter_active,
    populate_teams,
    total_ratings,
)
from ratings.templatetags.ratings_extras import cdate
from aligulac.cache import cache_page
from aligulac.tools import (
    Message,
    base_ctx,
    get_param,
)
from aligulac.settings import INACTIVE_THRESHOLD, SHOW_PER_LIST_PAGE
# }}}

msg_preview = _('This is a <em>preview</em> of the next rating list. It will not be finalized until %s.')

# {{{ periods view
@cache_page
def periods(request):
    base = base_ctx('Ranking', 'History', request)
    base['periods'] = Period.objects.filter(computed=True).order_by('-id')
    
    base.update({"title": _("Historical overview")})
    return render_to_response('periods.djhtml', base)
# }}}

# {{{ period view
@cache_page
def period(request, period_id=None):
    base = base_ctx('Ranking', 'Current', request)

    # {{{ Get period object
    if not period_id:
        period = base['curp']
    else:
        period = get_object_or_404(Period, id=period_id, computed=True)

    if period.is_preview():
        base['messages'].append(Message(msg_preview % cdate(period.end, _('F jS')), type=Message.INFO))

    base['period'] = period
    if period.id != base['curp'].id:
        base['curpage'] = ''
    # }}}

    # {{{ Best and most specialised players
    qset = total_ratings(filter_active(Rating.objects.filter(period=period))).select_related('player')
    qsetp = qset.filter(player__race=P)
    qsett = qset.filter(player__race=T)
    qsetz = qset.filter(player__race=Z)
    base.update({
        'best':     qset.latest('rating'),
        'bestvp':   qset.latest('tot_vp'),
        'bestvt':   qset.latest('tot_vt'),
        'bestvz':   qset.latest('tot_vz'),
        'bestp':    qsetp.latest('rating'),
        'bestpvp':  qsetp.latest('tot_vp'),
        'bestpvt':  qsetp.latest('tot_vt'),
        'bestpvz':  qsetp.latest('tot_vz'),
        'bestt':    qsett.latest('rating'),
        'besttvp':  qsett.latest('tot_vp'),
        'besttvt':  qsett.latest('tot_vt'),
        'besttvz':  qsett.latest('tot_vz'),
        'bestz':    qsetz.latest('rating'),
        'bestzvp':  qsetz.latest('tot_vp'),
        'bestzvt':  qsetz.latest('tot_vt'),
        'bestzvz':  qsetz.latest('tot_vz'),
        'specvp':   qset.extra(select={'d':   'rating_vp/dev_vp*(rating+1.5)'}).latest('d'),
        'specvt':   qset.extra(select={'d':   'rating_vt/dev_vt*(rating+1.5)'}).latest('d'),
        'specvz':   qset.extra(select={'d':   'rating_vz/dev_vz*(rating+1.5)'}).latest('d'),
        'specpvp':  qsetp.extra(select={'d':  'rating_vp/dev_vp*(rating+1.5)'}).latest('d'),
        'specpvt':  qsetp.extra(select={'d':  'rating_vt/dev_vt*(rating+1.5)'}).latest('d'),
        'specpvz':  qsetp.extra(select={'d':  'rating_vz/dev_vz*(rating+1.5)'}).latest('d'),
        'spectvp':  qsett.extra(select={'d':  'rating_vp/dev_vp*(rating+1.5)'}).latest('d'),
        'spectvt':  qsett.extra(select={'d':  'rating_vt/dev_vt*(rating+1.5)'}).latest('d'),
        'spectvz':  qsett.extra(select={'d':  'rating_vz/dev_vz*(rating+1.5)'}).latest('d'),
        'speczvp':  qsetz.extra(select={'d':  'rating_vp/dev_vp*(rating+1.5)'}).latest('d'),
        'speczvt':  qsetz.extra(select={'d':  'rating_vt/dev_vt*(rating+1.5)'}).latest('d'),
        'speczvz':  qsetz.extra(select={'d':  'rating_vz/dev_vz*(rating+1.5)'}).latest('d'),
    })
    # }}}

    # {{{ Highest gainer and biggest losers

    # TODO: Fix these queries, highly dependent on the way django does things.
    gainers = filter_active(Rating.objects.filter(period=period))\
        .filter(prev__isnull=False)\
        .select_related('prev', 'player')\
        .extra(select={'diff': 'rating.rating - T3.rating'})\
        .order_by('-diff')
    losers = filter_active(Rating.objects.filter(period=period))\
        .filter(prev__isnull=False)\
        .select_related('prev', 'player')\
        .extra(select={'diff': 'rating.rating - T3.rating'})\
        .order_by('diff')

    base.update({
        'updown': zip(gainers[:5], losers[:5])
    })
    # }}}

    # {{{ Matchup statistics
    qset = period.match_set
    base['pvt_wins'], base['pvt_loss'] = count_matchup_games(qset, 'P', 'T')
    base['pvz_wins'], base['pvz_loss'] = count_matchup_games(qset, 'P', 'Z')
    base['tvz_wins'], base['tvz_loss'] = count_matchup_games(qset, 'T', 'Z')
    base.update({
        'pvp_games': count_mirror_games(qset, 'P'),
        'tvt_games': count_mirror_games(qset, 'T'),
        'zvz_games': count_mirror_games(qset, 'Z'),
    })

    base['tot_mirror'] = base['pvp_games'] + base['tvt_games'] + base['zvz_games']
    # }}}

    # {{{ Build country list
    all_players = Player.objects.filter(rating__period_id=period.id, rating__decay__lt=INACTIVE_THRESHOLD)
    base['countries'] = country_list(all_players)
    # }}}

    # {{{ Initial filtering of ratings
    entries = filter_active(period.rating_set).select_related('player')

    # Race filter
    race = get_param(request, 'race', 'ptzrs')
    q = Q()
    for r in race:
        q |= Q(player__race=r.upper())
    entries = entries.filter(q)

    # Country filter
    nats = get_param(request, 'nats', 'all')
    if nats == 'foreigners':
        entries = entries.exclude(player__country='KR')
    elif nats != 'all':
        entries = entries.filter(player__country=nats)

    # Sorting
    sort = get_param(request, 'sort', '')
    if sort not in ['vp', 'vt', 'vz']: 
        entries = entries.order_by('-rating', 'player__tag')
    else:
        entries = entries.extra(select={'d':'rating+rating_'+sort}).order_by('-d', 'player__tag')

    entries = entries.prefetch_related('prev')

    base.update({
        'race': race,
        'nats': nats,
        'sort': sort,
    })
    # }}}

    # {{{ Pages etc.
    pagesize = SHOW_PER_LIST_PAGE
    page = int(get_param(request, 'page', 1))
    nitems = entries.count()
    npages = nitems//pagesize + (1 if nitems % pagesize > 0 else 0)
    page = min(max(page, 1), npages)
    entries = entries[(page-1)*pagesize : page*pagesize] if page > 0 else []

    pn_start, pn_end = page - 2, page + 2
    if pn_start < 1:
        pn_end += 1 - pn_start
        pn_start = 1
    if pn_end > npages:
        pn_start -= pn_end - npages
        pn_end = npages
    if pn_start < 1:
        pn_end = npages

    base.update({
        'page':       page,
        'npages':     npages,
        'startcount': (page-1)*pagesize,
        'entries':    populate_teams(entries),
        'nperiods':   Period.objects.filter(computed=True).count(),
        'pn_range':   range(pn_start, pn_end+1),
    })
    # }}}

    base.update({
        'sortable':   True,
        'localcount': True,
    })
        
    fmt_date = django_date_filter(period.end, "F jS, Y")
    # Translators: List (number): (date)
    base.update({"title": _("List {num}: {date}").format(num=period.id, date=fmt_date)})

    return render_to_response('period.djhtml', base)
# }}}

# {{{ earnings view
@cache_page
def earnings(request):
    base = base_ctx('Ranking', 'Earnings', request)

    # {{{ Build country and currency list
    all_players = Player.objects.filter(earnings__player__isnull=False).distinct()
    base['countries'] = country_list(all_players)
    base['currencies'] = currency_list(Earnings.objects)
    # }}}

    # {{{ Initial filtering of earnings
    preranking = Earnings.objects.filter(earnings__isnull=False)

    # Filtering by year
    year = get_param(request, 'year', 'all')
    if year != 'all':
        preranking = preranking.filter(event__latest__year=int(year))

    # Country filter
    nats = get_param(request, 'country', 'all')
    if nats == 'foreigners':
        preranking = preranking.exclude(player__country='KR')
    elif nats != 'all':
        preranking = preranking.filter(player__country=nats)

    # Currency filter
    curs = get_param(request, 'currency', 'all')
    if curs != 'all':
        preranking = preranking.filter(currency=curs)

    base['filters'] = {'year': year, 'country': nats, 'currency': curs}

    ranking = (
        preranking.values('player')
            .annotate(totalorigearnings=Sum('origearnings'))
            .annotate(totalearnings=Sum('earnings'))
            .order_by('-totalearnings', 'player')
    )
    # }}}

    # {{{ Calculate total earnings
    base.update({
        'totalorigprizepool': preranking.aggregate(Sum('origearnings'))['origearnings__sum'],
        'totalprizepool':     preranking.aggregate(Sum('earnings'))['earnings__sum'],
    })
    # }}}

    # {{{ Pages, etc.
    pagesize = SHOW_PER_LIST_PAGE
    page = int(get_param(request, 'page', 1))
    nitems = ranking.count()
    npages = nitems//pagesize + (1 if nitems % pagesize > 0 else 0)
    page = min(max(page, 1), npages)

    pn_start, pn_end = page - 2, page + 2
    if pn_start < 1:
        pn_end += 1 - pn_start
        pn_start = 1
    if pn_end > npages:
        pn_start -= pn_end - npages
        pn_end = npages
    if pn_start < 1:
        pn_end = npages

    base.update({
        'page':       page,
        'npages':     npages,
        'startcount': (page-1)*pagesize,
        'pn_range':   range(pn_start, pn_end+1)
    })

    if nitems > 0:
        ranking = ranking[(page-1)*pagesize : page*pagesize]
    else:
        base['empty'] = True
    # }}}

    # {{{ Populate with player and team objects
    ids = [p['player'] for p in ranking]
    players = Player.objects.in_bulk(ids)
    for p in ranking:
        p['playerobj'] = players[p['player']]
        p['teamobj'] = p['playerobj'].get_current_team()

    base['ranking'] = ranking
    # }}}

    base.update({"title": _("Earnings ranking")})

    return render_to_response('earnings.djhtml', base)
# }}}
