# {{{ Imports
from datetime import (
    datetime,
    date,
)
import operator
import shlex

import ccy

from django import forms
from django.db.models import (
    Count,
    Min,
    Max,
    Sum,
    Q,
    F,
)
from django.http import HttpResponse
from django.shortcuts import (
    redirect,
    render_to_response,
    get_object_or_404,
)
from django.template import RequestContext
from django.views.decorators.csrf import csrf_protect

from aligulac.cache import cache_page
from aligulac.tools import (
    base_ctx,
    etn,
    generate_messages,
    get_param,
    Message,
    NotUniquePlayerMessage,
    StrippedCharField,
)

from ratings.models import (
    CAT_FREQUENT,
    CAT_INDIVIDUAL,
    CAT_TEAM,
    Earnings,
    Event,
    EVENT_TYPES,
    GAMES,
    Match,
    Player,
    Story,
    TLPD_DBS,
    TYPE_CATEGORY,
    TYPE_EVENT,
    TYPE_ROUND,
)
from ratings.tools import (
    count_matchup_games,
    count_mirror_games,
    count_winloss_games,
    display_matches,
    filter_flags,
    find_player,
)
# }}}

# {{{ collect: Auxiliary function for reducing a list to a list of tuples (reverse concat)
def collect(lst, n=2):
    ret = []
    while len(lst) > 0:
        ret.append(lst[:n])
        lst = lst[n:]

    ret[-1] = ret[-1] + [None] * (n-len(ret[-1]))

    return ret
# }}}

# {{{ earnings_code: Converts a queryset of earnings to the corresponding code.
def earnings_code(queryset):
    if not queryset.exists():
        return '[prize] [player]'
    return '\n'.join(['%i %s %i' % (e.origearnings, e.player.tag, e.player_id) for e in queryset])
# }}}

# {{{ EventModForm: Form for modifying an event.
class EventModForm(forms.Form):
    name       = StrippedCharField(max_length=100, required=True, label='Name')
    date       = forms.DateField(required=False, label='Date')
    game       = forms.ChoiceField(choices=[('nochange','No change')]+GAMES, required=True, label='Game')
    offline    = forms.ChoiceField(
        choices=[('nochange','No change'), ('online','Online'), ('offline','Offline')],
        required=True, label='On/offline'
    )
    type       = forms.ChoiceField(choices=[('nochange','No change')]+EVENT_TYPES, required=True, label='Type')
    same_level = forms.BooleanField(required=False, label='Apply to all events on the same level')
    homepage   = StrippedCharField(max_length=200, required=False, label='Homepage')
    tlpd_id    = forms.IntegerField(required=False, label='TLPD ID')
    tlpd_db    = forms.MultipleChoiceField(
        required=False, choices=TLPD_DBS, label='TLPD DB', widget=forms.CheckboxSelectMultiple)
    tl_thread  = forms.IntegerField(required=False, label='TL thread')
    lp_name    = StrippedCharField(max_length=200, required=False, label='Liquipedia title')

    # {{{ Constructor
    def __init__(self, request=None, event=None):
        if request is not None:
            super(EventModForm, self).__init__(request.POST)
        else:
            super(EventModForm, self).__init__(initial={
                'name': event.name,
                'date': None,
                'game': 'nochange',
                'offline': 'nochange',
                'type': event.type,
                'same_level': False,
                'homepage': event.homepage,
                'tlpd_id': event.tlpd_id,
                'tlpd_db': filter_flags(event.tlpd_db if event.tlpd_db else 0),
                'tl_thread': event.tl_thread,
                'lp_name': event.lp_name,
            })

        self.label_suffix = ''
    # }}}

    # {{{ update_event: Pushes updates to event, responds with messages
    def update_event(self, event):
        ret = []

        if not self.is_valid():
            ret.append(Message('Entered data was invalid, no changes made.', type=Message.ERROR))
            for field, errors in self.errors.items():
                for error in errors:
                    ret.append(Message(error=error, field=self.fields[field].label))
            return ret

        if self.cleaned_data['name'] != event.name:
            event.update_name(self.cleaned_data['name'])
            for e in event.get_children(id=False):
                e.update_name()
            ret.append(Message('Changed event name.', type=Message.SUCCESS))

        if self.cleaned_data['date'] is not None:
            nchanged = event.get_matchset().update(date=self.cleaned_data['date'])
            ret.append(Message('Changed date for %i matches.' % nchanged, type=Message.SUCCESS))

        if self.cleaned_data['game'] != 'nochange':
            nchanged = event.get_matchset().update(game=self.cleaned_data['game'])
            ret.append(Message('Changed game for %i matches.' % nchanged, type=Message.SUCCESS))

        if self.cleaned_data['offline'] != 'nochange':
            nchanged = event.get_matchset().update(offline=(self.cleaned_data['offline']=='offline'))
            ret.append(Message('Changed type for %i matches.' % nchanged, type=Message.SUCCESS))

        events = [event] if not self.cleaned_data['same_level'] else event.event_set.all()
        for e in events:
            nchanged = 0
            if e.type != self.cleaned_data['type']:
                e.change_type(self.cleaned_data['type'])
                nchanged += 1
            if nchanged > 0:
                ret.append(Message('Changed type for %i event(s).' % nchanged, type=Message.SUCCESS))

        def update(value, attr, setter, label):
            if value != getattr(event, attr):
                getattr(event, setter)(value)
                ret.append(Message('Changed %s.' % label, type=Message.SUCCESS))

        update(self.cleaned_data['homepage'],   'homepage',   'set_homepage',   'homepage')
        update(self.cleaned_data['tlpd_id'],    'tlpd_id',    'set_tlpd_id',    'TLPD ID')
        update(self.cleaned_data['lp_name'],    'lp_name',    'set_lp_name',    'Liquipedia title')
        update(self.cleaned_data['tl_thread'],  'tl_thread',  'set_th_thread',  'TL thread')
        update(sum([int(a) for a in self.cleaned_data['tlpd_db']]), 'tlpd_db', 'set_tlpd_db', 'TLPD DBs')

        return ret
    # }}}
# }}} 

# {{{ PrizepoolModForm: Form for changing prizepools.
class PrizepoolModForm(forms.Form):
    sorted_curs = sorted(ccy.currencydb(), key=operator.itemgetter(0))
    currencies  = [(ccy.currency(c).code, ccy.currency(c).name) for c in sorted_curs]
    currency    = forms.ChoiceField(choices=currencies, required=True, label='Currency')
    ranked      = forms.CharField(required=False, max_length=10000, label='Ranked')
    unranked    = forms.CharField(required=False, max_length=10000, label='Unranked')

    # {{{ Constructor
    def __init__(self, request=None, event=None):
        if request is not None:
            super(PrizepoolModForm, self).__init__(request.POST)
        else:
            initial = {
                'ranked':   earnings_code(event.earnings_set.filter(placement__gt=0).order_by('-earnings')),
                'unranked': earnings_code(event.earnings_set.filter(placement=0).order_by('-earnings')),
            }

            try:
                initial['currency'] = event.earnings_set.all().first().currency
            except:
                initial['currency'] = 'USD'

            super(PrizepoolModForm, self).__init__(initial=initial)

        self.label_suffix = ''
    # }}}

    # {{{ Function for parsing a single line
    def line_to_data(self, line):
        ind = line.find(' ')
        prize = int(line[:ind])

        queryset = find_player(query=line[ind+1:])
        if not queryset.exists():
            raise Exception("No such player: '%s'." % line[ind+1:])
        elif queryset.count() > 1:
            raise Exception("Unamiguous player: '%s'." % line[ind+1:])
        else:
            return prize, queryset.first()
    # }}}

    # {{{ update_event: Pushes changes to event object
    def update_event(self, event):
        ret = []

        if not self.is_valid():
            ret.append(Message('Entered data was invalid, no changes made.', type=Message.ERROR))
            for field, errors in self.errors.items():
                for error in errors:
                    ret.append(Message(error=error, field=self.fields[field].label))
            return ret

        # {{{ Gather data
        ranked, unranked, ok = [], [], True

        for line in self.cleaned_data['ranked'].split('\n'):
            if line.strip() == '':
                continue
            try:
                prize, player = self.line_to_data(line)
                ranked.append({'prize': prize, 'player': player, 'placement': 0})
            except Exception as e:
                ret.append(Message(str(e), type=Message.ERROR))
                ok = False

        for line in self.cleaned_data['unranked'].split('\n'):
            if line.strip() == '':
                continue
            try:
                prize, player = self.line_to_data(line)
                unranked.append({'prize': prize, 'player': player, 'placement': -1})
            except Exception as e:
                ret.append(Message(str(e), type=Message.ERROR))
                ok = False

        if not ok:
            ret.append(Message('Errors occured, no changes made.', type=Message.ERROR))
            return ret
        # }}}

        # {{{ Fix placements of ranked prizes
        ranked.sort(key=lambda a: a['placement'])
        for i, e in enumerate(ranked):
            ranked[i]['placement'] = i
        # }}}

        # {{{ Commit
        Earnings.set_earnings(event, ranked,   self.cleaned_data['currency'], True)
        Earnings.set_earnings(event, unranked, self.cleaned_data['currency'], False)
        # }}}

        ret.append(Message('New prizes committed.', type=Message.SUCCESS))

        return ret
    # }}}
# }}}

# {{{ StoryModForm: Form for adding stories.
class StoryModForm(forms.Form):
    player = forms.ChoiceField(required=True, label='Player')
    date   = forms.DateField(required=True, label='Date')
    text   = StrippedCharField(max_length=200, required=True, label='Text')

    # {{{ Constructor
    def __init__(self, request=None, event=None):
        if request is not None:
            super(StoryModForm, self).__init__(request.POST)
        else:
            super(StoryModForm, self).__init__(initial={'date': event.latest})

        matches = event.get_immediate_matchset()
        players = Player.objects.filter(Q(id__in=matches.values('pla')) | Q(id__in=matches.values('plb')))
        self.fields['player'].choices = [(str(p.id), str(p)) for p in players]

        self.label_suffix = ''

        self.existing_stories = Player.objects.filter(story__event=event)
    # }}}

    # {{{ update_event: Pushes changes
    def update_event(self, event):
        ret = []

        if not self.is_valid():
            ret.append(Message('Entered data was invalid, no changes made.', type=Message.ERROR))
            for field, errors in self.errors.items():
                for error in errors:
                    ret.append(Message(error=error, field=self.fields[field].label))
            return ret

        story = Story(
            event=event,
            player_id=self.cleaned_data['player'],
            date=self.cleaned_data['date'],
            text=self.cleaned_data['text'],
        )
        story.save()

        ret.append(Message('Added a story.', type=Message.SUCCESS))

        return ret
    # }}}
# }}}

# {{{ AddForm: Form for adding subevents.
class AddForm(forms.Form):
    name    = StrippedCharField(max_length=100, required=True, label='Name')
    type    = forms.ChoiceField(choices=EVENT_TYPES, required=True, label='Type')
    noprint = forms.BooleanField(required=False, label='No Print')
    closed  = forms.BooleanField(required=False, label='Closed')

    # {{{ Constructor
    def __init__(self, request=None, event=None):
        if request is not None:
            super(AddForm, self).__init__(request.POST)
        else:
            super(AddForm, self).__init__(initial={
                'type': TYPE_EVENT if event.type == TYPE_CATEGORY else TYPE_ROUND,
                'noprint': False,
                'closed': event.closed
            })

        self.label_suffix = ''
    # }}}

    # {{{ update_event: Pushes changes
    def update_event(self, event):
        ret = []

        if not self.is_valid():
            ret.append(Message('Entered data was invalid, no changes made.', type=Message.ERROR))
            for field, errors in self.errors.items():
                for error in errors:
                    ret.append(Message(error=error, field=self.fields[field].label))
            return ret

        event.add_child(
            self.cleaned_data['name'],
            self.cleaned_data['type'],
            self.cleaned_data['noprint'],
            self.cleaned_data['closed'],
        )

        ret.append(Message('Added a subevent.', type=Message.SUCCESS))

        return ret
    # }}}
# }}}

# {{{ SearchForm: Form for searching.
class SearchForm(forms.Form):
    after      = forms.DateField(required=False, label='After', initial=None)
    before     = forms.DateField(required=False, label='Before', initial=None)
    players    = forms.CharField(max_length=10000, required=False, label='Involving players', initial='')
    event      = StrippedCharField(max_length=200, required=False, label='Event', initial='')
    unassigned = forms.BooleanField(required=False, label='Only show unassigned matches')
    bestof     = forms.ChoiceField(
        choices=[
            ('all','All'),
            ('3','Best of 3+'),
            ('5','Best of 5+'),
        ],
        required=False, label='Match format', initial='all'
    )
    offline = forms.ChoiceField(
        choices=[
            ('both','Both'),
            ('offline','Offline'),
            ('online','Online'),
        ],
        required=False, label='On/offline', initial='both',
    )
    game = forms.ChoiceField(
        choices=[('all','All')]+GAMES, required=False, label='Game version', initial='all')

    # {{{ Constructor
    def __init__(self, request=None):
        if request is not None:
            super(SearchForm, self).__init__(request.GET)
        else:
            super(SearchForm, self).__init__()

        self.label_suffix = ''
    # }}}

    # {{{ search: Performs a search, returns a dict with results to be added to the rendering context
    def search(self, adm):
        # {{{ Check validity (lol)
        if not self.is_valid():
            msgs = []
            msgs.append(Message('Entered data was invalid, no changes made.', type=Message.ERROR))
            for field, errors in self.errors.items():
                for error in errors:
                    msgs.append(Message(error=error, field=self.fields[field].label))
            return {'messages': msgs}
        # }}}

        matches = (
            Match.objects.all().prefetch_related('message_set')
                .select_related('pla','plb','period')
                .annotate(Count('eventobj__match'))
        )

        # {{{ All the easy filtering
        if self.cleaned_data['after'] is not None:
            matches = matches.filter(date__gte=self.cleaned_data['after'])

        if self.cleaned_data['before'] is not None:
            matches = matches.filter(date__gte=self.cleaned_data['before'])

        if self.cleaned_data['unassigned'] and adm:
            matches = matches.filter(eventobj__isnull=True)

        if self.cleaned_data['bestof'] == '3':
            matches = matches.filter(Q(sca__gte=2) | Q(scb__gte=2))
        elif self.cleaned_data['bestof'] == '5':
            matches = matches.filter(Q(sca__gte=3) | Q(scb__gte=3))

        if self.cleaned_data['offline'] != 'both':
            matches = matches.filter(offline=(self.cleaned_data['offline']=='offline'))

        if self.cleaned_data['game'] != 'all':
            matches = matches.filter(game=self.cleaned_data['game'])
        # }}}

        # {{{ Filter by event
        if self.cleaned_data['event'] != None:
            queries = [s.strip() for s in shlex.split(self.cleaned_data['event']) if s.strip() != '']
            for q in queries:
                matches = matches.filter(
                    Q(eventobj__isnull=True, event__icontains=query) |\
                    Q(eventobj__isnull=False, eventobj__fullname__icontains=query)
                )
        # }}}

        ret = {'messages': []}

        # {{{ Filter by players
        lines = self.cleaned_data['players'].splitlines()
        lineno, ok, players = -1, True, []
        for line in lines:
            lineno += 1
            if line.strip() == '':
                continue

            pls = find_player(query=line, make=False)
            if not pls.exists():
                ret['messages'].append(Message("No matches found: '%s'." % line.strip(), type=Message.ERROR))
                ok = False
            else:
                if pls.count() > 1:
                    ret['messages'].append(NotUniquePlayerMessage(
                        line.strip(), pls, update=self['players'].auto_id,
                        updateline=lineno, type=Message.WARNING
                    ))

                players.append(list(pls))

        if not ok:
            return ret

        pls = []
        for p in players:
            pls += p

        if len(pls) > 1:
            matches = matches.filter(pla__in=pls, plb__in=pls)
        elif len(pls) == 1:
            matches = matches.filter(Q(pla__in=pls) | Q(plb__in=pls))
        # }}}

        # {{{ Collect data
        ret['count'] = matches.count()
        if ret['count'] > 1000:
            ret['messages'].append(Message(
                'Too many results (%i). Please add restrictions.' % ret['count'],
                type=Message.ERROR
            ))
            return ret

        matches = matches.order_by('-date', 'eventobj__lft', 'event', 'id')
        if 1 <= len(pls) <= 2:
            ret['matches'] = display_matches(matches, date=True, fix_left=pls[0], eventcount=True)
            ret['sc_my'], ret['sc_op'] = (
                sum([m['pla_score'] for m in ret['matches']]),
                sum([m['plb_score'] for m in ret['matches']]),
            )
            ret['msc_my'], ret['msc_op'] = (
                sum([1 if m['pla_score'] > m['plb_score'] else 0 for m in ret['matches']]),
                sum([1 if m['plb_score'] > m['pla_score'] else 0 for m in ret['matches']]),
            )
            ret['left'] = pls[0]
            if len(pls) == 2:
                ret['right'] = pls[1]
        else:
            ret['matches'] = display_matches(matches, date=True, eventcount=True)

        return ret
        # }}}
    # }}}
# }}}

# {{{ ResultsModForm: Form for modifying search results.
class ResultsModForm(forms.Form):
    event   = forms.ChoiceField(required=True, label='Event')
    date    = forms.DateField(required=False, label='Date', initial=None)
    offline = forms.ChoiceField(
        choices=[('nochange','No change'), ('online','Online'), ('offline','Offline')],
        required=True, label='On/offline', initial='nochange'
    )
    game = forms.ChoiceField(
        choices=[('nochange','No change')]+GAMES,
        required=True, label='Game version', initial='nochange'
    )

    # {{{ Constructor
    def __init__(self, request=None):
        if request is not None:
            super(ResultsModForm, self).__init__(request.POST)
        else:
            super(ResultsModForm, self).__init__()

        self.fields['event'].choices = [(0, 'No change')] + [
            (e['id'], e['fullname']) for e in (
                Event.objects.filter(closed=False, rgt=F('lft')+1).order_by('lft').values('id','fullname')
            )
        ]
    # }}}

    # {{{ modify: Commits modifications
    def modify(self, ids):
        ret = []

        if not self.is_valid():
            ret.append(Message('Entered data was invalid, no changes made.', type=Message.ERROR))
            for field, errors in self.errors.items():
                for error in errors:
                    ret.append(Message(error=error, field=self.fields[field].label))
            return ret

        print(ids)
        matches = Match.objects.filter(id__in=ids)

        if self.cleaned_data['event'] != 0:
            try:
                event = Event.objects.get(id=self.cleaned_data['event'])
                matches.update(eventobj=event)
            except:
                pass

        if self.cleaned_data['date'] != None:
            matches.update(date=self.cleaned_data['date'])

        if self.cleaned_data['offline'] != 'nochange':
            matches.update(offline=(self.cleaned_data['offline']=='offline'))

        if self.cleaned_data['game'] != 'nochange':
            matches.update(game=self.cleaned_data['game'])

        return [Message('Updated %i matches.' % matches.count(), type=Message.SUCCESS)]
    # }}}
# }}}

# {{{ results view
@cache_page
def results(request):
    base = base_ctx('Results', 'By Date', request)

    try:
        day = datetime.strptime(get_param(request, 'd', None), '%Y-%m-%d').date()
    except:
        day = date.today()

    bounds = Match.objects.aggregate(Min('date'), Max('date'))
    day = min(max(bounds['date__min'], day), bounds['date__max'])
    base.update({
        'mindate': bounds['date__min'],
        'maxdate': bounds['date__max'],
        'td':      day,
    })

    matches = (
        Match.objects.filter(date=day).order_by('eventobj__lft', 'event', 'id')
            .prefetch_related('message_set')
            .select_related('rta', 'rtb')
            .annotate(Count('eventobj__match'))
    )
    base['matches'] = display_matches(matches, date=False, ratings=True, messages=True, eventcount=True)

    return render_to_response('results.html', base)
# }}}

# {{{ events view
@cache_page
@csrf_protect
def events(request, event_id=None):
    # {{{ Get base context, redirect if necessary
    if 'goto' in request.GET:
        return redirect('/results/events/' + request.GET['goto'])

    base = base_ctx('Results', 'By Event', request)
    # }}}

    # {{{ Display the main table if event ID is not given
    if event_id is None:
        root_events = (
            Event.objects.filter(parent__isnull=True).prefetch_related('event_set').order_by('lft')
        )
        base.update({
            'ind_bigs':    collect(root_events.filter(big=True, category=CAT_INDIVIDUAL), 2),
            'ind_smalls':  root_events.filter(big=False, category=CAT_INDIVIDUAL).order_by('name'),
            'team_bigs':   collect(root_events.filter(big=True, category=CAT_TEAM), 2),
            'team_smalls': root_events.filter(big=False, category=CAT_TEAM).order_by('name'),
            'freq_bigs':   collect(root_events.filter(big=True, category=CAT_FREQUENT), 2),
            'freq_smalls': root_events.filter(big=False, category=CAT_FREQUENT).order_by('name'),
        })

        return render_to_response('events.html', base)
    # }}}

    # {{{ Get object, generate messages, and ensure big is set. Find familial relationships.
    event = get_object_or_404(Event, id=event_id)
    base['messages'] += generate_messages(event)

    matches = event.get_matchset()
    if matches.count() > 200 and not event.big:
        event.set_big(True)

    base.update({
        'event':             event,
        'siblings':          event.parent.event_set.exclude(id=event.id) if event.parent else None,
        'path':              event.get_ancestors(id=True),
        'children':          event.event_set.all(),
        'surroundingevents': event.parent.event_set.exclude(lft__lte=event.lft, rgt__lte=event.rgt),
    })
    # }}}

    # {{{ Make forms
    if base['adm']:
        def check_form(formname, cl, check):
            if request.method == 'POST' and check in request.POST:
                f = cl(request=request, event=event)
                base['messages'] += f.update_event(event)
            else:
                f = cl(event=event)
            base[formname] = f

        check_form('form', EventModForm, 'modevent')
        check_form('addform', AddForm, 'addevent')
        if event.type == TYPE_EVENT:
            check_form('ppform', PrizepoolModForm, 'modpp')
        if not event.has_children() and event.get_immediate_matchset().exists():
            check_form('stform', StoryModForm, 'modstories')
    # }}}

    # {{{ Prizepool information for the public
    total_earnings = Earnings.objects.filter(event__lft__gte=event.lft, event__rgt__lte=event.rgt)
    currencies = [r['currency'] for r in total_earnings.values('currency').distinct()]
    base.update({
        'prizepool':     total_earnings.aggregate(Sum('earnings'))['earnings__sum'],
        'nousdpp':       len(currencies) > 1 or len(currencies) == 1 and currencies[0] != 'USD',
        'prizepoolorig': [{
            'pp':  total_earnings.filter(currency=k).aggregate(Sum('origearnings'))['origearnings__sum'],
            'cur': k,
        } for k in currencies],
    })
    # }}}

    # {{{ Other easy statistics
    base.update({
        'game':      etn(lambda: dict(Match.GAMES)[matches.values('game').distinct()[0]['game']]),
        'offline':   etn(lambda: matches.values('offline').distinct()[0]['offline']),
        'nmatches':  matches.count(),
        'ngames':    sum(count_winloss_games(matches)),
        'pvp_games': count_mirror_games(matches, 'P'),
        'tvt_games': count_mirror_games(matches, 'T'),
        'zvz_games': count_mirror_games(matches, 'Z'),
        'matches':   display_matches(
            matches.prefetch_related('message_set')
                .select_related('pla', 'plb', 'eventobj')
                .annotate(Count('eventobj__match'))
                .order_by('-eventobj__lft', '-date', '-id')[0:200],
            eventcount=True,
        ),
        'nplayers':  Player.objects.filter(
            Q(id__in=matches.values('pla')) | Q(id__in=matches.values('plb'))
        ).count(),
    })

    base['pvt_wins'], base['pvt_loss'] = count_matchup_games(matches, 'P', 'T')
    base['pvz_wins'], base['pvz_loss'] = count_matchup_games(matches, 'P', 'Z')
    base['tvz_wins'], base['tvz_loss'] = count_matchup_games(matches, 'T', 'Z')
    # }}}

    return render_to_response('eventres.html', base)
# }}}

# {{{ search view
@cache_page
@csrf_protect
def search(request):
    base = base_ctx('Results', 'Search', request)

    # {{{ Filtering and modifying
    if base['adm']:
        if request.method == 'POST':
            modform = ResultsModForm(request=request)
            print(request.POST)
            base['messages'] += modform.modify([
                int(k.split('-')[-1]) for k in request.POST if 'y' in request.POST[k] and k[0:6] == 'match-'
            ])
        else:
            modform = ResultsModForm()
        base['modform'] = modform

    if 'search' in request.GET:
        searchform = SearchForm(request=request)
        q = searchform.search(base['adm'])
        base['messages'] += q['messages']
        del q['messages']
        base.update(q)
    else:
        searchform = SearchForm()
    base['searchform'] = searchform
    # }}}

    return render_to_response('results_search.html', base, context_instance=RequestContext(request))
# }}}
