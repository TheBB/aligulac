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
from django.utils.translation import (
    ugettext_lazy as _,
    ugettext
)

from aligulac.cache import cache_page
from aligulac.tools import (
    base_ctx,
    get_param,
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
    'name':       _('Best-of-N match'),
    'np-check':   lambda a: a == 2,
    'np-errmsg':  _("Expected exactly two players."),
    'bo-check':   lambda a: a == 1,
    'bo-errmsg':  _("Expected exactly one 'best of'."),
}, {
    'url':        'dual',
    'name':       _('Dual tournament'),
    'np-check':   lambda a: a == 4,
    'np-errmsg':  _("Expected exactly four players."),
    'bo-check':   lambda a: a == 1,
    'bo-errmsg':  _("Expected exactly one 'best of'."),
}, {
    'url':        'sebracket',
    'name':       _('Single elimination bracket'),
    'np-check':   lambda a: a > 1 and not a & (a-1), 
    'np-errmsg':  _("Expected number of players to be a power of two (2,4,8,…)."),
    'bo-check':   lambda a: a > 0,
    'bo-errmsg':  _("Expected at least one 'best of'."),
}, {
    'url':        'rrgroup',
    'name':       _('Round robin group'),
    'np-check':   lambda a: a > 2,
    'np-errmsg':  _("Expected at least three players."),
    'bo-check':   lambda a: a == 1,
    'bo-errmsg':  _("Expected exactly one 'best of'."),

}, {
    'url':        'proleague',
    'name':       _('Proleague team match'),
    'np-check':   lambda a: a % 2 == 0,
    'np-errmsg':  _("Expected an even number of players."),
    'bo-check':   lambda a: a == 1,
    'bo-errmsg':  _("Expected exactly one 'best of'."),
}]
# }}}

# {{{ PredictForm: Form for entering a prediction request.
class PredictForm(forms.Form):
    format = forms.ChoiceField(
        choices=[(i, f['name']) for i, f in enumerate(FORMATS)],
        required=True,
        label=_('Format'),
        initial=0,
    )
    bestof = StrippedCharField(max_length=100, required=True, label=_('Best of'), initial='1')
    players = forms.CharField(max_length=10000, required=True, label=_('Players'), initial='')

    # {{{ Constructor
    def __init__(self, request=None):
        self.messages = []
 
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
            raise ValidationError(_("Must be a comma-separated list of positive odd integers (1,3,5,…)."))

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
                # Translators: Matches as in search matches
                self.messages.append(Message(_("No matches found: '%s'.") % line.strip(), type=Message.ERROR))
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
            raise ValidationError(_('One or more errors found in player list.'))

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

# {{{ predict view
@cache_page
def predict(request):
    base = base_ctx('Inference', 'Predict', request=request)

    if 'submitted' not in request.GET:
        base['form'] = PredictForm()
        return render_to_response('predict.djhtml', base)

    base['form'] = PredictForm(request=request)
    base['messages'] += base['form'].get_messages()

    if not base['form'].is_valid():
        return render_to_response('predict.djhtml', base)
    return redirect(base['form'].generate_url())
# }}}

# {{{ Match predictions

# {{{ MatchPredictionResult
class MatchPredictionResult:
    def range(self, i, mn, mx):
        return min(max(i, mn), mx)

    def __init__(self, dbpl=None, bos=None, s1=None, s2=None):
        if dbpl is None:
            return

        sipl = [make_player(p) for p in dbpl]
        num = bos[0]
        obj = MatchSim(num)
        obj.set_players(sipl)
        obj.modify(self.range(int(s1), 0, num), self.range(int(s2), 0, num))
        obj.compute()

        self.dbpl = dbpl
        self.bos = bos
        self.sipl = sipl
        self.num = num
        self.obj = obj
        self.pla, self.plb = dbpl[0], dbpl[1]
        self.rta = sipl[0].elo_vs_opponent(sipl[1])
        self.rtb = sipl[1].elo_vs_opponent(sipl[0])
        self.proba = obj.get_tally()[sipl[0]][1]
        self.probb = obj.get_tally()[sipl[1]][1]
        self.sca = s1
        self.scb = s2

        self.outcomes = [
            {'sca': outcome[1], 'scb': outcome[2], 'prob': outcome[0]}
            for outcome in obj.instances_detail()
        ]

    def generate_updates(self):
        return '&'.join(['s1=%s' % self.sca, 's2=%s' % self.scb])
# }}}

# {{{ Match prediction view
@cache_page
def match(request):
    base = base_ctx('Inference', 'Predict', request=request)

    # {{{ Get data, set up and simulate
    form = SetupForm(request.GET)
    if not form.is_valid():
        return redirect('/inference/')

    result = MatchPredictionResult(
        dbpl=form.cleaned_data['ps'],
        bos=form.cleaned_data['bo'],
        s1=get_param(request, 's1', 0),
        s2=get_param(request, 's2', 0),
    )
    # }}}

    # {{{ Postprocessing
    base.update({
        'form': form,
        'dbpl': result.dbpl,
        'rta': result.rta,
        'rtb': result.rtb,
        'proba': result.proba,
        'probb': result.probb,
        'match': result.obj,
    })

    base.update({
        'max': max(base['proba'], base['probb']),
        'fav': result.dbpl[0] if base['proba'] > base['probb'] else result.dbpl[1],
    })

    resa = [oc for oc in result.outcomes if oc['sca'] > oc['scb']]
    resb = [oc for oc in result.outcomes if oc['scb'] > oc['sca']]
    if len(resa) < len(resb):
        resa = [None] * (len(resb) - len(resa)) + resa
    else:
        resb = [None] * (len(resa) - len(resb)) + resb
    base['res'] = list(zip(resa, resb))
    # }}}

    # {{{ Scores and other data
    dbpl = result.dbpl
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

    return render_to_response('pred_match.djhtml', base)
# }}}

# }}}

# {{{ Superclass for combination format results
class CombinationPredictionResult:
    def range(self, i, mn, mx):
        return min(max(int(i), mn), mx)

    def update_matches(self, obj, prefixes, args):
        self.updates = []
        for m in prefixes:
            try:
                match = obj.get_match(m)
                num = match.get_num()
                if match.can_modify():
                    match.modify(
                        self.range(args.get('%s_1' % m, 0), 0, num),
                        self.range(args.get('%s_2' % m, 0), 0, num),
                    )
                    if '%s_1' % m in args and args['%s_1' % m] != '0':
                        self.updates.append(('%s_1' % m, args['%s_1' % m]))
                    if '%s_2' % m in args and args['%s_2' % m] != '0':
                        self.updates.append(('%s_2' % m, args['%s_2' % m]))
            except:
                pass

    def player_data(self, player):
        if player is not None:
            return {
                'id':       player.id,
                'tag':      player.tag,
                'race':     player.race,
                'country':  player.country,
            }
        else:
            return {
                'id':       None,
                'tag':      'BYE',
                'race':     None,
                'country':  None,
            }

    def create_matches(self, sim, prefixes):
        ret = []
        for rnd, matches in prefixes:
            for m in matches:
                match = sim.get_match(m)
                if not match.can_modify():
                    continue

                ret.append({})
                ret[-1]['pla'] = self.player_data(match.get_player(0).dbpl)
                ret[-1]['plb'] = self.player_data(match.get_player(1).dbpl)
                ret[-1]['pla']['score'] = match.get_result()[0]
                ret[-1]['plb']['score'] = match.get_result()[1]

                ret[-1].update({
                    'unfixed':      not match.is_fixed(),
                    'eventtext':    rnd,
                    'match_id':     smallhash(rnd) + '-ent',
                    'sim':          match,
                    'identifier':   m,
                })

        return ret

    def create_median_matches(self, sim, prefixes, modify=True):
        ret = []
        for rnd, matches in prefixes:
            for m in matches:
                match = sim.get_match(m)
                match.compute()
                mean = match.find_lsup()
                match.broadcast_instance((0, [mean[4], mean[3]], match))
                if modify:
                    match.modify(mean[1], mean[2])

                ret.append({})
                ret[-1]['pla'] = self.player_data(match.get_player(0).dbpl)
                ret[-1]['plb'] = self.player_data(match.get_player(1).dbpl)
                ret[-1]['pla']['score'] = mean[1]
                ret[-1]['plb']['score'] = mean[2]
                ret[-1].update({
                    'eventtext':    rnd,
                    'match_id':     smallhash(rnd) + '-med',
                    'identifier':   m,
                })

        return ret

    def generate_updates(self):
        return '&'.join('%s=%s' % up for up in self.updates)
# }}}

# {{{ Dual tournament predictions

# {{{ DualPredictionResult
class DualPredictionResult(CombinationPredictionResult):
    def __init__(self, dbpl=None, bos=None, args=None):
        if dbpl is None:
            return

        prefixes = '12wlf'
        rounds = [
            (_('Intial round'),                    '12'),
            (_('Winners\' and losers\' matches'),  'wl'),
            (_('Final match'),                     'f'),
        ]

        self.bos = bos
        self.dbpl = dbpl
        sipl = [make_player(p) for p in dbpl]
        num = bos[0]
        obj = MSLGroup(num)
        obj.set_players(sipl)
        self.update_matches(obj, prefixes, args)
        obj.compute()

        players = list(sipl)
        for p in players:
            p.tally = obj.get_tally()[p][::-1]
        for i in range(3, -1, -1):
            players.sort(key=lambda p: p.tally[i], reverse=True)

        self.table = [
            {'player': self.player_data(p.dbpl), 'probs': p.tally}
            for p in players
        ]

        self.matches = self.create_matches(obj, rounds)
        self.meanres = self.create_median_matches(obj, rounds)
# }}}

# {{{ Dual tournament prediction view
@cache_page
def dual(request):
    base = base_ctx('Inference', 'Predict', request=request)

    # {{{ Get data, set up and simulate
    form = SetupForm(request.GET)
    if not form.is_valid():
        return redirect('/inference/')

    result = DualPredictionResult(
        dbpl=form.cleaned_data['ps'],
        bos=form.cleaned_data['bo'],
        args=request.GET,
    )
    # }}}

    # {{{ Post-processing
    base.update({
        'table':    result.table,
        'matches':  result.matches,
        'meanres':  result.meanres,
        'form':     form,
    })
    # }}}

    postable_dual(base, request)

    return render_to_response('pred_4pswiss.djhtml', base)
# }}}

# }}}

# {{{ Single elimination predictions

# {{{ SingleEliminationPredictionResult
class SingleEliminationPredictionResult(CombinationPredictionResult):
    def __init__(self, dbpl=None, bos=None, args=None):
        if dbpl is None:
            return

        nrounds = int(log(len(dbpl), 2))
        num = [bos[0]] * (nrounds - len(bos)) + bos
        if len(num) > nrounds:
            num = num[-nrounds:]

        prefixes = ['%i-%i' % (rnd, j) for rnd in range(1, nrounds+1) for j in range(1, 2**(nrounds-rnd)+1)]
        rounds = [
            (_('Round %i') % rnd, ['%i-%i' % (rnd, j) for j in range(1, 2**(nrounds-rnd)+1)])
            for rnd in range(1, nrounds+1)
        ]

        self.dbpl = dbpl
        self.bos = bos
        sipl = [make_player(p) for p in dbpl]
        obj = SEBracket(num)
        obj.set_players(sipl)
        self.update_matches(obj, prefixes, args)
        obj.compute()

        players = list(sipl)
        for p in players:
            p.tally = obj.get_tally()[p][::-1]
        for i in range(len(players[0].tally)-1, -1, -1):
            players.sort(key=lambda p: p.tally[i], reverse=True)

        self.table = [
            {'player': self.player_data(p.dbpl), 'probs': p.tally}
            for p in players
        ]

        self.matches = self.create_matches(obj, rounds)
        self.meanres = self.create_median_matches(obj, rounds)
        self.nrounds = nrounds
# }}}

# {{{ Single tournament prediction view
@cache_page
def sebracket(request):
    base = base_ctx('Inference', 'Predict', request=request)

    # {{{ Get data, set up and simulate
    form = SetupForm(request.GET)
    if not form.is_valid():
        return redirect('/inference/')

    result = SingleEliminationPredictionResult(
        dbpl=form.cleaned_data['ps'],
        bos=form.cleaned_data['bo'],
        args=request.GET,
    )
    # }}}

    # {{{ Post-processing
    base.update({
        'table':    result.table,
        'matches':  result.matches,
        'meanres':  result.meanres,
        'nrounds':  result.nrounds,
        'form':     form,
    })
    # }}}

    postable_sebracket(base, request, group_by(base['meanres'], key=lambda a: a['eventtext']))

    return render_to_response('pred_sebracket.djhtml', base)
# }}}

# }}}

# {{{ Round robin predictions

# {{{ RoundRobinPredictionResult
class RoundRobinPredictionResult(CombinationPredictionResult):
    def __init__(self, dbpl=None, bos=None, args=None):
        if dbpl is None:
            return

        nplayers = len(dbpl)
        nmatches = (nplayers-1) * nplayers // 2
        num = bos[0]

        prefixes = [str(i) for i in range(0, nmatches)]

        self.dbpl = dbpl
        self.bos = bos
        sipl = [make_player(p) for p in dbpl]

        obj = RRGroup(nplayers, num, ['mscore', 'sscore', 'imscore', 'isscore', 'ireplay'], 1)
        obj.set_players(sipl)
        obj.compute() # Necessary to fill the tiebreak tables.
        obj.save_tally()
        self.update_matches(obj, prefixes, args)
        obj.compute()

        players = list(sipl)
        for p in players:
            p.tally = obj.get_tally()[p][::-1]
        for i in range(len(players[0].tally)-1, -1, -1):
            players.sort(key=lambda p: p.tally[i], reverse=True)

        self.table = [
            {'player': self.player_data(p.dbpl), 'probs': p.tally}
            for p in players
        ]

        self.matches = self.create_matches(obj, [(_('Group play'), prefixes)])
        self.meanres = self.create_median_matches(obj, [(_('Group play'), prefixes)])

        obj.compute()

        mplayers = list(sipl)
        for p in mplayers:
            p.mtally = obj.get_tally()[p]
        self.mtable = [{
            'player': self.player_data(p.dbpl),
            'exp_match_wins': p.mtally.exp_mscore()[0],
            'exp_match_losses': p.mtally.exp_mscore()[1],
            'exp_set_wins': p.mtally.exp_sscore()[0],
            'exp_set_losses': p.mtally.exp_sscore()[1],
        } for p in obj.table]
# }}}

# {{{ Round robin group prediction view
@cache_page
def rrgroup(request):
    base = base_ctx('Inference', 'Predict', request=request)

    # {{{ Get data, set up and simulate
    form = SetupForm(request.GET)
    if not form.is_valid():
        return redirect('/inference/')

    result = RoundRobinPredictionResult(
        dbpl=form.cleaned_data['ps'],
        bos=form.cleaned_data['bo'],
        args=request.GET,
    )
    # }}}

    #{{{ Post-processing
    base.update({
        'table':    result.table,
        'mtable':   result.mtable,
        'matches':  result.matches,
        'meanres':  result.meanres,
        'form':     form,
    })
    # }}}

    postable_rrgroup(base, request)

    return render_to_response('pred_rrgroup.djhtml', base)
# }}}

# }}}

# {{{ Proleague predictions

# {{{ ProleaguePredictionResult
class ProleaguePredictionResult(CombinationPredictionResult):
    def __init__(self, dbpl=None, bos=None, args=None):
        if dbpl is None:
            return

        self.dbpl = dbpl
        self.bos = bos

        num = bos[0]
        nplayers = len(dbpl)
        nmatches = nplayers//2

        sipl = [make_player(p) for p in dbpl]

        obj = TeamPL(num)
        obj.set_players(sipl)

        prefixes = [str(i) for i in range(0, nmatches)]

        self.update_matches(obj, prefixes, args)
        obj.compute()

        self.matches = self.create_matches(obj, [(_('Matches'), prefixes)])

        self.outcomes = []
        self.prob_draw = 0
        for si in range(0, nmatches//2 + 1):
            if si == nmatches//2 and nmatches % 2 == 0:
                self.prob_draw = obj.get_tally()[0][si]
            else:
                self.outcomes.append({
                    'loser':  si,
                    'winner': obj._numw,
                    'proba':  obj.get_tally()[1][si],
                    'probb':  obj.get_tally()[0][si],
                })

        matches = [obj.get_match(m) for m in prefixes]
        self.s1 = sum([1 if m._result[0] > m._result[1] and m.is_fixed() else 0 for m in matches])
        self.s2 = sum([1 if m._result[0] < m._result[1] and m.is_fixed() else 0 for m in matches])
        self.proba = sum(r['proba'] for r in self.outcomes)
        self.probb = sum(r['probb'] for r in self.outcomes)

        self.meanres = self.create_median_matches(obj, [(_('Matches'), prefixes)])
# }}}

# {{{ Proleage prediction view
@cache_page
def proleague(request):
    base = base_ctx('Inference', 'Predict', request=request)

    # {{{ Get data, set up and simulate
    form = SetupForm(request.GET)
    if not form.is_valid():
        return redirect('/inference/')

    result = ProleaguePredictionResult(
        dbpl=form.cleaned_data['ps'],
        bos=form.cleaned_data['bo'],
        args=request.GET,
    )
    # }}}

    # {{{ Post-processing
    base.update({
        's1':         result.s1,
        's2':         result.s2,
        'outcomes':   result.outcomes,
        'prob_draw':  result.prob_draw,
        'proba':      result.proba,
        'probb':      result.probb,
        'matches':    result.matches,
        'meanres':    result.meanres,
        'form':       form,
    })
    # }}}

    postable_proleague(base, request)

    return render_to_response('pred_proleague.djhtml', base)
# }}}

# }}}

# {{{ Postables

# {{{ Headers and footers
TL_HEADER = '[center][code]'
TL_SEBRACKET_MIDDLE = (
    '[/code][/center][b]%(medoutbr)s[/b]\n'
    '[spoiler][code]'
)
TL_SEBRACKET_FOOTER = (
    '[/code][/spoiler]\n'
    '[small]%(estby)s [url=http://aligulac.com/]Aligulac[/url]. '
    '[url=%(modurl)s]%(modify)s[/url].[/small]'
)
TL_FOOTER = (
    '[/code][/center]\n'
    '[small]%(estby)s [url=http://aligulac.com/]Aligulac[/url]. '
    '[url=%(modurl)s]%(modify)s[/url].[/small]'
)

REDDIT_HEADER = ''
REDDIT_FOOTER = '\n\n^(%(estby)s) [^Aligulac](http://aligulac.com/)^. [^%(modify)s](%(modurl)s)^.'
# }}}

# {{{ ordinal: Converts an integer to its ordinal (string) representation
def ordinal(value):
    return str(value)

    # If we find a way to make this translation-friendly then good.
    # Until then, this is how it'll be.
    # -- TheBB

    #try:
        #value = int(value)
    #except (TypeError, ValueError):
        #return value
    #suffixes = ('th', 'st', 'nd', 'rd', 'th', 'th', 'th', 'th', 'th', 'th')
    #if value % 100 in (11, 12, 13):
        #return "%d%s" % (value, suffixes[0])
    #return "%d%s" % (value, suffixes[value % 10])
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
        + ('\n\n{medout}: {pla} {sca}-{scb} {plb}'.format(
            medout=_('Median outcome'), pla=pla.name, sca=median[1], scb=median[2], plb=plb.name))
        + TL_FOOTER % {
              'modurl': request.build_absolute_uri(),
              'modify': _('Modify'),
              'estby': _('Estimated by'),
          }
    )

    base['postable_reddit'] = (
          REDDIT_HEADER 
        + left_center_right(strings, justify=False, indent=4) 
        + ('\n\n    {medout}: {pla} {sca}-{scb} {plb}'.format(
            medout=_('Median outcome'), pla=pla.name, sca=median[1], scb=median[2], plb=plb.name))
        + REDDIT_FOOTER % {
              'modurl': request.build_absolute_uri(),
              'modify': _('Modify'),
              'estby': _('Estimated by'),
          }
    )
# }}}

# {{{ postable_dual
def postable_dual(base, request):
    numlen = max([len(p['player']['tag']) for p in base['table'] if p['player']['id'] is not None])

    strings = (
        [('{s: >9}'.format(s=ugettext('Top 2')) + '{s: >9}'.format(s=ugettext('1st')) +
          '{s: >9}'.format(s=ugettext('2nd')) + '{s: >9}'.format(s=ugettext('3rd')) +
          '{s: >9}'.format(s=ugettext('4th')), '', ''), None] +
        [('{name: >{nl}}   {top2: >7.2f}% {p1: >7.2f}% {p2: >7.2f}% {p3: >7.2f}% {p4: >7.2f}%'.format(
            top2 = 100*(p['probs'][0]+p['probs'][1]),
            p1   = 100*p['probs'][0],
            p2   = 100*p['probs'][1],
            p3   = 100*p['probs'][2],
            p4   = 100*p['probs'][3],
            name = p['player']['tag'],
            nl   = numlen,
        ), '', '') for p in base['table']]
    )

    base['postable_tl'] = (
          TL_HEADER
        + left_center_right(strings, justify=False, gap=0)
        + TL_FOOTER % {
              'modurl': request.build_absolute_uri(),
              'modify': _('Modify'),
              'estby': _('Estimated by'),
          }
    )

    base['postable_reddit'] = (
          REDDIT_HEADER
        + left_center_right(strings, justify=False, gap=0, indent=4)
        + REDDIT_FOOTER % {
              'modurl': request.build_absolute_uri(),
              'modify': _('Modify'),
              'estby': _('Estimated by'),
          }
    )
# }}}

# {{{ postable_sebracket
def postable_sebracket(base, request, bracket):
    numlen = max([len(p['player']['tag']) for p in base['table'] if p['player']['id'] is not None])

    strings = [(''.join(
        # Translators: Win a tournament
        ['{s: >9}'.format(s=ugettext('Win'))] + 
        # Translators: Top 2, 4 etc. (in tournament)
        ['{s: >9}'.format(s=ugettext('Top {i}').format(i=2**rnd))
         for rnd in range(1, int(log(len(base['table']),2)) + 1)]
    ), '', ''), None]

    for p in base['table']:
        if p['player']['id'] is None:
            continue
        strings.append((''.join(
            ['{name: >{nl}}  '.format(name=p['player']['tag'], nl=numlen)] +
            [' {p: >7.2f}%'.format(p=100*t) for t in p['probs']]
        ), '', ''))

    base['postable_tl'] = (
          TL_HEADER
        + left_center_right(strings, justify=False, gap=0)
        + TL_SEBRACKET_MIDDLE % {'medoutbr': _('Median Outcome Bracket')}
        + create_postable_bracket(bracket)
        + TL_SEBRACKET_FOOTER % {
              'modurl': request.build_absolute_uri(),
              'modify': _('Modify'),
              'estby': _('Estimated by'),
          }
    )

    base['postable_reddit'] = (
          REDDIT_HEADER
        + left_center_right(strings, justify=False, gap=0, indent=4)
        + REDDIT_FOOTER % {
              'modurl': request.build_absolute_uri(),
              'modify': _('Modify'),
              'estby': _('Estimated by'),
          }
    )

    base['postable_bracket_reddit'] = (
          REDDIT_HEADER
        + create_postable_bracket(bracket, indent=4)
        + REDDIT_FOOTER % {
              'modurl': request.build_absolute_uri(),
              'modify': _('Modify'),
              'estby': _('Estimated by'),
          }
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
            pla = m['pla']['tag']
            plascore = m['pla']['score']
            plb = m['plb']['tag']
            plbscore = m['plb']['score']

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
        final['pla']['tag'] 
        if final['pla']['score'] > final['plb']['score'] 
        else final ['plb']['tag']
    ))

    postable_result = ''
    for line in range(len(result[0])):
        postable_result += ' '*indent + ''.join(block[line] for block in result if line < len(block)) + '\n'

    return postable_result.rstrip()
# }}}

# {{{ postable_rrgroup
def postable_rrgroup(base, request):
    numlen = max([len(p['player']['tag']) for p in base['table']])

    strings = [(''.join([
        ('{s: <9}'.format(s=ordinal(i+1)) if i < len(base['table'])-1 else ordinal(i+1))
        for i in range(0, len(base['table']))
    ]), '', ''), None]

    for p in base['table']:
        strings.append((''.join(
            ['{name: >{nl}}  '.format(name=p['player']['tag'], nl=numlen)] +
            [' {p: >7.2f}%'.format(p=100*t) for t in p['probs']]
        ), '', ''))

    base['postable_tl'] = (
          TL_HEADER
        + left_center_right(strings, justify=False, gap=0)
        + TL_FOOTER % {
              'modurl': request.build_absolute_uri(),
              'modify': _('Modify'),
              'estby': _('Estimated by'),
          }
    )

    base['postable_reddit'] = (
          REDDIT_HEADER
        + left_center_right(strings, justify=False, gap=0, indent=4)
        + REDDIT_FOOTER % {
              'modurl': request.build_absolute_uri(),
              'modify': _('Modify'),
              'estby': _('Estimated by'),
          }
    )
# }}}

# {{{ postable_proleague
def postable_proleague(base, request):
    numlen = len(str((len(base['matches']) + 1) // 2))
    strings = [(
        # Translators: Team [player], e.g. "Team Jaedong"
        ugettext('Team {p}').format(p=base['matches'][0]['pla']['tag']),
        '{sca: >{nl}}-{scb: <{nl}}'.format(sca=base['s1'], scb=base['s2'], nl=numlen),
        ugettext('Team {p}').format(p=base['matches'][0]['plb']['tag']),
    ), None]

    for r in base['outcomes']:
        if r['proba'] == 0.0 and r['probb'] == 0.0:
            continue
        L = ('{pctg: >6.2f}% {sca}-{scb: >{nl}}'.format(
            pctg=100*r['proba'], sca=r['winner'], scb=r['loser'], nl=numlen
        ) if r['proba'] > 0.0 else '')
        R = ('{sca: >{nl}}-{scb} {pctg: >6.2f}%'.format(
            pctg=100*r['probb'], sca=r['loser'], scb=r['winner'], nl=numlen
        ) if r['probb'] > 0.0 else '')
        strings.append((L, '', R))

    strings += [None, (
        '{pctg: >6.2f}%'.format(pctg=100*base['proba']),
        '{pctg: >6.2f}%'.format(pctg=100*base['prob_draw']) if base['prob_draw'] > 0.0 else '',
        '{pctg: >6.2f}%'.format(pctg=100*base['probb']),
    )]

    base['postable_tl'] = (
          TL_HEADER
        + left_center_right(strings)
        + TL_FOOTER % {
              'modurl': request.build_absolute_uri(),
              'modify': _('Modify'),
              'estby': _('Estimated by'),
          }
    )

    base['postable_reddit'] = (
          REDDIT_HEADER 
        + left_center_right(strings, justify=False, indent=4) 
        + REDDIT_FOOTER % {
              'modurl': request.build_absolute_uri(),
              'modify': _('Modify'),
              'estby': _('Estimated by'),
          }
    )
# }}}

# }}}
