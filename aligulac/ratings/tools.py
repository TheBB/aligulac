# {{{ Imports
from numpy import (
    arctanh,
    tanh,
    pi,
)
from math import sqrt
from datetime import date
from decimal import Decimal
import shlex

from django.db.models import (
    Sum,
    Q
)
from django.db.models.query import QuerySet
from django.utils.translation import ugettext_lazy as _

from pyparsing import *

import ccy
from countries import data
from countries.transformations import (
    cca3_to_ccn,
    ccn_to_cca2,
    cn_to_ccn,
)

import aligulac
from aligulac.settings import (
    INACTIVE_THRESHOLD,
    INIT_DEV,
    start_rating,
)

from ratings.models import (
    Match,
    Period,
    Player,
    Rating,
)
# }}}

# {{{ Patchlist
PATCHES = [
    (date(year=2010, month=10, day=14), '1.1.2'),
    (date(year=2011, month=3,  day=22), '1.3.0'),
    (date(year=2011, month=9,  day=20), '1.4.0'),
    (date(year=2012, month=2,  day=21), '1.4.3'),
    (date(year=2013, month=3,  day=12), 'HotS'),
    (date(year=2013, month=7,  day=11), '2.0.9 BU'),
    (date(year=2013, month=11,  day=11), '2.0.12 BU'),
    (date(year=2014, month=2,  day=3), '2.1 BU'),
    (date(year=2014, month=3,  day=1), '2.1 BU2'),
    (date(year=2014, month=5,  day=23), '2.1.2 BU'),
    (date(year=2014, month=7,  day=25), '2.1.3 BU'),
    (date(year=2015, month=4,  day=9), '2.1.9 BU'),
    (date(year=2015, month=11,  day=10), 'LotV'),
    (date(year=2016, month=1,  day=29), '3.1.1 BU'),
    (date(year=2016, month=5,  day=23), '3.3.0 BU'),
    (date(year=2016, month=7,  day=6), '3.3.2 BU'),
    (date(year=2016, month=11, day=21), '3.8.0'),
    (date(year=2016, month=12, day=8), '3.8.0 BU'),
    (date(year=2017, month=2, day=1), '3.10.1'),
    (date(year=2017, month=3, day=7), '3.11.0 BU'),
    (date(year=2017, month=4, day=19), '3.12.0 BU'),
    (date(year=2017, month=5, day=24), '3.14.0'),
    (date(year=2017, month=11, day=15), '4.0.0'),
    (date(year=2017, month=11, day=21), '4.0.2 BU'),
    (date(year=2017, month=12, day=18), '4.1.1 BU'),
    (date(year=2018, month=1, day=29), '4.1.4 BU'),
    (date(year=2018, month=3, day=19), '4.2.1 BU'),
    (date(year=2018, month=5, day=15), '4.3.0 BU')
]
# }}}

# {{{ Currency names 
CURRENCIES = {
    'EUR': _('Euro'),
    'GBP': _('British Pound'),
    'AUD': _('Australian Dollar'),
    'NZD': _('New-Zealand Dollar'),
    'USD': _('US Dollar'),
    'CAD': _('Canadian Dollar'),
    'CHF': _('Swiss Franc'),
    'NOK': _('Norwegian Krona'),
    'SEK': _('Swedish Krona'),
    'DKK': _('Danish Krona'),
    'JPY': _('Japanese Yen'),
    'CNY': _('Chinese Renminbi'),
    'KRW': _('South Korean won'),
    'SGD': _('Singapore Dollar'),
    'IDR': _('Indonesian Rupiah'),
    'THB': _('Thai Baht'),
    'TWD': _('Taiwan Dollar'),
    'HKD': _('Hong Kong Dollar'),
    'PHP': _('Philippines Peso'),
    'INR': _('Indian Rupee'),
    'MYR': _('Malaysian Ringgit'),
    'VND': _('Vietnamese Dong'),
    'BRL': _('Brazilian Real'),
    'PEN': _('Peruvian Nuevo Sol'),
    'ARS': _('Argentine Peso'),
    'MXN': _('Mexican Peso'),
    'CLP': _('Chilean Peso'),
    'COP': _('Colombian Peso'),
    'JMD': _('Jamaican Dollar'),
    'TTD': _('Trinidad and Tobago Dollar'),
    'BMD': _('Bermudian Dollar'),
    'CZK': _('Czech Koruna'),
    'PLN': _('Polish Zloty'),
    'TRY': _('Turkish Lira'),
    'HUF': _('Hungarian Forint'),
    'RON': _('Romanian Leu'),
    'RUB': _('Russian Ruble'),
    'HRK': _('Croatian kuna'),
    'KZT': _('Kazakhstani Tenge'),
    'ILS': _('Israeli Shekel'),
    'AED': _('United Arab Emirates Dirham'),
    'QAR': _('Qatari Riyal'),
    'SAR': _('Saudi Riyal'),
    'EGP': _('Egyptian Pound'),
    'ZAR': _('South African Rand'),
    'XBT': _('Bitcoin'),
}
# }}}

# {{{ find_player: Magic!
def find_player(query=None, lst=None, make=False, soft=False, strict=False):
    queryset = Player.objects.all()

    if not lst:
        try:
            lst = [s.strip() for s in shlex.split(query) if s.strip() != '']
        except:
            return []

    tag, country, race = None, None, None

    # {{{ Build filter
    for s in lst:
        # If numeric, assume a restriction on ID
        if type(s) is int or s.isdigit():
            queryset = queryset.filter(id=int(s))
            continue

        # If only one character, assume a restriction on race
        if len(s) == 1 and s.upper() in 'PTZSR':
            race = s.upper()
            queryset = queryset.filter(race=s.upper())
            continue

        # Otherwise, always search by player tag, team and aliases
        filter_type = "iexact"
        if soft:
            filter_type = "icontains"

        # Helper function that formats the filter to use `filter_type`
        def format_filter(**kwargs):
            ret = dict()
            for k in kwargs:
                if k.endswith("MATCHES"):
                    ret[k.replace("MATCHES", filter_type)] = kwargs[k]
                else:
                    ret[k] = kwargs[k]
            return ret

        tag_filter = format_filter(tag__MATCHES=s)
        alias_filter = format_filter(alias__name__MATCHES=s)
        full_name_filter = format_filter(name__MATCHES=s)
        romanized_name_filter = format_filter(romanized_name__MATCHES=s)

        q = (
            Q(**tag_filter) |
            Q(**alias_filter) |
            Q(**full_name_filter) |
            Q(**romanized_name_filter)
        )
        if not strict or len(lst) > 1:
            group_name_filter = format_filter(
                groupmembership__current=True,
                groupmembership__group__name__MATCHES=s,
                groupmembership__group__is_team=True)

            group_alias_filter = format_filter(
                groupmembership__current=True,
                groupmembership__group__alias__name__MATCHES=s,
                groupmembership__group__is_team=True)

            q |= Q(**group_name_filter) | Q(**group_alias_filter)

            # ...and perhaps country codes
            found_country = False
            if len(s) == 2 and s.upper() in data.cca2_to_ccn:
                country = s.upper()
                found_country = True
                q |= Q(country=s.upper())

            if len(s) == 3 and s.upper() in data.cca3_to_ccn:
                country = ccn_to_cca2(cca3_to_ccn(s.upper()))
                found_country = True
                q |= Q(country=ccn_to_cca2(cca3_to_ccn(s.upper())))

            renorm = s[0].upper() + s[1:].lower()
            if renorm in data.cn_to_ccn:
                country = ccn_to_cca2(cn_to_ccn(renorm))
                found_country = True
                q |= Q(country=ccn_to_cca2(cn_to_ccn(renorm)))

            if not found_country:
                tag = s

        queryset = queryset.filter(q)
    # }}}

    # {{{ If no results, make player if allowed
    if not queryset.exists() and make:
        # {{{ Raise exceptions if missing crucial data
        if tag == None:
            msg = _("Player '%s' was not found and cound not be made (missing player tag)") % ' '.join(lst)
            raise Exception(msg)

        if race == None:
            msg = _("Player '%s' was not found and cound not be made (missing race)") % ' '.join(lst)
            raise Exception(msg)
        # }}}

        p = Player(tag=tag, country=country, race=race)
        p.save()

        return Player.objects.filter(id=p.id)
    # }}}

    return queryset.distinct()
# }}}

# Submit match parser
# Format is:
#   player-player score-score flags
# or:
#   archon-archon score-score flags
#   where archon = player / player
#
# Examples:
#  'flash 55-2 life 1-2 !MAKE' =>
#    {'flags': {'MAKE'},
#     'pla': ['flash', 55],
#     'plb': [2, 'life'],
#     'sca': 1,
#     'scb': 2}
#
#  'hello  /  hi    -    1  /  " /!/!/-/ "     3-1 !MAKE !DUP !DUP'  =>
#    {'archona': {'pla': ['hello'], 'plb': ['hi']},
#     'archonb': {'pla': [1], 'plb': [' /!/!/-/ ']},
#     'flags': {'DUP', 'MAKE'},
#     'sca': 3,
#     'scb': 1}

def parse_match(line, allow_archon=False):
    quote = Literal('"').suppress()
    slash = Literal('/').suppress()
    dash  = Literal('-').suppress()
    excl  = Literal('!').suppress()

    quotedWord = QuotedString('"', escChar='\\', unquoteResults=True)
    string = CharsNotIn('-/"\' ')
    integer = Word(nums).addParseAction(lambda t: int(t[0]))

    sca = integer("sca")
    scb = integer("scb")
    score = sca + dash + scb

    flag = Combine(excl + (
        Literal("MAKE") |
        Literal("DUP")
    ))
    flags = ZeroOrMore(flag)("flags")

    entry = integer | string | quotedWord
    player = entry + ZeroOrMore(
        ~(score + flags + stringEnd) +
        ~dash +
        ~slash +
        White().suppress() +
        entry
    )

    pla = player("pla")
    plb = player("plb")
    archon = pla + slash + plb

    players = pla + dash + plb

    if allow_archon:
        archona = archon("archona")
        archonb = archon("archonb")

        players = archona + dash + archonb | players

    match = players + score + flags

    result = match.parseString(line)

    result_dict = dict(result)

    ## Clean-up
    if 'archona' in result_dict:
        clean = lambda key: dict(
            map(lambda x: (x[0], list(x[1])), dict(result_dict[key]).items())
        )
        result_dict['archona'] = clean('archona')
        result_dict['archonb'] = clean('archonb')
        del result_dict['pla']
        del result_dict['plb']
    else:
        result_dict['pla'] = list(result_dict['pla'])
        result_dict['plb'] = list(result_dict['plb'])

    if 'flags' in result_dict:
         result_dict['flags'] = set(list(result_dict['flags']))
    else:
         result_dict['flags'] = set()

    return result_dict

# {{{ cdf: Cumulative distribution function
def cdf(x, loc=0.0, scale=1.0):
    return 0.5 + 0.5 * tanh(pi/2/sqrt(3) * (x-loc)/scale)
# }}}

# {{{ pdf: Probability distribution function
def pdf(x, loc=0.0, scale=1.0):
    return pi/4/sqrt(3)/scale * (1 - tanh(pi/2/sqrt(3)*(x-loc)/scale)**2)
# }}}

# {{{ icdf: Inverse cumulative distribution function
def icdf(c, loc=0.0, scale=1.0):
    return loc + scale * 2*sqrt(3)/pi * arctanh(2*c - 1)
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

def filter_active_players(queryset):
    return queryset.filter(current_rating__decay__lt=INACTIVE_THRESHOLD)
# }}}

# {{{ filter_inactive: Filters a rating queryset by removing active ratings.
def filter_inactive(queryset):
    return queryset.exclude(decay__lt=INACTIVE_THRESHOLD)

def filter_inactive_players(queryset):
    return queryset.exclude(current_rating__decay__lt=INACTIVE_THRESHOLD)
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
def populate_teams(queryset, player_set=False):
    if player_set:
        q = queryset.prefetch_related(
            'groupmembership_set',
            'groupmembership_set__group'
        )
    else:
        q = queryset.prefetch_related(
            'player__groupmembership_set',
            'player__groupmembership_set__group'
        )
    for e in q:
        if isinstance(e, Player):
            player = e
        else:
            player = e.player

        membership = player.get_current_teammembership()
        if membership:
            e.team = membership.group.shortname
            e.teamfull = membership.group.name
            e.teamid = membership.group.id

    return q
# }}}

# {{{ country_list: Creates a list of countries in the given queryset (of Players).
def country_list(queryset):
    countries = queryset.values('country').distinct()
    country_codes = {c['country'] for c in countries if c['country'] is not None}
    country_dict = [{'cc': c, 'name': _(data.ccn_to_cn[data.cca2_to_ccn[c]])} for c in country_codes]
    country_dict.sort(key=lambda a: a['name'])
    return country_dict
# }}}

# {{{ currency_list: Creates a list of currencies in the given queryset (of Earnings).
def currency_list(queryset):
    currencies = queryset.values('currency').distinct().order_by('currency')
    currency_dict = [
        {'name': CURRENCIES[ccy.currency(c['currency']).code], 'code': ccy.currency(c['currency']).code} 
        for c in currencies
    ]
    return currency_dict
# }}}


# {{{
def currency_strip(value):
    """
    Pretty prints the value using as few characters as possible
    """
    if isinstance(value, str):
        return value.rstrip('0').rstrip('.')
        
    if isinstance(value, Decimal):
        return currency_strip(str(value))

    if isinstance(value, int):
        return str(value)
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

# {{{ get_placements: Returns a dict mapping prizemoney to tuple (min,max) placements for a given event.
def get_placements(event):
    ret = {}
    for earning in event.earnings_set.exclude(placement=0).order_by('placement'):
        try:
            ret[earning.earnings] = (
                min(min(ret[earning.earnings]), earning.placement),
                max(max(ret[earning.earnings]), earning.placement),
            )
        except:
            ret[earning.earnings] = (earning.placement, earning.placement)
    return ret
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

# {{{ count_winloss_player(queryset, player): Counts wins and losses over a queryset for a given player.
def count_winloss_player(queryset, player):
    wa, la = count_winloss_games(queryset.filter(pla=player))
    lb, wb = count_winloss_games(queryset.filter(plb=player))
    return wa+wb, la+lb
# }}}

# {{{ count_matchup_games: Gets the matchup W-L data for a queryset.
def count_matchup_games(queryset, rca, rcb):
    wa, la = count_winloss_games(queryset.filter(rca=rca, rcb=rcb))
    lb, wb = count_winloss_games(queryset.filter(rca=rcb, rcb=rca))
    return wa+wb, la+lb
# }}}

# {{{ count_matchup_player: Gets the matcup W-L data for a queryset for a given player.
def count_matchup_player(queryset, player, race):
    wa, la = count_winloss_games(queryset.filter(pla=player, rcb=race))
    lb, wb = count_winloss_games(queryset.filter(plb=player, rca=race))
    return wa+wb, la+lb
# }}}

# {{{ count_mirror_games: Gets the number of mirror games for a queryset.
def count_mirror_games(queryset, race):
    w, l = count_winloss_games(queryset.filter(rca=race, rcb=race))
    return w + l
# }}}

# {{{ add_counts: Add match and game counts to a rating queryset (should have prefetched prev__rt(a,b)).
# Will probably result in two queries being run.
def add_counts(queryset):
    for r in queryset:
        if r.prev is not None:
            r.ngames, r.nmatches = 0, 0
            for s in [r.prev.rta.all(), r.prev.rtb.all()]:
                for m in s:
                    r.ngames += m.sca + m.scb
                    r.nmatches += 1
        else:
            initial = (
                r.player.get_matchset().filter(period=r.period).aggregate(Sum('sca'), Sum('scb'))
            )
            r.ngames = ntz(initial['sca__sum']) + ntz(initial['scb__sum'])
            r.nmatches = r.player.get_matchset().filter(period_id=r.period_id).count()
    return queryset
# }}}

# {{{ display_matches: Prepare a match queryset for display. Works for both Match and PreMatch objects.
# Optional arguments:
# - date: True to display dates, false if not.
# - fix_left: Set to a player object if you want that player to be always listed on the left.
# - ratings: True to display ratings, false if not.
# - messages: True to display messages, false if not.
def display_matches(matches, date=True, fix_left=None, ratings=False, messages=True,
                    eventcount=False, add_links=False, no_events=False):
    if isinstance(matches, QuerySet) and not no_events:
        matches = matches.prefetch_related('eventobj__uplink', 'eventobj__uplink__parent')

    ret = []
    for idx, m in enumerate(matches):
        # {{{ Basic stuff
        r = {
            'match':        m,
            'match_id':     m.id,
            'game':         m.game if isinstance(m, Match) else m.group.game,
            'offline':      m.offline if isinstance(m, Match) else m.group.offline,
            'treated':      isinstance(m, Match) and m.treated,
            'pla': {
                'id': m.pla_id,
                'tag': m.pla.tag if m.pla is not None else m.pla_string,
                'race': m.rca or (m.pla.race if m.pla else None),
                'country': m.pla.country if m.pla else None,
                'score': m.sca,
            },
            'plb': {
                'id': m.plb_id,
                'tag': m.plb.tag if m.plb is not None else m.plb_string,
                'race': m.rcb or (m.plb.race if m.plb else None),
                'country': m.plb.country if m.plb else None,
                'score': m.scb,
            },
        }

        if eventcount and isinstance(m, Match):
            r['eventcount'] = m.eventobj__match__count

        if isinstance(m, Match):
            r['eventtext'] = m.eventobj.fullname if m.eventobj is not None else m.event

        # If event is not closed and add_links=True, show add link
        r['add_links'] = add_links and m.eventobj is not None and not m.eventobj.closed
        # }}}

        # {{{ Add dates and messages if needed
        if date and isinstance(m, Match):
            r['date'] = m.date

        if messages:
            r['messages'] = [
                aligulac.tools.Message(msg=msg, type=msg.type + '-small')
                for msg in m.message_set.all()
            ]
        # }}}

        # {{{ Check ratings if needed
        if ratings and isinstance(m, Match):
            r['pla'].update({
                'rating':  m.rta.get_totalrating(m.rcb) if m.rta
                           else start_rating(r['pla']['country'], m.period_id),
                'dev':     m.rta.get_totaldev(m.rcb) if m.rta else sqrt(2)*INIT_DEV,
            })

            r['plb'].update({
                'rating':  m.rtb.get_totalrating(m.rca) if m.rtb
                           else start_rating(r['plb']['country'], m.period_id),
                'dev':     m.rtb.get_totaldev(m.rca) if m.rtb else sqrt(2)*INIT_DEV,
            })
        # }}}

        # {{{ Switch roles of pla and plb if needed
        if fix_left is not None and fix_left.id == r['plb']['id']:
            r['pla'], r['plb'] = r['plb'], r['pla']
        # }}}

        ret.append(r)

    return ret
# }}}
