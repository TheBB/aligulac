# {{{ Imports
from datetime import date
from dateutil.relativedelta import relativedelta
from math import log

from django import forms
from django.core.exceptions import ValidationError
from django.db.models import Q
from django.http import HttpResponse
from django.shortcuts import (
    redirect, 
    render_to_response,
)

from aligulac.cache import cache_page
from aligulac.tools import (
    base_ctx,
    get_param_range,
    Message,
    NotUniquePlayerMessage,
    StrippedCharField,
)

from ratings.models import (
    Match,
    Player,
)
from ratings.templatetags.ratings_extras import (
    ratscale,
    smallhash,
)
from ratings.tools import (
    count_matchup_player,
    count_winloss_games,
    count_winloss_player,
    display_matches,
    find_player,
)

from simul.playerlist import make_player
from simul.formats.match import Match as MatchSim
from simul.formats.mslgroup import MSLGroup
from simul.formats.sebracket import SEBracket
from simul.formats.rrgroup import RRGroup
from simul.formats.teampl import TeamPL
# }}}

# {{{ Prediction formats
FORMATS = [{
    'url':        'match',
    'name':       'Best-of-N match',
    'np-check':   lambda a: a == 2,
    'np-errmsg':  "Expected exactly two players.",
    'bo-check':   lambda a: a == 1,
    'bo-errmsg':  "Expected exactly one 'best of'.",
}, {
    'url':        'dual',
    'name':       'Dual tournament',
    'np-check':   lambda a: a == 4,
    'np-errmsg':  "Expected exactly four players.",
    'bo-check':   lambda a: a == 1,
    'bo-errmsg':  "Expected exactly one 'best of'.",
}, {
    'url':        'sebracket',
    'name':       'Single elimination bracket',
    'np-check':   lambda a: a > 1 and not a & (a-1), 
    'np-errmsg':  "Expected number of players to be a power of two (2,4,8,…).",
    'bo-check':   lambda a: a > 0,
    'bo-errmsg':  "Expected at least one 'best of'.",
}, {
    'url':        'rrgroup',
    'name':       'Round robin group',
    'np-check':   lambda a: a > 2,
    'np-errmsg':  "Expected at least three players.",
    'bo-check':   lambda a: a == 1,
    'bo-errmsg':  "Expected exactly one 'best of'.",

}, {
    'url':        'proleague',
    'name':       'Proleague team match',
    'np-check':   lambda a: a % 2 == 0,
    'np-errmsg':  "Expected an even number of players.",
    'bo-check':   lambda a: a == 1,
    'bo-errmsg':  "Expected exactly one 'best of'.",
}]
# }}}

# {{{ PredictForm: Form for entering a prediction request.
class PredictForm(forms.Form):
    format = forms.ChoiceField(
        choices=[(i, f['name']) for i, f in enumerate(FORMATS)],
        required=True,
        label='Format',
        initial=0,
    )
    bestof = StrippedCharField(max_length=100, required=True, label='Best of', initial='1')
    players = forms.CharField(max_length=10000, required=True, label='Players', initial='')

    # {{{ Constructor
    def __init__(self, request=None):
        if request is not None:
            super(PredictForm, self).__init__(request.GET)
        else:
            super(PredictForm, self).__init__()

        self.label_suffix = ''
    # }}}

    # {{{ Custom validation of bestof and players
    def clean_bestof(self):
        try:
            ret = []
            for a in map(int, self.cleaned_data['bestof'].split(',')):
                ret.append(a)
                assert(a > 0 and a % 2 == 1)
            return ret
        except:
            raise ValidationError("Must be a comma-separated list of positive odd integers (1,3,5,…).")

    def clean_players(self):
        lines = self.cleaned_data['players'].splitlines()
        lineno, ok, players = -1, True, []
        self.messages = []

        for line in lines:
            lineno += 1
            if line.strip() == '':
                continue

            if line.strip() == '-' or line.strip().lower() == 'bye':
                players.append(None)
                continue

            pls = find_player(query=line, make=False)
            if not pls.exists():
                self.messages.append(Message("No matches found: '%s'." % line.strip(), type=Message.ERROR))
                ok = False
            elif pls.count() > 1:
                self.messages.append(NotUniquePlayerMessage(
                    line.strip(), pls, update=self['players'].auto_id,
                    updateline=lineno, type=Message.ERROR
                ))
                ok = False
            else:
                players.append(pls.first())

        if not ok:
            raise ValidationError('One or more errors found in player list.')

        return players
    # }}}

    # {{{ Combined validation of format, bestof and players
    def clean(self):
        self.cleaned_data['format'] = min(max(int(self.cleaned_data['format']), 0), len(FORMATS))
        fmt = FORMATS[self.cleaned_data['format']]

        if 'players' in self.cleaned_data and not fmt['np-check'](len(self.cleaned_data['players'])):
            raise ValidationError(fmt['np-errmsg'])
        if 'bestof' in self.cleaned_data and not fmt['bo-check'](len(self.cleaned_data['bestof'])):
            raise ValidationError(fmt['bo-errmsg'])

        return self.cleaned_data
    # }}}

    # {{{ get_messages: Returns a list of messages after validation
    def get_messages(self):
        if not self.is_valid():
            ret = []
            for field, errors in self.errors.items():
                for error in errors:
                    if field == '__all__':
                        ret.append(Message(error, type=Message.ERROR))
                    else:
                        ret.append(Message(error=error, field=self.fields[field].label))
            return self.messages + ret

        return self.messages
    # }}}

    # {{{ generate_url: Returns an URL to continue to (assumes validation has passed)
    def generate_url(self):
        return '/inference/%s/?bo=%s&ps=%s' % (
            FORMATS[self.cleaned_data['format']]['url'],
            '%2C'.join([str(b) for b in self.cleaned_data['bestof']]),
            '%2C'.join([str(p.id) if p is not None else '0' for p in self.cleaned_data['players']]),
        )
    # }}}
# }}}

# {{{ SetupForm: Form for getting the bo and player data from GET for each prediction format.
class SetupForm(forms.Form):
    bo = forms.CharField(max_length=200, required=True)
    ps = forms.CharField(max_length=200, required=True)

    # {{{ Cleaning methods. NO VALIDATION IS PERFORMED HERE.
    def clean_bo(self):
        return [(int(a)+1)//2 for a in self.cleaned_data['bo'].split(',')]

    def clean_ps(self):
        ids = [int(a) for a in self.cleaned_data['ps'].split(',')]
        players = Player.objects.in_bulk(ids)
        return [players[id] if id in players else None for id in ids]
    # }}}
# }}}

# {{{ Auxiliary functions for prediction

# {{{ group_by: Works the same as itertools.groupby but makes a list.
def group_by(lst, key):
    ret = [(key(lst[0]), [lst[0]])]
    for e in lst[1:]:
        if key(e) != ret[-1][0]:
            ret.append((key(e), [e]))
        else:
            ret[-1][1].append(e)
    return ret
# }}}

# {{{ player_data: Creates a dict with player data
def player_data(player, prefix):
    if player is not None:
        return {
            prefix + '_id':       player.id,
            prefix + '_tag':      player.tag,
            prefix + '_race':     player.race,
            prefix + '_country':  player.country,
        }
    else:
        return {
            prefix + '_id':       None,
            prefix + '_tag':      'BYE',
            prefix + '_race':     None,
            prefix + '_country':  None,
        }
# }}}

# {{{ update_matches(sim, lst, request): Updates the matches in sim from the data in request, according to the
# list lst, which is a list of triples (match name, get param player A, get param player B)
def update_matches(sim, lst, request):
    for m in lst:
        try:
            match = sim.get_match(m)
            num = match.get_num()
            if match.can_modify() and match.:
                match.modify(
                    get_param_range(request, '%s_1' % m, (0, num), 0),
                    get_param_range(request, '%s_2' % m, (0, num), 0),
                )
        except:
            pass
# }}}

# {{{ create_matches: Creates a list of dicts that will work as match objects in the templates, given a sim
# object and a list of match names
def create_matches(sim, lst):
    ret = []
    for rnd, matches in lst:
        for m in matches:
            match = sim.get_match(m)
            if not match.can_modify():
                continue

            ret.append({})
            ret[-1].update(player_data(match.get_player(0).dbpl, 'pla'))
            ret[-1].update(player_data(match.get_player(1).dbpl, 'plb'))
            ret[-1].update({
                'pla_score':    match.get_result()[0],
                'plb_score':    match.get_result()[1],
                'unfixed':      not match.is_fixed(),
                'eventtext':    rnd,
                'match_id':     smallhash(rnd) + '-ent',
                'sim':          match,
                'identifier':   m,
            })

    return ret
# }}}

# {{{ create_median_matches: Creates a list of dicts taht will work as match objects in the templates, given a
# sim object and a list of matc names. Generates MEDIAN RESULTS only.
def create_median_matches(sim, lst, modify=True):
    ret = []
    for rnd, matches in lst:
        for m in matches:
            match = sim.get_match(m)
            match.compute()
            mean = match.find_lsup()
            match.broadcast_instance((0, [mean[4], mean[3]], match))
            if modify:
                match.modify(mean[1], mean[2])

            ret.append({})
            ret[-1].update(player_data(match.get_player(0).dbpl, 'pla'))
            ret[-1].update(player_data(match.get_player(1).dbpl, 'plb'))
            ret[-1].update({
                'pla_score':    mean[1],
                'plb_score':    mean[2],
                'eventtext':    rnd,
                'match_id':     smallhash(rnd) + '-med',
            })

    return ret
# }}}

# }}}

# {{{ predict view
@cache_page
def predict(request):
    base = base_ctx('Inference', 'Predict', request=request)

    base.update({"title": "Predict"})

    if 'submitted' not in request.GET:
        base['form'] = PredictForm()
        return render_to_response('predict.html', base)

    base['form'] = PredictForm(request=request)
    base['messages'] += base['form'].get_messages()

    if not base['form'].is_valid():
        return render_to_response('predict.html', base)
    return redirect(base['form'].generate_url())
# }}}

# {{{ Match prediction view
@cache_page
def match(request):
    base = base_ctx('Inference', 'Predict', request=request)

    # {{{ Get data, set up and simulate
    form = SetupForm(request.GET)
    if not form.is_valid():
        return redirect('/inference/')

    num = form.cleaned_data['bo'][0]
    dbpl = form.cleaned_data['ps']
    sipl = [make_player(p) for p in dbpl]

    match = MatchSim(num)
    match.set_players(sipl)
    match.modify(
        get_param_range(request, 's1', (0, num), 0),
        get_param_range(request, 's2', (0, num), 0),
    )
    match.compute()
    # }}}

    # {{{ Postprocessing
    base.update({
        'form': form,
        'dbpl': dbpl,
        'rta': sipl[0].elo_vs_opponent(sipl[1]),
        'rtb': sipl[1].elo_vs_opponent(sipl[0]),
        'proba': match.get_tally()[sipl[0]][1],
        'probb': match.get_tally()[sipl[1]][1],
        'match': match,
    })

    base.update({
        'max': max(base['proba'], base['probb']),
        'fav': dbpl[0] if base['proba'] > base['probb'] else dbpl[1],
    })

    resa, resb = [], []
    outcomes = [
        {'sca': outcome[1], 'scb': outcome[2], 'prob': outcome[0]} 
        for outcome in match.instances_detail()
    ]
    resa = [oc for oc in outcomes if oc['sca'] > oc['scb']]
    resb = [oc for oc in outcomes if oc['scb'] > oc['sca']]
    if len(resa) < len(resb):
        resa = [None] * (len(resb) - len(resa)) + resa
    else:
        resb = [None] * (len(resa) - len(resb)) + resb
    base['res'] = list(zip(resa, resb))
    # }}}

    # {{{ Scores and other data
    thr = date.today() - relativedelta(months=2)
    pla_matches = dbpl[0].get_matchset()
    plb_matches = dbpl[1].get_matchset()
    base['tot_w_a'], base['tot_l_a'] = count_winloss_player(pla_matches, dbpl[0])
    base['frm_w_a'], base['frm_l_a'] = count_winloss_player(pla_matches.filter(date__gte=thr), dbpl[0])
    base['tot_w_b'], base['tot_l_b'] = count_winloss_player(plb_matches, dbpl[1])
    base['frm_w_b'], base['frm_l_b'] = count_winloss_player(plb_matches.filter(date__gte=thr), dbpl[1])
    if dbpl[1].race in 'PTZ':
        base['mu_w_a'], base['mu_l_a'] = count_matchup_player(pla_matches, dbpl[0], dbpl[1].race)
        base['fmu_w_a'], base['fmu_l_a'] = count_matchup_player(
            pla_matches.filter(date__gte=thr), dbpl[0], dbpl[1].race
        )
    if dbpl[0].race in 'PTZ':
        base['mu_w_b'], base['mu_l_b'] = count_matchup_player(plb_matches, dbpl[1], dbpl[0].race)
        base['fmu_w_b'], base['fmu_l_b'] = count_matchup_player(
            plb_matches.filter(date__gte=thr), dbpl[1], dbpl[0].race
        )
    wa_a, wb_a = count_winloss_games(Match.objects.filter(pla=dbpl[0], plb=dbpl[1]))
    wb_b, wa_b = count_winloss_games(Match.objects.filter(pla=dbpl[1], plb=dbpl[0]))
    base['vs_a'] = wa_a + wa_b
    base['vs_b'] = wb_a + wb_b

    base['matches'] = display_matches(
        Match.objects.filter(Q(pla=dbpl[0], plb=dbpl[1]) | Q(plb=dbpl[0], pla=dbpl[1]))
            .select_related('period', 'pla', 'plb')
            .order_by('-date', 'id'),
        fix_left=dbpl[0],
    )
    # }}}

    postable_match(base, request)

    base.update({"title": "{} vs. {}".format(dbpl[0].tag, dbpl[1].tag)})

    return render_to_response('pred_match.html', base)
# }}}

# {{{ Dual tournament prediction view
@cache_page
def dual(request):
    base = base_ctx('Inference', 'Predict', request=request)

    # {{{ Get data, set up and simulate
    form = SetupForm(request.GET)
    if not form.is_valid():
        return redirect('/inference/')

    num = form.cleaned_data['bo'][0]
    dbpl = form.cleaned_data['ps']
    sipl = [make_player(p) for p in dbpl]

    group = MSLGroup(num)
    group.set_players(sipl)
    update_matches(group, '12wlf', request)

    group.compute()
    # }}}

    # {{{ Post-processing
    players = list(sipl)
    for p in players:
        p.tally = group.get_tally()[p]
    for i in range(0, 4):
        players.sort(key=lambda p: p.tally[i], reverse=True)

    rounds = [
        ('Intial round',                    '12'),
        ('Winners\' and losers\' matches',  'wl'),
        ('Final match',                     'f'),
    ]

    base.update({
        'players':  players,
        'matches':  create_matches(group, rounds),
        'meanres':  create_median_matches(group, rounds),
        'form':     form,
    })
    # }}}

    postable_dual(base, request)

    base.update({"title": "Dual tournament"})

    return render_to_response('pred_4pswiss.html', base)
# }}}

# {{{ Single elimination prediction view
@cache_page
def sebracket(request):
    base = base_ctx('Inference', 'Predict', request=request)

    # {{{ Get data, set up and simulate
    form = SetupForm(request.GET)
    if not form.is_valid():
        return redirect('/inference/')

    num = form.cleaned_data['bo']
    dbpl = form.cleaned_data['ps']
    sipl = [make_player(p) for p in dbpl]

    nrounds = int(log(len(sipl), 2))
    num = [num[0]] * (nrounds - len(num)) + num
    if len(num) > nrounds:
        num = num[-nrounds:]

    bracket = SEBracket(num)
    bracket.set_players(sipl)
    matchlist = ['%i-%i' % (rnd, j) for rnd in range(1, nrounds+1) for j in range(1, 2**(nrounds-rnd)+1)]
    update_matches(bracket, matchlist, request)

    bracket.compute()
    # }}}

    # {{{ Post-processing
    players = list(sipl)
    for p in players:
        p.tally = bracket.get_tally()[p][::-1]
    for i in range(len(players[0].tally)-1, -1, -1):
        players.sort(key=lambda p: p.tally[i], reverse=True)

    rounds = [
        ('Round %i' % rnd, ['%i-%i' % (rnd, j) for j in range(1, 2**(nrounds-rnd)+1)])
        for rnd in range(1, nrounds+1)
    ]
    
    base.update({
        'players':  players,
        'matches':  create_matches(bracket, rounds),
        'meanres':  create_median_matches(bracket, rounds),
        'nrounds':  nrounds,
        'form':     form,
    })
    # }}}

    postable_sebracket(base, request, group_by(base['meanres'], key=lambda a: a['eventtext']))

    base.update({"title": "Single elimination bracket"})

    return render_to_response('pred_sebracket.html', base)
# }}}

# {{{ Round robin group prediction view
@cache_page
def rrgroup(request):
    base = base_ctx('Inference', 'Predict', request=request)

    # {{{ Get data, set up and simulate
    form = SetupForm(request.GET)
    if not form.is_valid():
        return redirect('/inference/')

    num = form.cleaned_data['bo'][0]
    dbpl = form.cleaned_data['ps']
    sipl = [make_player(p) for p in dbpl]

    nplayers = len(sipl)
    nmatches = (nplayers-1) * nplayers // 2

    group = RRGroup(nplayers, num, ['mscore', 'sscore', 'imscore', 'isscore', 'ireplay'], 1)
    group.set_players(sipl)
    group.compute() # Necessary to fill the tiebreak tables.
    group.save_tally()

    matchlist = [str(i) for i in range(0, nmatches)]
    update_matches(group, matchlist, request)
    group.compute()
    # }}}

    #{{{ Post-processing
    players = list(sipl)
    for p in players:
        p.tally = group.get_tally()[p][::-1]
    for i in range(len(players[0].tally)-1, -1, -1):
        players.sort(key=lambda p: p.tally[i], reverse=True)

    rounds = [('Matches', matchlist)]

    base.update({
        'players':  players,
        'matches':  create_matches(group, rounds),
        'form':     form,
    })

    base['meanres'] = create_median_matches(group, rounds, modify=True)
    group.compute()

    for p in sipl:
        p.mtally = group.get_tally()[p]
    base['mplayers'] = group.table
    # }}}

    postable_rrgroup(base, request)

    base.update({"title": "Round robin group"})

    return render_to_response('pred_rrgroup.html', base)
# }}}

# {{{ Proleage prediction view
@cache_page
def proleague(request):
    base = base_ctx('Inference', 'Predict', request=request)

    # {{{ Get data, set up and simulate
    form = SetupForm(request.GET)
    if not form.is_valid():
        return redirect('/inference/')

    num = form.cleaned_data['bo'][0]
    dbpl = form.cleaned_data['ps']
    sipl = [make_player(p) for p in dbpl]

    nplayers = len(sipl)

    sim = TeamPL(num)
    sim.set_players(sipl)

    matchlist = [str(i) for i in range(0, nplayers//2)]
    update_matches(sim, matchlist, request)
    sim.compute()
    # }}}

    # {{{ Post-processing
    results, prob_draw = [], 0
    for si in range(0, nplayers//4 + 1):
        if si == nplayers//4 and nplayers//2 % 2 == 0:
            prob_draw = sim.get_tally()[0][si]
        else:
            results.append({
                'scl':    si,
                'scw':    sim._numw,
                'proba':  sim.get_tally()[1][si],
                'probb':  sim.get_tally()[0][si],
            })

    rounds = [('Matches', matchlist)]
    matches = [sim.get_match(m) for m in matchlist]
    base.update({
        's1':         sum([1 if m._result[0] > m._result[1] and m.is_fixed() else 0 for m in matches]),
        's2':         sum([1 if m._result[0] < m._result[1] and m.is_fixed() else 0 for m in matches]),
        'results':    results,
        'prob_draw':  prob_draw,
        'ta':         sum([r['proba'] for r in results]),
        'tb':         sum([r['probb'] for r in results]),
        'matches':    create_matches(sim, rounds),
        'meanres':    create_median_matches(sim, rounds),
        'form':       form,
    })
    # }}}

    postable_proleague(base, request)

    base.update({"title": "Proleague team match"})

    return render_to_response('pred_proleague.html', base)
# }}}

# {{{ Postables

# {{{ Headers and footers
TL_HEADER = '[center][code]'
TL_SEBRACKET_MIDDLE = (
    '[/code][/center][b]Median Outcome Bracket[/b]\n'
    '[spoiler][code]'
)
TL_SEBRACKET_FOOTER = (
    '[/code][/spoiler]\n'
    '[small]Estimated by [url=http://aligulac.com/]Aligulac[/url]. '
    '[url=%s]Modify[/url].[/small]'
)
TL_FOOTER = (
    '[/code][/center]\n'
    '[small]Estimated by [url=http://aligulac.com/]Aligulac[/url]. '
    '[url=%s]Modify[/url].[/small]'
)

REDDIT_HEADER = ''
REDDIT_FOOTER = '\n\n^(Estimated by) [^Aligulac](http://aligulac.com/)^. [^Modify](%s)^.'
# }}}

# {{{ ordinal: Converts an integer to its ordinal (string) representation
def ordinal(value):
    try:
        value = int(value)
    except (TypeError, ValueError):
        return value
    suffixes = ('th', 'st', 'nd', 'rd', 'th', 'th', 'th', 'th', 'th', 'th')
    if value % 100 in (11, 12, 13):
        return "%d%s" % (value, suffixes[0])
    return "%d%s" % (value, suffixes[value % 10])
## }}}

# {{{ left_center_right(strings, gap=2, justify=True, indent=0): Aid for pretty-printing tables
# Takes a list of triples (strings), each element a line with left, center and right entries.
# gap: The number of spaces between columns
# justify: If true, makes the left and right columns equally wide
# indent: Extra indentation to add to the left
def left_center_right(strings, gap=2, justify=True, indent=0):
    width = lambda i: max([len(s[i]) for s in strings if s is not None])
    width_l = width(0) + 4
    width_c = width(1)
    width_r = width(2) + 4

    if justify:
        width_l = max(width_l, width_r)
        width_r = width_l

    width_l += indent

    out = []
    for s in strings:
        if s is None:
            out.append(' '*indent + '-'*(width_l + width_r + width_c + 2*gap - indent))
            continue

        R = (width_c - len(s[1])) // 2
        L = width_c - len(s[1]) - R
        out.append(
              ' '*(width_l-len(s[0])) + s[0]
            + ' '*(L+gap) + s[1] + ' '*(R+gap) 
            + s[2] + ' '*(width_r-len(s[2]))
        )

    return '\n'.join(out)
# }}}

# {{{ postable_match
def postable_match(base, request):
    pla = base['match'].get_player(0)
    plb = base['match'].get_player(1)

    numlen = len(str(base['match'].get_num()))

    strings = [(
        '({rat}) {name}'.format(rat=ratscale(pla.elo_vs_opponent(plb)), name=pla.name),
        '{sca: >{nl}}-{scb: <{nl}}'.format(
            sca=base['match'].get_result()[0],
            scb=base['match'].get_result()[1],
            nl=numlen
        ),
        '{name} ({rat})'.format(rat=ratscale(plb.elo_vs_opponent(pla)), name=plb.name),
    ), None]

    for resa, resb in base['res']:
        L = ('{pctg: >6.2f}% {sca}-{scb: >{nl}}'.format(
            pctg=100*resa['prob'], sca=resa['sca'], scb=resa['scb'], nl=numlen
        ) if resa else '')
        R = ('{sca: >{nl}}-{scb} {pctg: >6.2f}%'.format(
            pctg=100*resb['prob'], sca=resb['sca'], scb=resb['scb'], nl=numlen
        ) if resb else '')
        strings.append((L, '', R))

    strings += [None, (
        '{pctg: >6.2f}%'.format(pctg=100*base['proba']), '',
        '{pctg: >6.2f}%'.format(pctg=100*base['probb']),
    )]

    median = base['match'].find_lsup()

    base['postable_tl'] = (
          TL_HEADER
        + left_center_right(strings)
        + ('\n\nMedian outcome: {pla} {sca}-{scb} {plb}'.format(
            pla=pla.name, sca=median[1], scb=median[2], plb=plb.name))
        + TL_FOOTER % request.build_absolute_uri()
    )

    base['postable_reddit'] = (
          REDDIT_HEADER 
        + left_center_right(strings, justify=False, indent=4) 
        + ('\n\n    Median outcome: {pla} {sca}-{scb} {plb}'.format(
            pla=pla.name, sca=median[1], scb=median[2], plb=plb.name))
        + REDDIT_FOOTER % request.build_absolute_uri()
    )
# }}}

# {{{ postable_dual
def postable_dual(base, request):
    numlen = max([len(p.dbpl.tag) for p in base['players'] if p.dbpl is not None])

    strings = (
        [('Top 2      1st      2nd      3rd      4th', '', ''), None] +
        [('{name: >{nl}}   {top2: >7.2f}% {p1: >7.2f}% {p2: >7.2f}% {p3: >7.2f}% {p4: >7.2f}%'.format(
            top2 = 100*(p.tally[2]+p.tally[3]),
            p1   = 100*p.tally[3],
            p2   = 100*p.tally[2],
            p3   = 100*p.tally[1],
            p4   = 100*p.tally[0],
            name = p.dbpl.tag,
            nl   = numlen,
        ), '', '') for p in base['players']]
    )

    base['postable_tl'] = (
          TL_HEADER
        + left_center_right(strings, justify=False, gap=0)
        + TL_FOOTER % request.build_absolute_uri()
    )

    base['postable_reddit'] = (
          REDDIT_HEADER
        + left_center_right(strings, justify=False, gap=0, indent=4)
        + REDDIT_FOOTER % request.build_absolute_uri()
    )
# }}}

# {{{ postable_sebracket
def postable_sebracket(base, request, bracket):
    numlen = max([len(p.dbpl.tag) for p in base['players'] if p.dbpl is not None])

    strings = [(''.join(
        ['Win    '] + 
        ['Top {i: <5}'.format(i=2**rnd) for rnd in range(1, int(log(len(base['players']),2)))] +
        ['Top {i}'.format(i=len(base['players']))]
    ), '', ''), None]

    for p in base['players']:
        if p.dbpl is None:
            continue
        strings.append((''.join(
            ['{name: >{nl}}  '.format(name=p.dbpl.tag, nl=numlen)] +
            [' {p: >7.2f}%'.format(p=100*t) for t in p.tally]
        ), '', ''))

    base['postable_tl'] = (
          TL_HEADER
        + left_center_right(strings, justify=False, gap=0)
        + TL_SEBRACKET_MIDDLE
        + create_postable_bracket(bracket)
        + TL_SEBRACKET_FOOTER % request.build_absolute_uri()
    )

    base['postable_reddit'] = (
          REDDIT_HEADER
        + left_center_right(strings, justify=False, gap=0, indent=4)
        + REDDIT_FOOTER % request.build_absolute_uri()
    )

    base['postable_bracket_reddit'] = (
          REDDIT_HEADER
        + create_postable_bracket(bracket, indent=4)
        + REDDIT_FOOTER % request.build_absolute_uri()
    )
# }}}

# {{{ create_postable_bracket
def create_postable_bracket(bracket, indent=0):
    nrounds = len(bracket)

    result = []
    for r, (rnd_name, matches) in enumerate(bracket):
        result.append([])
        result[r].extend([''] * (2**r - 1))

        for i, m in enumerate(matches):
            pla = m['pla_tag']
            plascore = m['pla_score']
            plb = m['plb_tag']
            plbscore = m['plb_score']

            if r != 0:
                pla = (' ' + pla).rjust(12, '─')
                plb = (' ' + plb).rjust(12, '─')
            else:
                pla = (' ' + pla).rjust(12)
                plb = (' ' + plb).rjust(12)
            result[r].append('{0} {1:>1} ┐ '.format(pla, plascore))
            result[r].extend(['               │ '] * (2**r - 1))
            result[r].append('               ├─')
            result[r].extend(['               │ '] * (2**r - 1))
            result[r].append('{0} {1:>1} ┘ '.format(plb, plbscore))

            if i < len(matches):
                result[r].extend(['                 '] * int(2**(r + 1) - 1))

    result.append([''] * (2**(r + 1) - 1))
    final = bracket[-1][1][0]
    result[-1].append(' ' + (
        final['pla_tag'] 
        if final['pla_score'] > final['plb_score'] 
        else final ['plb_tag']
    ))

    postable_result = ''
    for line in range(len(result[0])):
        postable_result += ' '*indent + ''.join(block[line] for block in result if line < len(block)) + '\n'

    return postable_result.rstrip()
# }}}

# {{{ postable_rrgroup
def postable_rrgroup(base, request):
    numlen = max([len(p.dbpl.tag) for p in base['players'] if p.dbpl is not None])

    strings = [(''.join([
        ('{s: <9}'.format(s=ordinal(i+1)) if i < len(base['players'])-1 else ordinal(i+1))
        for i in range(0, len(base['players']))
    ]), '', ''), None]

    for p in base['players']:
        strings.append((''.join(
            ['{name: >{nl}}  '.format(name=p.dbpl.tag if p.dbpl is not None else 'BYE', nl=numlen)] +
            [' {p: >7.2f}%'.format(p=100*t) for t in p.tally]
        ), '', ''))

    base['postable_tl'] = (
          TL_HEADER
        + left_center_right(strings, justify=False, gap=0)
        + TL_FOOTER % request.build_absolute_uri()
    )

    base['postable_reddit'] = (
          REDDIT_HEADER
        + left_center_right(strings, justify=False, gap=0, indent=4)
        + REDDIT_FOOTER % request.build_absolute_uri()
    )
# }}}

# {{{ postable_proleague
def postable_proleague(base, request):
    numlen = len(str((len(base['matches']) + 1) // 2))
    strings = [(
        'Team {p}'.format(p=base['matches'][0]['pla_tag']),
        '{sca: >{nl}}-{scb: <{nl}}'.format(sca=base['s1'], scb=base['s2'], nl=numlen),
        'Team {p}'.format(p=base['matches'][0]['plb_tag']),
    ), None]

    for r in base['results']:
        if r['proba'] == 0.0 and r['probb'] == 0.0:
            continue
        L = ('{pctg: >6.2f}% {sca}-{scb: >{nl}}'.format(
            pctg=100*r['proba'], sca=r['scw'], scb=r['scl'], nl=numlen
        ) if r['proba'] > 0.0 else '')
        R = ('{sca: >{nl}}-{scb} {pctg: >6.2f}%'.format(
            pctg=100*r['probb'], sca=r['scl'], scb=r['scw'], nl=numlen
        ) if r['probb'] > 0.0 else '')
        strings.append((L, '', R))

    strings += [None, (
        '{pctg: >6.2f}%'.format(pctg=100*base['ta']),
        '{pctg: >6.2f}%'.format(pctg=100*base['prob_draw']) if base['prob_draw'] > 0.0 else '',
        '{pctg: >6.2f}%'.format(pctg=100*base['tb']),
    )]

    base['postable_tl'] = (
          TL_HEADER
        + left_center_right(strings)
        + TL_FOOTER % request.build_absolute_uri()
    )

    base['postable_reddit'] = (
          REDDIT_HEADER 
        + left_center_right(strings, justify=False, indent=4) 
        + REDDIT_FOOTER % request.build_absolute_uri()
    )
# }}}

# }}}
