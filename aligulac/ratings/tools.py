from django.db.models import Sum

import ccy
from countries import data

from ratings.models import Period, Player, Rating
from aligulac.settings import INACTIVE_THRESHOLD

# {{{ get_latest_period: Returns the latest computed period, or None.
def get_latest_period():
    try:
        return Period.objects.filter(computed=True).latest('start')
    except:
        return None
# }}}

# {{{ filter_active: Filters a rating queryset by removing inactive ratings.
def filter_active(queryset):
    return queryset.filter(decay__lt=INACTIVE_THRESHOLD)
# }}}

# {{{ filter_inactive: Filters a rating queryset by removing active ratings.
def filter_inactive(queryset):
    return queryset.exclude(decay__lt=INACTIVE_THRESHOLD)
# }}}

# {{{ populate_teams: Adds team information to rows in a queryset (ratings or players) by populating the
# members team (short name), teamfull (full name) and teamid (team ID).
def populate_teams(queryset):
    for e in queryset:
        if isinstance(e, Player):
            player = e
        else:
            player = e.player

        membership = player.get_current_teammembership()
        if membership:
            e.team = membership.group.shortname
            e.teamfull = membership.group.name
            e.teamid = membership.group.id
    return queryset
# }}}

# {{{ country_list: Creates a list of countries in the given queryset (of Players).
def country_list(queryset):
    countries = queryset.values('country').distinct()
    country_codes = {c['country'] for c in countries if c['country'] is not None}
    print(country_codes)
    country_dict = [{'cc': c, 'name': data.ccn_to_cn[data.cca2_to_ccn[c]]} for c in country_codes]
    country_dict.sort(key=lambda a: a['name'])
    return country_dict
# }}}

# {{{ currency_list: Creates a list of currencies in the given queryset (of Earnings).
def currency_list(queryset):
    currencies = queryset.values('currency').distinct().order_by('currency')
    currency_dict = [{'name': ccy.currency(c['currency']).name,
                      'code': ccy.currency(c['currency']).code} for c in currencies]
    return currency_dict
# }}}

# {{{ ntz: Helper function with aggregation, sending None to 0, so that the sum of an empty list is 0.
# AS IT FUCKING SHOULD BE.
ntz = lambda k: k if k is not None else 0
# }}}

# {{{ count_winloss_games: Counts wins and losses over a queryset relative to player A.
def count_winloss_games(queryset):
    agg = queryset.aggregate(Sum('sca'), Sum('scb'))
    return ntz(agg['sca__sum']), ntz(agg['scb__sum'])
# }}}

# {{{ count_matchup_games: Gets the matchup W-L data for a queryset.
def count_matchup_games(queryset, rca, rcb):
    wa, la = count_winloss_games(queryset.filter(rca=rca, rcb=rcb))
    lb, wb = count_winloss_games(queryset.filter(rca=rcb, rcb=rca))
    return wa+wb, la+lb
# }}}

# {{{ count_mirror_games: Gets the number of mirror games for a queryset.
def count_mirror_games(queryset, race):
    w, l = count_winloss_games(queryset.filter(rca=race, rcb=race))
    return w + l
# }}}
