from datetime import datetime, date
import operator

import ccy

from django import forms
from django.db.models import Min, Max, Sum, Q
from django.http import HttpResponse
from django.shortcuts import render_to_response, get_object_or_404, redirect
from django.views.decorators.csrf import csrf_protect

from aligulac.cache import cache_page
from aligulac.tools import get_param, base_ctx, StrippedCharField, generate_messages, Message, etn

from ratings.models import Earnings, Event, Match, Player, Story
from ratings.tools import (display_matches, count_winloss_games, count_matchup_games, count_mirror_games,
                           filter_flags, find_player)

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
    name = StrippedCharField(max_length=100, required=True, label='Name')
    date = forms.DateField(required=False, label='Date')
    game = forms.ChoiceField(choices=[('nochange','No change')]+Match.GAMES, required=True, label='Game')
    offline = forms.ChoiceField(
        choices=[('nochange','No change'), ('online','Online'), ('offline','Offline')],
        required=True, label='Offline'
    )
    type = forms.ChoiceField(choices=[('nochange','No change')]+Event.TYPES, required=True, label='Type')
    same_level = forms.BooleanField(required=False, label='Apply to all events on the same level')
    homepage = StrippedCharField(max_length=200, required=False, label='Homepage')
    tlpd_id = forms.IntegerField(required=False, label='TLPD ID')
    tlpd_db = forms.MultipleChoiceField(
        required=False, choices=Event.TLPD_DBS, label='TLPD DB', widget=forms.CheckboxSelectMultiple)
    tl_thread = forms.IntegerField(required=False, label='TL thread')
    lp_name = StrippedCharField(max_length=200, required=False, label='Liquipedia title')

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

        update(self.cleaned_data['homepage'], 'homepage', 'set_homepage', 'homepage')
        update(self.cleaned_data['tlpd_id'], 'tlpd_id', 'set_tlpd_id', 'TLPD ID')
        update(sum([int(a) for a in self.cleaned_data['tlpd_db']]), 'tlpd_db', 'set_tlpd_db', 'TLPD DBs')
        update(self.cleaned_data['lp_name'], 'lp_name', 'set_lp_name', 'Liquipedia title')
        update(self.cleaned_data['tl_thread'], 'tl_thread', 'set_th_thread', 'TL thread')

        return ret
    # }}}
# }}} 

# {{{ PrizepoolModForm: Form for changing prizepools.
class PrizepoolModForm(forms.Form):
    sorted_curs = sorted(ccy.currencydb(), key=operator.itemgetter(0))
    currencies = [(ccy.currency(c).code, ccy.currency(c).name) for c in sorted_curs]
    currency = forms.ChoiceField(choices=currencies, required=True, label='Currency')
    ranked = forms.CharField(required=False, max_length=10000, label='Ranked')
    unranked = forms.CharField(required=False, max_length=10000, label='Unranked')

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
        Earnings.set_earnings(event, ranked, self.cleaned_data['currency'], True)
        Earnings.set_earnings(event, unranked, self.cleaned_data['currency'], False)
        # }}}

        ret.append(Message('New prizes committed.', type=Message.SUCCESS))

        return ret
    # }}}
# }}}

# {{{ StoryModForm: Form for adding stories.
class StoryModForm(forms.Form):
    player = forms.ChoiceField(required=True, label='Player')
    date = forms.DateField(required=True, label='Date')
    text = StrippedCharField(max_length=200, required=True, label='Text')

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
    name = StrippedCharField(max_length=100, required=True, label='Name')
    type = forms.ChoiceField(choices=Event.TYPES, required=True, label='Type')
    noprint = forms.BooleanField(required=False, label='No Print')
    closed = forms.BooleanField(required=False, label='Closed')

    # {{{ Constructor
    def __init__(self, request=None, event=None):
        if request is not None:
            super(AddForm, self).__init__(request.POST)
        else:
            super(AddForm, self).__init__(initial={
                'type': Event.TYPE_EVENT if event.type == Event.TYPE_CATEGORY else Event.TYPE_ROUND,
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

    matches = Match.objects.filter(date=day).order_by('eventobj__lft', 'event', 'id')\
                   .prefetch_related('message_set')
    base['matches'] = display_matches(matches, date=False, ratings=True, messages=True)

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
        root_events = Event.objects.filter(parent__isnull=True)\
                           .prefetch_related('event_set')\
                           .order_by('lft')
        base.update({
            'ind_bigs':    collect(root_events.filter(big=True, category=Event.CAT_INDIVIDUAL), 2),
            'ind_smalls':  root_events.filter(big=False, category=Event.CAT_INDIVIDUAL).order_by('name'),
            'team_bigs':   collect(root_events.filter(big=True, category=Event.CAT_TEAM), 2),
            'team_smalls': root_events.filter(big=False, category=Event.CAT_TEAM).order_by('name'),
            'freq_bigs':   collect(root_events.filter(big=True, category=Event.CAT_FREQUENT), 2),
            'freq_smalls': root_events.filter(big=False, category=Event.CAT_FREQUENT).order_by('name'),
        })

        return render_to_response('events.html', base)
    # }}}

    # {{{ Get object, generate messages, make forms and ensure big is set. Find familial relationships.
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
        if event.type == Event.TYPE_EVENT:
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
                            'pp':  total_earnings.filter(currency=k)\
                                                 .aggregate(Sum('origearnings'))['origearnings__sum'],
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
        'matches':   display_matches(matches.prefetch_related('message_set')\
                                            .select_related('pla', 'plb', 'eventobj')\
                                            .order_by('-eventobj__lft', '-date', '-id')[0:200]),
        'nplayers':  Player.objects.filter(
                         Q(id__in=matches.values('pla')) | Q(id__in=matches.values('plb'))).count(),
    })

    base['pvt_wins'], base['pvt_loss'] = count_matchup_games(matches, 'P', 'T')
    base['pvz_wins'], base['pvz_loss'] = count_matchup_games(matches, 'P', 'Z')
    base['tvz_wins'], base['tvz_loss'] = count_matchup_games(matches, 'T', 'Z')
    # }}}

    return render_to_response('eventres.html', base)
# }}}
