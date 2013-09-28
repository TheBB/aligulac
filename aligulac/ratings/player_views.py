# {{{ Imports
from datetime import datetime, date, timedelta
from dateutil.relativedelta import relativedelta
from functools import partial
from math import sqrt

from django import forms
from django.db.models import Sum, Q, Count
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_protect
from django.shortcuts import render_to_response, get_object_or_404

from aligulac.cache import cache_page
from aligulac.tools import (
    Message,
    StrippedCharField,
    base_ctx,
    etn,
    generate_messages,
    get_param,
    get_param_date,
    ntz,
)
from aligulac.settings import INACTIVE_THRESHOLD

from ratings.models import (
    GAMES,
    Match,
    P,
    Period,
    Player,
    RACES,
    Rating,
    T,
    TLPD_DBS,
    Z,
)
from ratings.tools import (
    add_counts,
    cdf,
    count_winloss_player,
    count_matchup_player,
    display_matches,
    filter_flags,
    get_placements,
    PATCHES,
    split_matchset,
    total_ratings,
)

from countries import (
    data,
    transformations,
)
# }}}

msg_inactive = (
    'Due to %s\'s lack of recent games, they have been marked as <em>inactive</em> and '
    'removed from the current rating list. Once they play a rated game they will be reinstated.'
)
msg_nochart  = '%s has no rating chart on account of having played matches in fewer than two periods.'

# {{{ meandate: Rudimentary function for sorting objects with a start and end date.
def meandate(tm):
    if tm.start is not None and tm.end is not None:
        return (tm.start.toordinal() + tm.end.toordinal()) / 2
    elif tm.start is not None:
        return tm.start.toordinal()
    elif tm.end is not None:
        return tm.end.toordinal()
    else:
        return 1000000
# }}}

# {{{ interp_rating: Takes a date and a rating list, and interpolates linearly.
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
# }}}

# {{{ PlayerModForm: Form for modifying a player.
class PlayerModForm(forms.Form):
    tag      = StrippedCharField(max_length=30, required=True, label='Tag')
    race     = forms.ChoiceField(choices=RACES, required=True, label='Race')
    name     = StrippedCharField(max_length=100, required=False, label='Name')
    akas     = forms.CharField(max_length=200, required=False, label='AKAs')
    birthday = forms.DateField(required=False, label='Birthday')

    tlpd_id  = forms.IntegerField(required=False, label='TLPD ID')
    tlpd_db  = forms.MultipleChoiceField(
        required=False, choices=TLPD_DBS, label='TLPD DB', widget=forms.CheckboxSelectMultiple)
    lp_name  = StrippedCharField(max_length=200, required=False, label='Liquipedia title')
    sc2c_id  = forms.IntegerField(required=False, label='SC2Charts.net ID')
    sc2e_id  = forms.IntegerField(required=False, label='SC2Earnings.com ID')

    country = forms.ChoiceField(choices=data.countries, required=False, label='Country')

    # {{{ Constructor
    def __init__(self, request=None, player=None):
        if request is not None:
            super(PlayerModForm, self).__init__(request.POST)
        else:
            super(PlayerModForm, self).__init__(initial={
                'tag':       player.tag,
                'race':      player.race,
                'country':   player.country,
                'name':      player.name,
                'akas':      ', '.join(player.get_aliases()),
                'birthday':  player.birthday,
                'sc2c_id':   player.sc2c_id,
                'sc2e_id':   player.sc2e_id,
                'lp_name':   player.lp_name,
                'tlpd_id':   player.tlpd_id,
                'tlpd_db':   filter_flags(player.tlpd_db if player.tlpd_db else 0),
            })

        self.label_suffix = ''
    # }}}

    # {{{ update_player: Pushes updates to player, responds with messages
    def update_player(self, player):
        ret = []

        if not self.is_valid():
            ret.append(Message('Entered data was invalid, no changes made.', type=Message.ERROR))
            for field, errors in self.errors.items():
                for error in errors:
                    ret.append(Message(error=error, field=self.fields[field].label))
            return ret

        def update(value, attr, setter, label):
            if value != getattr(player, attr):
                getattr(player, setter)(value)
                ret.append(Message('Changed %s.' % label, type=Message.SUCCESS))

        update(self.cleaned_data['tag'],       'tag',       'set_tag',       'tag')
        update(self.cleaned_data['race'],      'race',      'set_race',      'race')
        update(self.cleaned_data['country'],   'country',   'set_country',   'country')
        update(self.cleaned_data['name'],      'name',      'set_name',      'name')
        update(self.cleaned_data['birthday'],  'birthday',  'set_birthday',  'birthday')
        update(self.cleaned_data['tlpd_id'],   'tlpd_id',   'set_tlpd_id',   'TLPD ID')
        update(self.cleaned_data['lp_name'],   'lp_name',   'set_lp_name',   'Liquipedia title')
        update(self.cleaned_data['sc2c_id'],   'sc2c_id',   'set_sc2c_id',   'SC2Charts.net ID')
        update(self.cleaned_data['sc2e_id'],   'sc2e_id',   'set_sc2e_id',   'SC2Earnings.com ID')
        update(sum([int(a) for a in self.cleaned_data['tlpd_db']]), 'tlpd_db', 'set_tlpd_db', 'TLPD DBs')

        if player.set_aliases(self.cleaned_data['akas'].split(',')):
            ret.append(Message('Changed aliases.', type=Message.SUCCESS))

        return ret
    # }}}
# }}} 

# {{{ ResultsFilterForm: Form for filtering results.
class ResultsFilterForm(forms.Form):
    after  = forms.DateField(required=False, label='After')
    before = forms.DateField(required=False, label='Before')
    race   = forms.ChoiceField(
        choices=[
            ('ptzr',  'All'),
            ('p',     'Protoss'),
            ('t',     'Terran'),
            ('z',     'Zerg'),
            ('tzr',   'No Protoss'),
            ('pzr',   'No Terran'),
            ('ptr',   'No Zerg'),
        ],
        required=False, label='Opponent race', initial='ptzr'
    )
    country = forms.ChoiceField(
        choices=[('all','All'),('foreigners','Non-Koreans')]+data.countries,
        required=False, label='Country', initial='all'
    )
    bestof = forms.ChoiceField(
        choices=[
            ('all',  'All'),
            ('3',    'Best of 3+'),
            ('5',    'Best of 5+'),
        ],
        required=False, label='Match format', initial='all'
    )
    offline = forms.ChoiceField(
        choices=[
            ('both',     'Both'),
            ('offline',  'Offline'),
            ('online',   'Online'),
        ],
        required=False, label='On/offline', initial='both',
    )
    game = forms.ChoiceField(
        choices=[('all','All')]+GAMES, required=False, label='Game version', initial='all')

    # {{{ Constructor
    def __init__(self, *args, **kwargs):
        super(ResultsFilterForm, self).__init__(*args, **kwargs)

        self.label_suffix = ''
    # }}}

    # {{{ Cleaning with default values
    def clean_default(self, field):
        if not self[field].html_name in self.data:
            return self.fields[field].initial
        return self.cleaned_data[field]

    clean_race    = lambda s: s.clean_default('race')
    clean_country = lambda s: s.clean_default('country')
    clean_bestof  = lambda s: s.clean_default('bestof')
    clean_offline = lambda s: s.clean_default('offline')
    clean_game    = lambda s: s.clean_default('game')
    # }}}
# }}}

# {{{ player view
@cache_page
@csrf_protect
def player(request, player_id):
    # {{{ Get player object and base context, generate messages and make changes if needed
    player = get_object_or_404(Player, id=player_id)
    base = base_ctx('Ranking', '%s:' % player.tag, request, context=player)

    if request.method == 'POST' and base['adm']:
        form = PlayerModForm(request)
        base['messages'] += form.update_player(player)
    else:
        form = PlayerModForm(player=player)

    base['messages'] += generate_messages(player)
    # }}}

    # {{{ Various easy data
    matches = player.get_matchset()
    recent = matches.filter(date__gte=(date.today() - relativedelta(months=2)))

    base.update({
        'player':           player,
        'form':             form,
        'first':            matches.earliest('date'),
        'last':             matches.latest('date'),
        'totalmatches':     matches.count(),
        'offlinematches':   matches.filter(offline=True).count(),
        'aliases':          player.alias_set.all(),
        'earnings':         ntz(player.earnings_set.aggregate(Sum('earnings'))['earnings__sum']),
        'team':             player.get_current_team(),
        'total':            count_winloss_player(matches, player),
        'vp':               count_matchup_player(matches, player, P),
        'vt':               count_matchup_player(matches, player, T),
        'vz':               count_matchup_player(matches, player, Z),
        'totalf':           count_winloss_player(recent, player),
        'vpf':              count_matchup_player(recent, player, P),
        'vtf':              count_matchup_player(recent, player, T),
        'vzf':              count_matchup_player(recent, player, Z),
    })

    if player.country is not None:
        base['countryfull'] = transformations.cc_to_cn(player.country)
    # }}}

    # {{{ Recent matches
    matches = player.get_matchset(related=['rta','rtb','pla','plb','eventobj'])[0:10]
    if matches.exists():
        base['matches'] = display_matches(matches, fix_left=player, ratings=True)
    # }}}

    # {{{ Team memberships
    team_memberships = list(player.groupmembership_set.filter(group__is_team=True).select_related('group'))
    team_memberships.sort(key=lambda t: t.id, reverse=True)
    team_memberships.sort(key=meandate, reverse=True)
    team_memberships.sort(key=lambda t: t.current, reverse=True)
    base['teammems'] = team_memberships
    # }}}

    # {{{ If the player has at least one rating
    ratings = total_ratings(player.rating_set.filter(period__computed=True)).select_related('period')
    if ratings.exists():
        rating = player.get_current_rating()
        base.update({
            'highs': (
                ratings.latest('rating'),
                ratings.latest('tot_vp'),
                ratings.latest('tot_vt'),
                ratings.latest('tot_vz'),
            ),
            'recentchange':  player.get_latest_rating_update(),
            'firstrating':   ratings.earliest('period'),
            'rating':        rating,
        })

        if rating.decay >= INACTIVE_THRESHOLD:
            base['messages'].append(Message(msg_inactive % player.tag, 'Inactive', type=Message.INFO))

        base['charts'] = base['recentchange'].period_id > base['firstrating'].period_id
    else:
        base['messages'].append(Message('%s has no rating yet.' % player.tag, type=Message.INFO))
        base['charts'] = False
    # }}}

    # {{{ If the player has enough games to make a chart
    if base['charts']:
        ratings = (
            total_ratings(player.rating_set.filter(period_id__lte=base['recentchange'].period_id))
                .select_related('period__end')
                .prefetch_related('prev__rta', 'prev__rtb')
                .order_by('period')
        )

        # {{{ Add stories and other extra information
        earliest = base['firstrating']
        latest = base['recentchange']

        # Look through team changes
        teampoints = []
        for mem in base['teammems']:
            if mem.start and earliest.period.end < mem.start < latest.period.end:
                teampoints.append({
                    'date':    mem.start,
                    'rating':  interp_rating(mem.start, ratings),
                    'data':    [{'date': mem.start, 'team': mem.group, 'jol': 'joins'}],
                })
            if mem.end and earliest.period.end < mem.end < latest.period.end:
                teampoints.append({
                    'date':    mem.end,
                    'rating':  interp_rating(mem.end, ratings),
                    'data':    [{'date': mem.end, 'team': mem.group, 'jol': 'leaves'}],
                })
        teampoints.sort(key=lambda p: p['date'])

        # Condense if team changes happened within 14 days
        cur = 0
        while cur < len(teampoints) - 1:
            if (teampoints[cur+1]['date'] - teampoints[cur]['date']).days <= 14:
                teampoints[cur]['data'].append(teampoints[cur+1]['data'][0])
                del teampoints[cur+1]
            else:
                cur += 1

        # Sort first by date, then by joined/left
        for point in teampoints:
            point['data'].sort(key=lambda a: a['jol'], reverse=True)
            point['data'].sort(key=lambda a: a['date'])

        # Look through stories
        stories = player.story_set.all().select_related('event__fullname')
        for s in stories:
            if earliest.period.start < s.date < latest.period.start:
                s.rating = interp_rating(s.date, ratings)
            else:
                s.skip = True
        # }}}

        base.update({
            'ratings':     add_counts(ratings),
            'patches':     PATCHES,
            'stories':     stories,
            'teampoints':  teampoints,
        })
    else:
        base['messages'].append(Message(msg_nochart % player.tag, type=Message.INFO))
    # }}}

    base.update({"title": player.tag})

    return render_to_response('player.html', base)
# }}}

# {{{ adjustment view
@cache_page
def adjustment(request, player_id, period_id):
    # {{{ Get objects
    period = get_object_or_404(Period, id=period_id, computed=True)
    player = get_object_or_404(Player, id=player_id)
    rating = get_object_or_404(Rating, player=player, period=period)
    base = base_ctx('Ranking', 'Adjustments', request, context=player)

    base.update({
        'period':    period,
        'player':    player,
        'rating':    rating,
        'prevlink':  etn(lambda: player.rating_set.filter(period__lt=period, decay=0).latest('period')),
        'nextlink':  etn(lambda: player.rating_set.filter(period__gt=period, decay=0).earliest('period')),
    })
    # }}}

    # {{{ Matches
    matches = player.get_matchset(related=['rta','rtb','pla','plb','eventobj']).filter(period=period)

    base.update({"title": "{} (list {})".format(player.tag, period.id)})

    # If there are no matches, we don't need to continue
    if not matches.exists():
        return render_to_response('ratingdetails.html', base)

    base.update({
        'matches': display_matches(matches, fix_left=player, ratings=True),
        'has_treated': False,
        'has_nontreated': False,
    })
    # }}}

    # {{{ Perform calculations
    tot_rating = {'M': 0.0, 'P': 0.0, 'T': 0.0, 'Z': 0.0}
    ngames     = {'M': 0.0, 'P': 0.0, 'T': 0.0, 'Z': 0.0}
    expwins    = {'M': 0.0, 'P': 0.0, 'T': 0.0, 'Z': 0.0}
    nwins      = {'M': 0.0, 'P': 0.0, 'T': 0.0, 'Z': 0.0}

    for m in base['matches']:
        if not m['match'].treated:
            base['has_nontreated'] = True
            continue
        base['has_treated'] = True

        total_score = m['pla_score'] + m['plb_score']

        scale = sqrt(1 + m['pla_dev']**2 + m['plb_dev']**2)
        expected = total_score * cdf(m['pla_rating'] - m['plb_rating'], scale=scale)

        ngames['M']     += total_score
        tot_rating['M'] += m['plb_rating'] * total_score
        expwins['M']    += expected
        nwins['M']      += m['pla_score']

        vs_races = [m['plb_race']] if m['plb_race'] in 'PTZ' else 'PTZ'
        weight = 1/len(vs_races)
        for r in vs_races:
            ngames[r]     += weight * total_score
            tot_rating[r] += weight * m['plb_rating'] * total_score
            expwins[r]    += weight * expected
            nwins[r]      += weight * m['pla_score']

    for r in 'MPTZ':
        if ngames[r] > 0:
            tot_rating[r] /= ngames[r]

    base.update({
        'ngames':      ngames,
        'tot_rating':  tot_rating,
        'expwins':     expwins,
        'nwins':       nwins,
    })
    # }}}

    return render_to_response('ratingdetails.html', base)
# }}}

# {{{ results view
@cache_page
def results(request, player_id):
    # {{{ Get objects
    player = get_object_or_404(Player, id=player_id)
    base = base_ctx('Ranking', 'Match history', request, context=player)

    base['player'] = player
    # }}}

    # {{{ Filtering
    matches = player.get_matchset(related=['pla','plb','eventobj'])

    form = ResultsFilterForm(request.GET)
    base['form'] = form

    form.is_valid()

    q = Q()
    for r in form.cleaned_data['race'].upper():
        q |= Q(pla=player, rcb=r) | Q(plb=player, rca=r)
    matches = matches.filter(q)

    if form.cleaned_data['country'] == 'foreigners':
        matches = matches.exclude(Q(pla=player, plb__country='KR') | Q(plb=player, pla__country='KR'))
    elif form.cleaned_data['country'] != 'all':
        matches = matches.filter(
              Q(pla=player, plb__country=form.cleaned_data['country'])
            | Q(plb=player, pla__country=form.cleaned_data['country'])
        )

    if form.cleaned_data['bestof'] != 'all':
        sc = int(form.cleaned_data['bestof'])//2 + 1
        matches = matches.filter(Q(sca__gte=sc) | Q(scb__gte=sc))

    if form.cleaned_data['offline'] != 'both':
        matches = matches.filter(offline=(form.cleaned_data['offline']=='offline'))

    if form.cleaned_data['game'] != 'all':
        matches = matches.filter(game=form.cleaned_data['game'])

    if form.cleaned_data['after'] is not None:
        matches = matches.filter(date__gte=form.cleaned_data['after'])

    if form.cleaned_data['before'] is not None:
        matches = matches.filter(date__lte=form.cleaned_data['before'])
    # }}}

    # {{{ Statistics
    base['matches'] = display_matches(matches, fix_left=player)
    base.update({
        'sc_my':  sum([m['pla_score'] for m in base['matches']]),
        'sc_op':  sum([m['plb_score'] for m in base['matches']]),
        'msc_my': sum([1 if m['pla_score'] > m['plb_score'] else 0 for m in base['matches']]),
        'msc_op': sum([1 if m['plb_score'] > m['pla_score'] else 0 for m in base['matches']]),
    })
    # }}}

    base.update({"title": "{} match history".format(player.tag)})
    
    return render_to_response('player_results.html', base)
# }}}

# {{{ historical view
@cache_page
def historical(request, player_id):
    player = get_object_or_404(Player, id=player_id)
    base = base_ctx('Ranking', 'Rating history', request, context=player)

    latest = player.rating_set.filter(period__computed=True, decay=0).latest('period')
    historical = (
        player.rating_set.filter(period_id__lte=latest.period_id)
            .prefetch_related('prev__rta', 'prev__rtb')
            .select_related('period', 'prev')
            .order_by('-period')
    )

    historical = add_counts(historical)

    base.update({
        'player': player,
        'historical': historical,
    })

    base.update({"title": "{}: Rating history".format(player.tag)})
    return render_to_response('historical.html', base)
# }}}

# {{{ earnings view
@cache_page
def earnings(request, player_id):
    player = get_object_or_404(Player, id=player_id)
    base = base_ctx('Ranking', 'Earnings', request, context=player)

    # {{{ Gather data
    earnings = player.earnings_set.prefetch_related('event__earnings_set').order_by('-event__latest')
    totalearnings = earnings.aggregate(Sum('earnings'))['earnings__sum']

    # Get placement range for each prize
    for e in earnings:
        placements = get_placements(e.event)
        for prize, rng in placements.items():
            if rng[0] <= e.placement <= rng[1]:
                e.rng = rng
    # }}}

    # {{{ Sum up earnings by currency
    currencies = {e.currency for e in earnings}
    by_currency = {cur: sum([e.origearnings for e in earnings if e.currency == cur]) for cur in currencies}
    if len(by_currency) == 1 and 'USD' in by_currency:
        by_currency = None
    # }}}

    base.update({
        'player': player,
        'earnings': earnings,
        'totalearnings': totalearnings,
        'by_currency': by_currency,
    })

    base.update({"title": "{} earnings".format(player.tag)})

    return render_to_response('player_earnings.html', base)
# }}}
