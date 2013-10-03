# {{{ Imports
import simplejson

from countries import transformations

from django.http import HttpResponse
from django.shortcuts import get_object_or_404

from ratings.models import (
    Period,
    Rating,
)
from ratings.tools import filter_active
# }}}

# {{{ player_object: Turn a player into a dict
def player_object(p, sparse=False):
    dp = {
        'id': p.id,
        'tag': p.tag,
        'race': p.race
    }

    if p.country is not None:
        dp['country'] = transformations.cc_to_cn(p.country)
        dp['country-iso'] = p.country

    if sparse:
        return dp

    if p.name is not None:
        dp['name'] = p.name

    if p.birthday is not None:
        dp['birthday'] = str(p.birthday)

    dp['aliases'] = [a.name for a in p.alias_set.all()]

    try:
        team = p.groupmembership_set.filter(current=True, group__is_team=True).first().group
        dp['team'] = team_object(team, sparse=True)
    except:
        pass

    return dp
# }}}

# {{{ rating_list: View for rating list API call
def rating_list(request, period=None):
    if period is not None:
        period = get_object_or_404(Period, id=period, computed=True)
    else:
        period = Period.objects.filter(computed=True).latest('start')

    ret = {
        'id': period.id,
        'start': str(period.start),
        'end': str(period.end),
        'retplayers': period.num_retplayers,
        'newplayers': period.num_newplayers,
        'games': period.num_games,
        'list': []
    }

    rats = filter_active(Rating.objects.filter(period=period))
    rats = rats.select_related('player').order_by('-rating')

    number = 1
    for r in rats:
        ret['list'].append({
            'number': number,
            'player': player_object(r.player, sparse=True),
            'rating': r.rating,
            'rating_vp': r.rating_vp,
            'rating_vt': r.rating_vt,
            'rating_vz': r.rating_vz,
            'dev': r.dev,
            'dev_vp': r.dev_vp,
            'dev_vt': r.dev_vt,
            'dev_vz': r.dev_vz,
            'decay': r.decay
        })
        number += 1

    return HttpResponse(simplejson.dumps(ret), mimetype='application/json')
# }}}
