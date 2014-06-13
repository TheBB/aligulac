# {{{ Imports
import shlex

from datetime import datetime, date, timedelta
from dateutil.relativedelta import relativedelta
from functools import partial
from itertools import zip_longest
from math import sqrt
from urllib.parse import urlencode

from django import forms
from django.db.models import Sum, Q, Count
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_protect
from django.shortcuts import render_to_response, get_object_or_404
from django.utils.translation import ugettext_lazy as _

from aligulac.cache import cache_page
from aligulac.tools import (
    base_ctx,
    cache_login_protect,
    etn,
    generate_messages,
    get_param,
    get_param_date,
    Message,
    ntz,
    StrippedCharField,
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
    STORIES,
    Story,
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

msg_inactive = _(
    'Due to %s\'s lack of recent games, they have been marked as <em>inactive</em> and '
    'removed from the current rating list. Once they play a rated game they will be reinstated.'
)
msg_nochart  = _('%s has no rating chart on account of having played matches in fewer than two periods.')

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
    tag      = StrippedCharField(max_length=30, required=True, label=_('Tag'))
    race     = forms.ChoiceField(choices=RACES, required=True, label=_('Race'))
    name     = StrippedCharField(max_length=100, required=False, label=_('Name'))
    akas     = forms.CharField(max_length=200, required=False, label=_('AKAs'))
    birthday = forms.DateField(required=False, label=_('Birthday'))

    tlpd_id  = forms.IntegerField(required=False, label=_('TLPD ID'))
    tlpd_db  = forms.MultipleChoiceField(
        required=False, choices=TLPD_DBS, label=_('TLPD DB'), widget=forms.CheckboxSelectMultiple)
    lp_name  = StrippedCharField(max_length=200, required=False, label=_('Liquipedia title'))
    sc2e_id  = forms.IntegerField(required=False, label=_('SC2Earnings.com ID'))

    country = forms.ChoiceField(choices=data.countries, required=False, label=_('Country'))

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
            ret.append(Message(_('Entered data was invalid, no changes made.'), type=Message.ERROR))
            for field, errors in self.errors.items():
                for error in errors:
                    ret.append(Message(error=error, field=self.fields[field].label))
            return ret

        def update(value, attr, setter, label):
            if value != getattr(player, attr):
                getattr(player, setter)(value)
                # Translators: Changed something (a noun).
                ret.append(Message(_('Changed %s.') % label, type=Message.SUCCESS))

        update(self.cleaned_data['tag'],       'tag',       'set_tag',       _('tag'))
        update(self.cleaned_data['race'],      'race',      'set_race',      _('race'))
        update(self.cleaned_data['country'],   'country',   'set_country',   _('country'))
        update(self.cleaned_data['name'],      'name',      'set_name',      _('name'))
        update(self.cleaned_data['birthday'],  'birthday',  'set_birthday',  _('birthday'))
        update(self.cleaned_data['tlpd_id'],   'tlpd_id',   'set_tlpd_id',   _('TLPD ID'))
        update(self.cleaned_data['lp_name'],   'lp_name',   'set_lp_name',   _('Liquipedia title'))
        update(self.cleaned_data['sc2e_id'],   'sc2e_id',   'set_sc2e_id',   _('SC2Earnings.com ID'))
        update(sum([int(a) for a in self.cleaned_data['tlpd_db']]), 'tlpd_db', 'set_tlpd_db', _('TLPD DBs'))

        if player.set_aliases([x for x in self.cleaned_data['akas'].split(',') if x.strip() != '']):
            ret.append(Message(_('Changed aliases.'), type=Message.SUCCESS))

        return ret
    # }}}
# }}} 

# {{{ ResultsFilterForm: Form for filtering results.
class ResultsFilterForm(forms.Form):
    after  = forms.DateField(required=False, label=_('After'))
    before = forms.DateField(required=False, label=_('Before'))
    event = forms.CharField(required=False, label=_('Event'))
    race   = forms.ChoiceField(
        choices=[
            ('ptzr',  _('All')),
            ('p',     _('Protoss')),
            ('t',     _('Terran')),
            ('z',     _('Zerg')),
            ('tzr',   _('No Protoss')),
            ('pzr',   _('No Terran')),
            ('ptr',   _('No Zerg')),
        ],
        required=False, label=_('Opponent race'), initial='ptzr'
    )
    country = forms.ChoiceField(
        choices=[('all',_('All')),('KR',_('South Korea')),('foreigners',_('Non-Koreans')),('','')] + 
                sorted(data.countries, key=lambda a: a[1]),
        required=False, label=_('Country'), initial='all'
    )
    bestof = forms.ChoiceField(
        choices=[
            ('all',  _('All')),
            ('3',    _('Best of 3+')),
            ('5',    _('Best of 5+')),
        ],
        required=False, label=_('Match format'), initial='all'
    )
    offline = forms.ChoiceField(
        choices=[
            ('both',     _('Both')),
            ('offline',  _('Offline')),
            ('online',   _('Online')),
        ],
        required=False, label=_('On/offline'), initial='both',
    )
    game = forms.ChoiceField(
        choices=[('all','All')]+GAMES, required=False, label=_('Game version'), initial='all')

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
@cache_login_protect
def player(request, player_id):
    # {{{ Get player object and base context, generate messages and make changes if needed
    player = get_object_or_404(Player, id=player_id)
    base = base_ctx('Ranking', 'Summary', request, context=player)

    if request.method == 'POST' and 'modplayer' in request.POST and base['adm']:
        modform = PlayerModForm(request)
        base['messages'] += modform.update_player(player)
    else:
        modform = PlayerModForm(player=player)

    base['messages'] += generate_messages(player)
    # }}}

    # {{{ Various easy data
    matches = player.get_matchset()
    recent = matches.filter(date__gte=(date.today() - relativedelta(months=2)))

    base.update({
        'player':           player,
        'modform':          modform,
        'first':            etn(lambda: matches.earliest('date')),
        'last':             etn(lambda: matches.latest('date')),
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

    riv = player.rivals or []
    nem = player.nemesis or []
    vic = player.victim or []
    base['riv_nem_vic'] = zip_longest(riv, nem, vic)

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
    if player.current_rating:
        ratings = total_ratings(player.rating_set.filter(period__computed=True)).select_related('period')
        base.update({
            'highs': (
                ratings.latest('rating'),
                ratings.latest('tot_vp'),
                ratings.latest('tot_vt'),
                ratings.latest('tot_vz'),
            ),
            'recentchange':  player.get_latest_rating_update(),
            'firstrating':   ratings.earliest('period'),
            'rating':        player.current_rating,
        })

        if player.current_rating.decay >= INACTIVE_THRESHOLD:
            base['messages'].append(Message(msg_inactive % player.tag, 'Inactive', type=Message.INFO))

        base['charts'] = base['recentchange'].period_id > base['firstrating'].period_id
    else:
        base['messages'].append(Message(_('%s has no rating yet.') % player.tag, type=Message.INFO))
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
                    'data':    [{'date': mem.start, 'team': mem.group, 'jol': _('joins')}],
                })
            if mem.end and earliest.period.end < mem.end < latest.period.end:
                teampoints.append({
                    'date':    mem.end,
                    'rating':  interp_rating(mem.end, ratings),
                    'data':    [{'date': mem.end, 'team': mem.group, 'jol': _('leaves')}],
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

    return render_to_response('player.djhtml', base)
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

    base.update({"title": player.tag})

    # If there are no matches, we don't need to continue
    if not matches.exists():
        return render_to_response('ratingdetails.djhtml', base)

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

        total_score = m['pla']['score'] + m['plb']['score']

        scale = sqrt(1 + m['pla']['dev']**2 + m['plb']['dev']**2)
        expected = total_score * cdf(m['pla']['rating'] - m['plb']['rating'], scale=scale)

        ngames['M']     += total_score
        tot_rating['M'] += m['plb']['rating'] * total_score
        expwins['M']    += expected
        nwins['M']      += m['pla']['score']

        vs_races = [m['plb']['race']] if m['plb']['race'] in 'PTZ' else 'PTZ'
        weight = 1/len(vs_races)
        for r in vs_races:
            ngames[r]     += weight * total_score
            tot_rating[r] += weight * m['plb']['rating'] * total_score
            expwins[r]    += weight * expected
            nwins[r]      += weight * m['pla']['score']

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

    return render_to_response('ratingdetails.djhtml', base)
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

    if form.cleaned_data['event'] is not None:
        lex = shlex.shlex(form.cleaned_data['event'], posix=True)
        lex.wordchars += "'"
        lex.quotes = '"'

        terms = [s.strip() for s in list(lex) if s.strip() != '']

        matches = matches.filter(
            eventobj__fullname__iregex=(
                r"\s".join(r".*{}.*".format(term) for term in terms)
            )
        )
    # }}}

    # {{{ Statistics
    disp_matches = display_matches(matches, fix_left=player)
    base['matches'] = disp_matches
    base.update({
        'sc_my':  sum(m['pla']['score'] for m in base['matches']),
        'sc_op':  sum(m['plb']['score'] for m in base['matches']),
        'msc_my': sum(1 for m in base['matches'] if m['pla']['score'] > m['plb']['score']),
        'msc_op': sum(1 for m in base['matches'] if m['plb']['score'] > m['pla']['score']),
    })

    recent = matches.filter(date__gte=(date.today() - relativedelta(months=2)))
    base.update({
        'total': count_winloss_player(matches, player),
        'vp': count_matchup_player(matches, player, P),
        'vt': count_matchup_player(matches, player, T),
        'vz': count_matchup_player(matches, player, Z),
        'totalf': count_winloss_player(recent, player),
        'vpf': count_matchup_player(recent, player, P),
        'vtf': count_matchup_player(recent, player, T),
        'vzf': count_matchup_player(recent, player, Z)
    })
    # }}}

    # {{{ TL Postable
    
    has_after = form.cleaned_data['after'] is not None
    has_before = form.cleaned_data['before'] is not None
    
    if not has_after and not has_before:
        match_date = ""
    elif not has_after: # and has_before
        match_date = _(" before {}").format(form.cleaned_data['before'])
    elif not has_before: # and has_after
        match_date = _(" after {}").format(form.cleaned_data['after'])
    else:
        match_date = _(" between {} and {}").format(form.cleaned_data['after'],
                                                    form.cleaned_data['before'])

    match_filter = ""

    def switcher(race):
        if race == "S":
            return "R"
        elif race == "s":
            return "r"
        return race

    def win(match):
        return match['pla']['score'] >= match['plb']['score']

    def format_match(d):
        # TL only recognizes lower case country codes :(
        if d["pla"]["country"] is not None:
            d["pla_country_formatted"] = ":{}:".format(d["pla"]["country"].lower())
        else:
            d["pla_country_formatted"] = ""

        if d["plb"]["country"] is not None:
            d["plb_country_formatted"] = ":{}:".format(d["plb"]["country"].lower())
        else:
            d["plb_country_formatted"] = ""

        # and no race switchers
        d["pla_race"] = switcher(d["pla"]["race"])
        d["plb_race"] = switcher(d["plb"]["race"])

        # Check who won
        temp = {
            "plaws": "",
            "plawe": "",
            "plbws": "",
            "plbwe": ""
        }

        if win(d):
            temp["plaws"] = "[b]"
            temp["plawe"] = "[/b]"
        else:
            temp["plbws"] = "[b]"
            temp["plbwe"] = "[/b]"

        d.update(temp)
        d["pla_id"] = d["pla"]["id"]
        d["pla_tag"] = d["pla"]["tag"]
        d["pla_score"] = d["pla"]["score"]
        d["plb_id"] = d["plb"]["id"]
        d["plb_tag"] = d["plb"]["tag"]
        d["plb_score"] = d["plb"]["score"]

        return TL_HISTORY_MATCH_TEMPLATE.format(**d)

    recent_matches = disp_matches[:min(10, len(disp_matches))]

    recent = "\n".join(format_match(m) for m in recent_matches)

    recent_form = " ".join("W" if win(m) else "L"
                           for m in reversed(recent_matches))

    # Get the parameters and remove those with None value
    get_params = dict((k, form.cleaned_data[k])
                      for k in form.cleaned_data
                      if form.cleaned_data[k] is not None)

    country = ""
    if player.country is not None:
        country = ":{}:".format(player.country.lower())

    tl_params = {
        "player_tag": player.tag,
        "player_country_formatted": country,
        "player_race": switcher(player.race),
        "filter": match_filter,
        "date": match_date,
        "recent": recent,
        "pid": player_id,
        "get": urlencode(get_params),
        "url": "http://aligulac.com"
    }

    tl_params.update({
        "sc_my": base["sc_my"],
        "sc_op": base["sc_op"],
        "msc_my": base["msc_my"],
        "msc_op": base["msc_op"],
        "form": recent_form
    })

    def calc_percent(s):
        f, a = float(int(tl_params[s+"_my"])), int(tl_params[s+"_op"])
        if f + a == 0:
            return "  NaN"
        return round(100 * f / (f+a), 2)

    tl_params.update({
        "sc_percent": calc_percent("sc"),
        "msc_percent": calc_percent("msc")
    })

    tl_params.update(get_params)

    # Final clean up and translation

    if tl_params["bestof"] != "all":
        tl_params["bestof"] = _('best of') + ' {}'.format(tl_params["bestof"])
    else:
        tl_params['bestof'] = _('all')

    if set(tl_params["race"]) == set('ptzr'):
        tl_params["race"] = _('all')
    else:
        tl_params['race'] = {
            'p': _('Protoss'),
            't': _('Terran'),
            'z': _('Zerg'),
            'ptr': _('No Zerg'),
            'pzr': _('No Terran'),
            'tzr': _('No Protoss'),
        }[tl_params['race']]

    if tl_params['country'] in ['all', 'foreigners']:
        tl_params['country'] = {
            'all': _('all'),
            'foreigners': _('foreigners'),
        }[tl_params['country']]
    else:
        tl_params['country'] = transformations.ccn_to_cn(transformations.cca2_to_ccn(tl_params['country']))

    tl_params['offline'] = {
        'offline': _('offline'),
        'online': _('online'),
        'both': _('both'),
    }[tl_params['offline']]

    if tl_params['game'] == 'all':
        tl_params['game'] = _('all')
    else:
        tl_params['game'] = dict(GAMES)[tl_params['game']]

    tl_params.update({
        'resfor': _('Results for'),
        'games': _('Games'),
        'matches': _('Matches'),
        'curform': _('Current form'),
        'recentmatches': _('Recent matches'),
        'filters': _('Filters'),
        # Translators: These have to line up on the right!
        'opprace': _('Opponent Race:    '),
        # Translators: These have to line up on the right!
        'oppcountry': _('Opponent Country: '),
        # Translators: These have to line up on the right!
        'matchformat': _('Match Format:     '),
        # Translators: These have to line up on the right!
        'onoff': _('On/offline:       '),
        # Translators: These have to line up on the right!
        'version': _('Game Version:     '),
        'statslink': _('Stats by [url={url}]Aligulac[/url]'),
        # Translators: Link in the sense of a HTTP hyperlink.
        'link': _('Link'),
    })

    base.update({
        "postable_tl": TL_HISTORY_TEMPLATE.format(**tl_params)
    })
    
    # }}}

    base.update({"title": player.tag})
    
    return render_to_response('player_results.djhtml', base)
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

    base.update({"title": player.tag})
    return render_to_response('historical.djhtml', base)
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

    base.update({"title": player.tag})

    return render_to_response('player_earnings.djhtml', base)
# }}}


# {{{ Postable templates
TL_HISTORY_TEMPLATE = (
    "{resfor} {player_country_formatted} :{player_race}: " +
    "[url={url}/players/{pid}/]{player_tag}[/url]{date}.\n" +
    "\n" +
    "[b]{games}:[/b] {sc_percent:0<5}% ({sc_my}-{sc_op})\n" +
    "[b]{matches}:[/b] {msc_percent:0<5}% ({msc_my}-{msc_op})\n" +
    "\n" +
    "[b][big]{curform}:[/big][/b]\n" +
    "[indent]{form}\n" +
    "[b][big]{recentmatches}:[/big][/b]\n" +
    "{recent}\n" +
    "\n\n" +
    "{filters}:\n" +
    "[spoiler][code]" +
    "{opprace}{race}\n" +
    "{oppcountry}{country}\n" +
    "{matchformat}{bestof}\n" +
    "{onoff}{offline}\n" +
    "{version}{game}\n" +
    "[/code][/spoiler]\n" +
    "[small]{statslink}. " +
    "[url={url}/players/{pid}/results/?{get}]{link}[/url].[/small]"
)

TL_HISTORY_MATCH_TEMPLATE = (
    "[indent]"
    " {pla_country_formatted} :{pla_race}: "
    " {plaws}[url=http://aligulac.com/players/{pla_id}/]{pla_tag}[/url]{plawe}"
    " {pla_score:>2} – {plb_score:<2} "
    " {plb_country_formatted} :{plb_race}: "
    " {plbws}[url=http://aligulac.com/players/{plb_id}/]{plb_tag}[/url]{plbwe}"
)

# }}}
