# {{{ Imports
from django.db.models import (
    Q,
    Max,
    Count,
)
from django.http import HttpResponse
from django.shortcuts import render_to_response

from aligulac.tools import (
    base_ctx,
    get_param,
    get_param_choice,
)

from ratings.models import (
    Player,
    Rating,
)
from ratings.tools import (
    PATCHES,
    filter_active,
    country_list,
    total_ratings,
)

from countries import data
# }}}

# {{{ history view
def history(request):
    base = base_ctx('Records', 'History', request)

    # {{{ Filtering (appears faster with custom SQL)
    nplayers = int(get_param(request, 'nplayers', '5'))
    race = get_param_choice(request, 'race', ['ptzrs','p','t','z','ptrs','tzrs','pzrs'], 'ptzrs')
    nats = get_param_choice(request, 'nats', ['all','foreigners'] + list(data.ccn_to_cca2.values()), 'all')

    query = '''SELECT player.id, player.tag, player.race, player.country, MAX(rating.rating) AS high
               FROM player JOIN rating ON player.id=rating.player_id'''
    if race != 'ptzrs' or nats != 'all':
        query += ' WHERE '
        ands = []
        if race != 'ptzrs':
            ands.append('(' + ' OR '.join(["player.race='%s'" % r.upper() for r in race]) + ')')
        if nats == 'foreigners':
            ands.append("(player.country!='KR')")
        elif nats != 'all':
            ands.append("(player.country='%s')" % nats)
        query += ' AND '.join(ands)
    query += ' GROUP BY player.id, player.tag, player.race, player.country ORDER BY high DESC LIMIT %i' % nplayers

    players = Player.objects.raw(query)
    # }}}

    base.update({
        'race': race,
        'nats': nats,
        'nplayers': nplayers,
        'players': [(p, p.rating_set.select_related('period')) for p in players],
        'countries': country_list(Player.objects.all()),
        'charts': True,
        'patches': PATCHES,
    })

    return render_to_response('history.html', base)
# }}}

# {{{ hof view
def hof(request):
    base = base_ctx('Records', 'HoF', request)
    base['high'] = (
        Player.objects.filter(
            dom_val__isnull=False, dom_start__isnull=False, dom_end__isnull=False, dom_val__gt=0
        ).order_by('-dom_val')
    )
    return render_to_response('hof.html', base)
# }}}

# {{{ race view
def race(request):
    race = get_param(request, 'race', 'all')
    if race not in 'PTZ':
        race = 'all'
    sub = ['All','Protoss','Terran','Zerg'][['all','P','T','Z'].index(race)]

    base = base_ctx('Records', sub, request)

    def sift(lst, num=5):
        ret, pls = [], set()
        for r in lst:
            if not r.player_id in pls:
                pls.add(r.player_id)
                ret.append(r)
            if len(ret) == num:
                return ret
        return ret

    high = (
        filter_active(total_ratings(Rating.objects.all()))
            .filter(period__id__gt=16).select_related('player', 'period')
    )
    if race != 'all':
        high = high.filter(player__race=race)

    base.update({
        'hightot': sift(high.order_by('-rating')[:200]),
        'highp':   sift(high.order_by('-tot_vp')[:200]),
        'hight':   sift(high.order_by('-tot_vt')[:200]),
        'highz':   sift(high.order_by('-tot_vz')[:200]),
        'race':    race if race != 'all' else '',
    })

    return render_to_response('records.html', base)
# }}}
