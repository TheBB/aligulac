from django.shortcuts import render_to_response, get_object_or_404
from django.db.models import Q

from ratings.models import Period, Player, Rating
from ratings.tools import filter_active, count_matchup_games, count_mirror_games, populate_teams

from aligulac.cache import cache_page
from aligulac.tools import Message, base_ctx, get_param
from aligulac.settings import INACTIVE_THRESHOLD

from countries import data

msg_preview = 'This is a <em>preview</em> of the next rating list. It will not be finalized until %s.'

# {{{ periods view
@cache_page
def periods(request):
    base = base_ctx('Ranking', 'History', request)
    base['periods'] = Period.objects.filter(computed=True).order_by('-id')
    return render_to_response('periods.html', base)
# }}}

# {{{ period view
@cache_page
def period(request, period_id):
    base = base_ctx('Ranking', 'Current', request)

    # {{{ Get period object
    period = get_object_or_404(Period, id=period_id, computed=True)
    if period.is_preview():
        base['messages'].append(Message(msg_preview % period.end.strftime('%B %d'), type=Message.INFO))

    base['period'] = period
    if period.id != base['curp'].id:
        base['curpage'] = ''
    # }}}

    # {{{ Best and most specialised players
    qset = filter_active(Rating.objects.filter(period=period))
    base.update({
        'best':   qset.filter(period=period).order_by('-rating')[0],
        'bestvp': qset.extra(select={'d':'rating+rating_vp'}).order_by('-d')[0],
        'bestvt': qset.extra(select={'d':'rating+rating_vt'}).order_by('-d')[0],
        'bestvz': qset.extra(select={'d':'rating+rating_vz'}).order_by('-d')[0],
        'specvp': qset.extra(select={'d':'rating_vp/dev_vp*rating'}).order_by('-d')[0],
        'specvt': qset.extra(select={'d':'rating_vt/dev_vt*rating'}).order_by('-d')[0],
        'specvz': qset.extra(select={'d':'rating_vz/dev_vz*rating'}).order_by('-d')[0],
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
    # }}}

    # {{{ Build country list
    countries = Player.objects\
                      .filter(rating__period_id=period.id, rating__decay__lt=INACTIVE_THRESHOLD)\
                      .values('country')
    country_codes = {c['country'] for c in countries if c is not None}
    country_dict = [{'cc': c, 'name': data.ccn_to_cn[data.cca2_to_ccn[c]]} for c in country_codes]
    country_dict.sort(key=lambda a: a['name'])
    base['countries'] = country_dict
    # }}}

    # {{{ Initial filtering of ratings
    entries = filter_active(period.rating_set)

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
    # }}}

    # {{{ Pages etc.
    pagesize = 40
    page = get_param(request, 'page', 1)
    nitems = entries.count()
    npages = nitems//pagesize + (1 if nitems % pagesize > 0 else 0)
    page = min(max(page, 1), npages)
    entries = entries[(page-1)*pagesize : page*pagesize]

    base.update({
        'page':       page,
        'npages':     npages,
        'startcount': (page-1)*pagesize,
        'entries':    populate_teams(entries),
        'nperiods':   Period.objects.filter(computed=True).count(),
    })
    # }}}

    base.update({
        'sortable':   True,
        'localcount': True,
    })
        
    return render_to_response('period.html', base)
# }}}
