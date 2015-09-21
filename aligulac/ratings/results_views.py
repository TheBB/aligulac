# {{{ Imports
from datetime import (
    datetime,
    date,
)
from decimal import Decimal
from itertools import groupby
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
from django.utils.translation import ugettext_lazy as _
from django.utils.translation import ungettext_lazy
import itertools

from aligulac.cache import cache_page
from aligulac.tools import (
    base_ctx,
    cache_login_protect,
    etn,
    generate_messages,
    get_param,
    Message,
    NotUniquePlayerMessage,
    StrippedCharField,
)

from currency import RateNotFoundError

from ratings.models import (
    ArchonMatch,
    CAT_FREQUENT,
    CAT_INDIVIDUAL,
    CAT_TEAM,
    Earnings,
    Event,
    EVENT_TYPES,
    GAMES,
    Match,
    Player,
    STORIES,
    Story,
    TLPD_DBS,
    TYPE_CATEGORY,
    TYPE_EVENT,
    TYPE_ROUND,
    WCSPoints,
    WCS_TIERS,
    WCS_YEARS,
)
from ratings.tools import (
    currency_strip,
    count_matchup_games,
    count_mirror_games,
    count_winloss_games,
    display_matches,
    filter_flags,
    find_player,
    get_placements
)
# }}}

# {{{ earnings_code, wcs_points_code: Converts a queryset of earnings or
# wcs points to the corresponding code.
def earnings_code(queryset):
    if not queryset.exists():
        return ''
    return '\n'.join([
        '{} {} {}'.format(currency_strip(e.origearnings), 
                          e.player.tag, 
                          e.player_id) 
        for e in queryset
    ])

def wcs_points_code(queryset):
    if not queryset.exists():
        return ''
    return '\n'.join([
        '{} {} {}'.format(e.points, e.player.tag, e.player_id)
        for e in queryset
    ])
# }}}

# {{{ EventModForm: Form for modifying an event.
class EventModForm(forms.Form):
    name       = StrippedCharField(max_length=100, required=True, label='Name')
    date       = forms.DateField(required=False, label='Date')
    game       = forms.ChoiceField(
        choices=[('nochange',_('No change'))]+GAMES, required=True,
        label=_('Game version')
    )
    offline    = forms.ChoiceField(
        choices=[('nochange',_('No change')), ('online',_('Online')), ('offline',_('Offline'))],
        required=True, label=_('On/offline')
    )
    type       = forms.ChoiceField(
        choices=[('nochange',_('No change'))]+EVENT_TYPES,
        # Translators: Type as in event type
        required=True, label=_('Type')
    )
    # Translators: Apply (changes) to…
    same_level = forms.BooleanField(required=False, label=_('Apply to all events on the same level'))
    homepage   = StrippedCharField(max_length=200, required=False, label=_('Homepage'))
    tlpd_id    = forms.IntegerField(required=False, label=_('TLPD ID'))
    tlpd_db    = forms.MultipleChoiceField(
        required=False, choices=TLPD_DBS, label=_('TLPD DB'), widget=forms.CheckboxSelectMultiple)
    tl_thread  = forms.IntegerField(required=False, label=_('TL thread'))
    lp_name    = StrippedCharField(max_length=200, required=False, label=_('Liquipedia title'))

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
            ret.append(Message(_('Entered data was invalid, no changes made.'), type=Message.ERROR))
            for field, errors in self.errors.items():
                for error in errors:
                    ret.append(Message(error=error, field=self.fields[field].label))
            return ret

        if self.cleaned_data['name'] != event.name:
            event.update_name(self.cleaned_data['name'])
            for e in event.get_children(id=False):
                e.update_name()
            ret.append(Message(_('Changed event name.'), type=Message.SUCCESS))

        if self.cleaned_data['date'] is not None:
            nchanged = event.get_matchset().update(date=self.cleaned_data['date'])
            ret.append(Message(
                ungettext_lazy('Changed date for %i match.', 'Changed date for %i matches.', nchanged)
                % nchanged, type=Message.SUCCESS
            ))

        if self.cleaned_data['game'] != 'nochange':
            nchanged = event.get_matchset().update(game=self.cleaned_data['game'])
            ret.append(Message(
                ungettext_lazy(
                    'Changed game version for %i match.',
                    'Changed game version for %i matches.',
                    nchanged) % nchanged,
                type=Message.SUCCESS
            ))

        if self.cleaned_data['offline'] != 'nochange':
            nchanged = event.get_matchset().update(offline=(self.cleaned_data['offline']=='offline'))
            ret.append(Message(
                ungettext_lazy(
                    'Changed on/offline for %i match.',
                    'Changed on/offline for %i matches.',
                    nchanged) % nchanged,
                type=Message.SUCCESS
            ))

        events = [event] if not self.cleaned_data['same_level'] else event.parent.get_immediate_children()
        nchanged = 0
        for e in events:
            if e.type != self.cleaned_data['type']:
                e.change_type(self.cleaned_data['type'])
            nchanged += 1
        if nchanged > 0:
            ret.append(Message(
                ungettext_lazy('Changed type for %i event.', 'Changed type for %i events.', nchanged) 
                % nchanged, type=Message.SUCCESS
            ))

        def update(value, attr, setter, label):
            if value != getattr(event, attr):
                getattr(event, setter)(value)
                ret.append(Message(_('Changed %s.') % label, type=Message.SUCCESS))

        update(self.cleaned_data['homepage'],   'homepage',   'set_homepage',   _('homepage'))
        update(self.cleaned_data['tlpd_id'],    'tlpd_id',    'set_tlpd_id',    _('TLPD ID'))
        update(self.cleaned_data['lp_name'],    'lp_name',    'set_lp_name',    _('Liquipedia title'))
        update(self.cleaned_data['tl_thread'],  'tl_thread',  'set_tl_thread',  _('TL thread'))
        update(sum([int(a) for a in self.cleaned_data['tlpd_db']]), 'tlpd_db', 'set_tlpd_db', _('TLPD DBs'))

        return ret
    # }}}
# }}} 

class StoriesForm(forms.Form):
    story_id = forms.IntegerField(required=False)
    player = forms.ChoiceField(required=True, label=_('Player'))
    date = forms.DateField(required=True, label=_('Date'))
    text = forms.ChoiceField(choices=STORIES, required=True, label=_('Story text'))
    params = forms.CharField(max_length=1000, required=True, label=_('Parameters'), initial='')

    def __init__(self, request=None, event=None):
        if request is not None:
            super(StoriesForm, self).__init__(request.POST)
            if 'storynew' in request.POST:
                self.action = 'new'
            elif 'storyupd' in request.POST:
                self.action = 'upd'
            elif 'storydel' in request.POST:
                self.action = 'del'
        else:
            super(StoriesForm, self).__init__()

        matches = event.get_immediate_matchset()
        players = Player.objects.filter(Q(id__in=matches.values('pla')) | Q(id__in=matches.values('plb')))
        self.fields['player'].choices = [(str(p.id), str(p)) for p in players]

        self.label_suffix = ''
        self.event = event

    def update_event(self, event):
        ret = []

        if not self.is_valid():
            ret.append(Message(_('Entered data was invalid, no changes made.'), type=Message.ERROR))
            for field, errors in self.errors.items():
                for error in errors:
                    ret.append(Message(error=error, field=self.fields[field].label))
            return ret

        if self.action in ['upd', 'del']:
            try:
                print('id:', self.cleaned_data['story_id'])
                story = Story.objects.get(id=self.cleaned_data['story_id'])
            except:
                ret.append(Message(_('Story could not be found.'), type=Message.ERROR))
                return ret

            if self.action == 'upd':
                story.date = self.cleaned_data['date']
                story.message = self.cleaned_data['text']
                story.params = self.cleaned_data['params']

                print(story.params)

                if story.verify():
                    story.save()
                    ret.append(Message(_('Story was successfully changed.'), type=Message.SUCCESS))
                else:
                    ret.append(Message(_('Parameter verification failed.'), type=Message.ERROR))

            elif self.action == 'del':
                story.delete()
                ret.append(Message(_('Story was successfully deleted.'), type=Message.SUCCESS))

        elif self.action == 'new':
            story = Story(
                player=Player.objects.get(id=self.cleaned_data['player']),
                event=event,
                date=self.cleaned_data['date'],
                message=self.cleaned_data['text'],
                params=self.cleaned_data['params']
            )
            if story.verify():
                story.save()
                ret.append(Message(_('Story was successfully created.'), type=Message.SUCCESS))
            else:
                ret.append(Message(_('Parameter verification failed.'), type=Message.ERROR))

        return ret

# {{{ WCSModForm: Form for changing WCS status.
class WCSModForm(forms.Form):
    year = forms.ChoiceField(choices=[(None, _('None'))] + WCS_YEARS, required=False, label=_('Year'))
    # Translators: WCS event tier
    tier = forms.ChoiceField(choices=WCS_TIERS, required=False, label=_('Tier'))
    points = forms.CharField(required=False, max_length=10000, label=_('Points'))

    def __init__(self, request=None, event=None):
        if request is not None:
            super(WCSModForm, self).__init__(request.POST)
        else:
            initial = {
                'year': str(event.wcs_year),
                'tier': str(event.wcs_tier),
                'points': wcs_points_code(event.wcspoints_set.order_by('-points')),
            }

            super(WCSModForm, self).__init__(initial=initial)

        self.label_suffix = ''

    # {{{ Function for parsing a single line
    def line_to_data(self, line):
        ind = line.find(' ')
        points = int(line[:ind])

        queryset = find_player(query=line[ind+1:])
        if not queryset.exists():
            raise Exception(_("No such player: '%s'.") % line[ind+1:])
        elif queryset.count() > 1:
            raise Exception(_("Ambiguous player: '%s'.") % line[ind+1:])
        else:
            return points, queryset.first()
    # }}}

    # {{{ update_event: Pushes changes to event object
    def update_event(self, event):
        ret = []

        if not self.is_valid():
            ret.append(Message(_('Entered data was invalid, no changes made.'), type=Message.ERROR))
            for field, errors in self.errors.items():
                for error in errors:
                    ret.append(Message(error=error, field=self.fields[field].label))
            return ret

        # {{{ Gather data
        entries, ok = [], True

        for line in self.cleaned_data['points'].split('\n'):
            if line.strip() == '':
                continue
            try:
                points, player = self.line_to_data(line)
                entries.append({'points': points, 'player': player, 'placement': 0})
            except Exception as e:
                ret.append(Message(str(e), type=Message.ERROR))
                ok = False

        if not ok:
            ret.append(Message(_('Errors occured, no changes made.'), type=Message.ERROR))
            return ret
        # }}}

        # {{{ If not a WCS event, clear all data
        if self.cleaned_data['year'] == 'None':
            WCSPoints.set_points(event, [])
            event.wcs_year = None
            event.wcs_tier = None
            event.save()

            ret.append(Message(_('WCS data cleared'), type=Message.SUCCESS))

            return ret
        # }}}

        # {{{ If a WCS event, set all data
        entries.sort(key=lambda a: a['placement'])
        for i, e in enumerate(entries):
            e['placement'] = i

        WCSPoints.set_points(event, entries)
        event.wcs_year = int(self.cleaned_data['year'])
        event.wcs_tier = int(self.cleaned_data['tier'])
        event.save()

        ret.append(Message(_('WCS data stored.'), type=Message.SUCCESS))

        return ret
        # }}}
    # }}}
# }}}

# {{{ PrizepoolModForm: Form for changing prizepools.
class PrizepoolModForm(forms.Form):
    sorted_curs = sorted(ccy.currencydb(), key=operator.itemgetter(0))
    currencies  = [(ccy.currency(c).code, ccy.currency(c).name) for c in sorted_curs]
    currency    = forms.ChoiceField(choices=currencies, required=True, label=_('Currency'))
    ranked      = forms.CharField(required=False, max_length=10000, label=_('Ranked'))
    unranked    = forms.CharField(required=False, max_length=10000, label=_('Unranked'))

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
        prize = Decimal(line[:ind])

        queryset = find_player(query=line[ind+1:])
        if not queryset.exists():
            raise Exception(_("No such player: '%s'.") % line[ind+1:])
        elif queryset.count() > 1:
            raise Exception(_("Ambiguous player: '%s'.") % line[ind+1:])
        else:
            return prize, queryset.first()
    # }}}

    # {{{ update_event: Pushes changes to event object
    def update_event(self, event):
        ret = []

        if not self.is_valid():
            ret.append(Message(_('Entered data was invalid, no changes made.'), type=Message.ERROR))
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
            ret.append(Message(_('Errors occured, no changes made.'), type=Message.ERROR))
            return ret
        # }}}

        # {{{ Fix placements of ranked prizes
        ranked.sort(key=lambda a: a['placement'])
        for i, e in enumerate(ranked):
            ranked[i]['placement'] = i
        # }}}

        # {{{ Commit
        try:
            Earnings.set_earnings(event, ranked, self.cleaned_data['currency'], True)
            Earnings.set_earnings(event, unranked, self.cleaned_data['currency'], False)
        except RateNotFoundError as e:
            ret.append(Message(str(e), type=Message.ERROR))
            return ret
        # }}}

        # Translators: New prizepools added to the database.
        ret.append(Message(_('New prizes committed.'), type=Message.SUCCESS))

        return ret
    # }}}
# }}}

# {{{ StoryModForm: Form for adding stories.
class StoryModForm(forms.Form):
    player = forms.ChoiceField(required=True, label=_('Player'))
    date   = forms.DateField(required=True, label=_('Date'))
    text   = StrippedCharField(max_length=200, required=True, label=_('Text'))

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
            ret.append(Message(_('Entered data was invalid, no changes made.'), type=Message.ERROR))
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

        # Translators: Stories are the dots on a player's rating chart
        ret.append(Message(_('Added a story.'), type=Message.SUCCESS))

        return ret
    # }}}
# }}}

# {{{ AddForm: Form for adding subevents.
class AddForm(forms.Form):
    name    = StrippedCharField(max_length=100, required=True, label=_('Name'))
    type    = forms.ChoiceField(choices=EVENT_TYPES, required=True, label=_('Type'))
    noprint = forms.BooleanField(required=False, label=_('No Print'))
    closed  = forms.BooleanField(required=False, label=_('Closed'))

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
            ret.append(Message(_('Entered data was invalid, no changes made.'), type=Message.ERROR))
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

        ret.append(Message(_('Added a subevent.'), type=Message.SUCCESS))

        return ret
    # }}}
# }}}

# {{{ ReorderForm: Form for reordering events.
class ReorderForm(forms.Form):
    order = StrippedCharField(max_length=10000, required=True)

    # {{{ Constructor
    def __init__(self, request=None, event=None):
        if request is not None:
            super(ReorderForm, self).__init__(request.POST)
        else:
            super(ReorderForm, self).__init__()
    # }}}

    # {{{ Custom validation
    def clean_order(self):
        try:
            ids = [int(s) for s in self.cleaned_data['order'].split(',') if s.strip() != '']
            events = Event.objects.in_bulk(ids)
        except:
            raise ValidationError(_('Unable to get these events.'))

        return [events[i] for i in ids]
    # }}}

    # {{{ update_event: Pushes changes
    def update_event(self, event):
        ret = []

        if not self.is_valid():
            ret.append(Message(_('Entered data was invalid, no changes made.'), type=Message.ERROR))
            for field, errors in self.errors.items():
                for error in errors:
                    ret.append(Message(error=error, field=self.fields[field].label))
            return ret

        if len(self.cleaned_data['order']) != event.get_immediate_children().count():
            # Translate: Order as in an ordering, e.g. 2, 7, 5…
            return [Message(_('Order invalid, try again?'), type=Message.ERROR)]

        for e in self.cleaned_data['order']:
            if e.parent != event:
                return [Message(_('Non-child event found. This should never happen.'), type=Message.ERROR)]

        min_idx = min([e.idx for idx in self.cleaned_data['order']])
        for idx, e in enumerate(self.cleaned_data['order']):
            e.set_idx(min_idx + idx)

        return [Message(_(
            # Translators: Children as in sub-events.
            'Successfully reordered %i children. Any inconsistencies will be fixed next update '
            '(no more than six hours away).'
        ) % len(self.cleaned_data['order']), type=Message.SUCCESS)]
    # }}}
# }}}

# {{{ SearchForm: Form for searching.
class SearchForm(forms.Form):
    after      = forms.DateField(required=False, label=_('After'), initial=None)
    before     = forms.DateField(required=False, label=_('Before'), initial=None)
    players    = forms.CharField(max_length=10000, required=False, label=_('Involving players'), initial='')
    event      = StrippedCharField(max_length=200, required=False, label=_('Event'), initial='')
    # Translators: Unassigned as in not assigned to an event.
    unassigned = forms.BooleanField(required=False, label=_('Only show unassigned matches'))
    bestof     = forms.ChoiceField(
        choices=[
            ('all',_('All')),
            ('3',_('Best of 3+')),
            ('5',_('Best of 5+')),
        ],
        required=False, label=_('Match format'), initial='all'
    )
    offline = forms.ChoiceField(
        choices=[
            ('both',_('Both')),
            ('offline',_('Offline')),
            ('online',_('Online')),
        ],
        required=False, label=_('On/offline'), initial='both',
    )
    wcs_season = forms.ChoiceField(
        choices=[
            ('',     _('All events')),
            ('all',  _('All seasons')),
        ]+WCS_YEARS,
        required=False, label=_('WCS Season'), initial='',
    )
    _all_tiers = ''.join(map(lambda t: str(t[0]), WCS_TIERS))
    wcs_tier = forms.ChoiceField(
        choices=[
            ('',         _('All events')),
            (_all_tiers, _('All tiers')),
        ] + WCS_TIERS + [
            (''.join(map(lambda t: str(t[0]), WCS_TIERS[1:])),  _('Non-native'))
        ],
        required=False, label=_('WCS Tier'), initial='',
    )

    game = forms.ChoiceField(
        choices=[('all',_('All'))]+GAMES, required=False, label=_('Game version'), initial='all')

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
            msgs.append(Message(_('Entered data was invalid, no changes made.'), type=Message.ERROR))
            for field, errors in self.errors.items():
                for error in errors:
                    msgs.append(Message(error=error, field=self.fields[field].label))
            return {'messages': msgs}
        # }}}

        matches = (
            Match.objects.all().prefetch_related('message_set')
                .prefetch_related('pla', 'plb', 'period', 'eventobj')
                .annotate(Count('eventobj__match'))
        )

        # {{{ All the easy filtering
        if self.cleaned_data['after'] is not None:
            matches = matches.filter(date__gte=self.cleaned_data['after'])

        if self.cleaned_data['before'] is not None:
            matches = matches.filter(date__lte=self.cleaned_data['before'])

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

        if self.cleaned_data['wcs_season'] != '':
            if self.cleaned_data['wcs_season'] == 'all':
                matches = matches.filter(
                    eventobj__uplink__parent__wcs_year__isnull=False
                )
            else:
                matches = matches.filter(
                    eventobj__uplink__parent__wcs_year=int(self.cleaned_data['wcs_season'])
                )

        if self.cleaned_data['wcs_tier'] != '':
            tiers = list(map(int, self.cleaned_data['wcs_tier']))
            matches = matches.filter(
                eventobj__uplink__parent__wcs_tier__in=tiers
            )

        # }}}

        matches = matches.distinct()

        # {{{ Filter by event
        if self.cleaned_data['event'] != None:
            lex = shlex.shlex(self.cleaned_data['event'], posix=True)
            lex.wordchars += "'"
            lex.quotes = '"'

            terms = [s.strip() for s in list(lex) if s.strip() != '']

            no_eventobj_q = Q(eventobj__isnull=True)

            for term in terms:
                no_eventobj_q &= Q(event__icontains=term)

            matches = matches.filter(
                no_eventobj_q |
                Q(
                    eventobj__isnull=False,
                    eventobj__fullname__iregex=(
                        r"\s".join(r".*{}.*".format(term) for term in terms)
                    )
                )
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
                ret['messages'].append(Message(
                    # Translators: Matches here as in search matches.
                    _("No matches found: '%s'.") % line.strip(), type=Message.ERROR
                ))
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
                _('Too many results (%i). Please add restrictions.') % ret['count'],
                type=Message.ERROR
            ))
            return ret

        matches = matches.order_by('-eventobj__latest', '-eventobj__idx', '-date', 'event', 'id')
        if 1 <= len(pls) <= 2:
            ret['matches'] = display_matches(matches, date=True, fix_left=pls[0], eventcount=True)
            ret['sc_my'], ret['sc_op'] = (
                sum([m['pla']['score'] for m in ret['matches']]),
                sum([m['plb']['score'] for m in ret['matches']]),
            )
            ret['msc_my'], ret['msc_op'] = (
                sum([1 if m['pla']['score'] > m['plb']['score'] else 0 for m in ret['matches']]),
                sum([1 if m['plb']['score'] > m['pla']['score'] else 0 for m in ret['matches']]),
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
    event   = forms.ChoiceField(required=True, label=_('Event'))
    date    = forms.DateField(required=False, label=_('Date'), initial=None)
    offline = forms.ChoiceField(
        choices=[('nochange',_('No change')), ('online',_('Online')), ('offline',_('Offline'))],
        required=True, label=_('On/offline'), initial='nochange'
    )
    game = forms.ChoiceField(
        choices=[('nochange',_('No change'))]+GAMES,
        required=True, label=_('Game version'), initial='nochange'
    )

    # {{{ Constructor
    def __init__(self, request=None):
        if request is not None:
            super(ResultsModForm, self).__init__(request.POST)
        else:
            super(ResultsModForm, self).__init__()

        self.fields['event'].choices = [(0, _('No change'))] + [
            (e['id'], e['fullname']) for e in Event.objects.filter(closed=False)
                .annotate(num_downlinks=Count('downlink'))
                .filter(num_downlinks=1)
                .order_by('idx')
                .values('id', 'fullname')
        ]
    # }}}

    # {{{ modify: Commits modifications
    def modify(self, ids):
        ret = []

        if not self.is_valid():
            ret.append(Message(_('Entered data was invalid, no changes made.'), type=Message.ERROR))
            for field, errors in self.errors.items():
                for error in errors:
                    ret.append(Message(error=error, field=self.fields[field].label))
            return ret

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

        return [Message(
            ungettext_lazy('Updated %i match.', 'Updated %i matches.', matches.count()) % matches.count(), 
            type=Message.SUCCESS
        )]
    # }}}
# }}}

# {{{ results view
@cache_login_protect
def results(request):
    base = base_ctx('Results', 'By Date', request)

    try:
        day = datetime.strptime(get_param(request, 'd', None), '%Y-%m-%d').date()
    except:
        day = date.today()

    bounds = Match.objects.aggregate(Min('date'), Max('date'))
    abounds = ArchonMatch.objects.aggregate(Min('date'), Max('date'))

    minn = min(bounds['date__min'], abounds['date__min'])
    maxx = max(bounds['date__max'], abounds['date__max'])

    day = min(max(minn, day), maxx)
    base.update({
        'mindate': minn,
        'maxdate': maxx,
        'td':      day,
    })

    matches = (
        Match.objects.filter(date=day).order_by('eventobj__idx', 'eventobj__latest', 'event', 'id')
            .prefetch_related('message_set', 'rta', 'rtb', 'pla', 'plb', 'eventobj')
            .annotate(Count('eventobj__match'))
    )
    archon_matches = (
        ArchonMatch.objects.filter(date=day).order_by('eventobj__idx', 'eventobj__latest', 'event', 'id')
            .prefetch_related('message_set', 'pla1', 'pla2', 'plb1', 'plb2', 'eventobj')
            .annotate(Count('eventobj__match'))
    )
    add_links = request.user.is_authenticated() and request.user.is_staff

    matches = itertools.chain(matches, archon_matches)

    base['matches'] = display_matches(matches, date=False, ratings=True, messages=True,
                                      eventcount=True, add_links=add_links)

    return render_to_response('results.djhtml', base)
# }}}

# {{{ events view
@cache_login_protect
def events(request, event_id=None):
    # {{{ Get base context, redirect if necessary
    if 'goto' in request.GET:
        return redirect('/results/events/' + request.GET['goto'])

    base = base_ctx('Results', 'By Event', request)
    # }}}

    # {{{ Display the main table if event ID is not given
    if event_id is None:
        root_events = (
            Event.objects
                  .annotate(num_uplinks=Count("uplink"))
                  .filter(num_uplinks=1)
                  .order_by('name')
                  .only('id', 'name', 'big', 'category', 'fullname')
        )
        base.update({
            'bigs': (
                list(root_events.filter(big=True, category=CAT_INDIVIDUAL)) +
                list(root_events.filter(big=True, category=CAT_TEAM)) +
                list(root_events.filter(big=True, category=CAT_FREQUENT))
            ),
            'smalls': (
                list(root_events.filter(big=False, category=CAT_INDIVIDUAL).order_by('name')) +
                list(root_events.filter(big=False, category=CAT_TEAM).order_by('name')) +
                list(root_events.filter(big=False, category=CAT_FREQUENT).order_by('name'))
            )
        })

        base['messages'].append(Message(
            _('The events are organized in a hierarchical fashion. Thus, all GSL tournaments '
              'are filed under GSL, all Code S under their respective seasons, all groups under '
              'their respective Code S event, and so on.'),
            type=Message.INFO
        ))

        return render_to_response('events.djhtml', base)
    # }}}

    # {{{ Get object, generate messages, and ensure big is set. Find familial relationships.
    event = get_object_or_404(Event, id=event_id)
    base['messages'] += generate_messages(event)

    matches = event.get_matchset()
    if matches.count() > 200 and not event.big:
        event.set_big(True)

    base.update({
        'event':            event,
        'siblings':         event.get_parent().get_immediate_children().exclude(id=event.id)
                                if event.get_parent() else None,
        'path':             event.get_ancestors(id=True),
        'children':         event.get_immediate_children(),
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
        if event.has_children():
            check_form('reorderform', ReorderForm, 'reorder')
        if event.type == TYPE_EVENT:
            check_form('ppform', PrizepoolModForm, 'modpp')
            check_form('wcsform', WCSModForm, 'modwcs')
        if not event.has_children() and event.get_immediate_matchset().exists():
            check_form('stform', StoriesForm, 'modstory')

        if 'close' in request.GET and request.GET['close'] == '1':
            event.close()
            base['messages'].append(Message(_('Sucessfully closed event.'), type=Message.SUCCESS))
    # }}}

    # {{{ Prizepool information for the public
    total_earnings = Earnings.objects.filter(event__uplink__parent=event)

    local_earnings = Earnings.objects.filter(event=event)

    ranked_prize = local_earnings.exclude(placement=0)\
                                 .order_by('-earnings', 'placement')
    unranked_prize = list(
        local_earnings.filter(placement=0).order_by('-earnings')
    )

    placements = get_placements(event)
    prize_pool_table = list()
    for k, g in groupby(ranked_prize, key=lambda x: x.earnings):
        gl = list(g)
        prize_pool_table.append((k, placements[k], gl, len(gl)))

    if len(prize_pool_table) > 0:
        base['ranked_prize'] = prize_pool_table
    if len(unranked_prize) > 0:
        base['unranked_prize'] = unranked_prize

    currencies = list({r['currency'] for r in total_earnings.values('currency').distinct()})
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

    add_links = request.user.is_authenticated() and request.user.is_staff

    base.update({
        'game':      etn(lambda: dict(GAMES)[matches.values('game').distinct()[0]['game']]),
        'nmatches':  matches.count(),
        'ngames':    sum(count_winloss_games(matches)),
        'pvp_games': count_mirror_games(matches, 'P'),
        'tvt_games': count_mirror_games(matches, 'T'),
        'zvz_games': count_mirror_games(matches, 'Z'),
        'matches':   display_matches(
            matches.prefetch_related('message_set')
                .prefetch_related('pla', 'plb', 'eventobj')
                .annotate(Count('eventobj__match'))
                .order_by('-eventobj__latest', '-eventobj__idx', '-date', '-id')[0:200],
            eventcount=True,
            add_links=add_links
        ),
        'nplayers':  Player.objects.filter(
            Q(id__in=matches.values('pla')) | Q(id__in=matches.values('plb'))
        ).count(),
    })

    offlines = list(matches.values('offline').distinct())
    if len(offlines) > 1:
        base['offline'] = _('Both')
    elif len(offlines) == 1:
        base['offline'] = _('Offline') if offlines[0]['offline'] else _('Online')

    base['pvt_wins'], base['pvt_loss'] = count_matchup_games(matches, 'P', 'T')
    base['pvz_wins'], base['pvz_loss'] = count_matchup_games(matches, 'P', 'Z')
    base['tvz_wins'], base['tvz_loss'] = count_matchup_games(matches, 'T', 'Z')
    base['tot_mirror'] = base['pvp_games'] + base['tvt_games'] + base['zvz_games']
    # }}}

    return render_to_response('eventres.djhtml', base)
# }}}

# {{{ search view
@cache_login_protect
def search(request):
    base = base_ctx('Results', 'Search', request)

    # {{{ Filtering and modifying
    if base['adm']:
        if request.method == 'POST':
            modform = ResultsModForm(request=request)
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

    return render_to_response('results_search.djhtml', base, context_instance=RequestContext(request))
# }}}
