from math import sqrt
from datetime import date

from django.db.models import Sum

import ccy
from countries import data

from aligulac.settings import INACTIVE_THRESHOLD, KR_INIT, INIT_DEV

from ratings.models import Match, Period, Player, Rating

# {{{ Patchlist
PATCHES = [
    (date(year=2010, month=10, day=14), '1.1.2'),
    (date(year=2011, month=3,  day=22), '1.3.0'),
    (date(year=2011, month=9,  day=20), '1.4.0'),
    (date(year=2012, month=2,  day=21), '1.4.3'),
    (date(year=2013, month=3,  day=12), 'HotS'),
    (date(year=2013, month=7,  day=11), '2.0.9 BU'),
]
# }}}

# {{{ start_rating: Gets the initial rating of a player.
def start_rating(country, period):
    if country == 'KR':
        return KR_INIT
    else:
        return 0.0
# }}}

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

# {{{ total_ratings: Annotates a rating queryset by adding tot_vp, tot_vt and tot_vz.
def total_ratings(queryset):
    return queryset.extra(select={
        'tot_vp': 'rating+rating_vp',
        'tot_vt': 'rating+rating_vt',
        'tot_vz': 'rating+rating_vz',
    })
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

# {{{ filter_flags: Splits an integer representing bitwise or into a list of each flag.
def filter_flags(flags):
    power = 1
    ret = []
    while flags > 0:
        if flags % 2 == 1:
            ret.append(power)
            flags -= 1
        flags //= 2
        power *= 2
    return ret
# }}}

# {{{ split_matchset: Splits a match queryset into two, where player is A and B respectively
def split_matchset(queryset, player):
    return queryset.filter(pla=player), queryset.filter(plb=player)
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

# {{{ display_matches: Prepare a match queryset for display. Works for both Match and PreMatch objects.
# Optional arguments:
# - date: True to display dates, false if not.
# - fix_left: Set to a player object if you want that player to be always listed on the left.
# - ratings: True to display ratings, false if not.
# - messages: True to display messages, false if not.
def display_matches(matches, date=True, fix_left=None, ratings=False, messages=True):
    ret = []
    for idx, m in enumerate(matches):
        # {{{ Basic stuff
        r = {
            'match': m,
            'match_id': m.id,
            'game': m.game if isinstance(m, Match) else m.group.game,
            'offline': m.offline if isinstance(m, Match) else m.group.offline,
            'treated': isinstance(m, Match) and m.treated,
            'pla_id': m.pla_id,
            'plb_id': m.plb_id,
            'pla_tag': m.pla.tag if m.pla is not None else m.pla_string,
            'plb_tag': m.plb.tag if m.plb is not None else m.plb_string,
            'pla_race': m.rca,
            'plb_race': m.rcb,
            'pla_country': m.pla.country if m.pla else None,
            'plb_country': m.plb.country if m.plb else None,
            'pla_score': m.sca,
            'plb_score': m.scb,
        }

        if isinstance(m, Match):
            r['eventtext'] = m.eventobj.fullname if m.eventobj is not None else m.event
        # }}}

        # {{{ Add dates and messages if needed
        if date and isinstance(m, Match):
            r['date'] = m.date

        if messages:
            r['messages'] = [aligulac.tools.Message(msg.text, msg.title, msg.type + '-small')\
                             for msg in m.message_set.all()]
        # }}}

        # {{{ Check ratings if needed
        if ratings and isinstance(m, Match):
            r.update({
                'pla_rating': m.rta.get_totalrating(m.rcb) if m.rta
                              else start_rating(r['pla_country'], m.period_id),
                'plb_rating': m.rtb.get_totalrating(m.rca) if m.rtb
                              else start_rating(r['plb_country'], m.period_id),
                'pla_dev':    m.rta.get_totaldev(m.rcb) if m.rta else sqrt(2)*INIT_DEV,
                'plb_dev':    m.rtb.get_totaldev(m.rca) if m.rtb else sqrt(2)*INIT_DEV,
            })
        # }}}

        # {{{ Switch roles of pla and plb if needed
        if fix_left is not None and fix_left.id == r['plb_id']:
            for k in r.keys():
                if k[0:3] == 'pla':
                    l = 'plb' + k[3:]
                    r[k], r[l] = r[l], r[k]
        # }}}

        ret.append(r)

    return ret
# }}}
