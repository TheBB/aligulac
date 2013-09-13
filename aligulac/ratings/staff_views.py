# {{{ Imports
from datetime import date, timedelta
import shlex

from django import forms
from django.core.exceptions import ValidationError
from django.db import connection
from django.db.models import (
    Count,
    F,
    Q,
)
from django.http import HttpResponse
from django.shortcuts import render_to_response

from aligulac.tools import (
    base_ctx,
    etn,
    login_message,
    Message,
    ntz,
    StrippedCharField,
)

from ratings.models import (
    CAT_TEAM,
    Event,
    EVENT_TYPES,
    GAMES,
    HOTS,
    Match,
    PreMatch,
    PreMatchGroup,
    TYPE_CATEGORY,
    TYPE_EVENT,
    TYPE_ROUND,
)
from ratings.tools import (
    display_matches,
    find_player,
)
# }}}

# {{{ Auxiliary functions
def find_dashes(line):
    in_quote = False
    dashes = []

    for ind, c in enumerate(line):
        if c == '"':
            in_quote = not in_quote
        elif c == '-' and not in_quote:
            dashes.append(ind)

    return dashes

def find_race_override(lst):
    override = None
    i = 0

    while i < len(lst):
        if len(lst[i]) == 3 and lst[i][:2].upper() == 'R:' and lst[i][2].upper() in 'PTZR':
            override = lst[i][2].upper()
            del lst[i]
        else:
            i += 1
    
    return override

def check_duplicates(match, dup_flag):
    if dup_flag:
        return False

    day = timedelta(days=1)
    matches = (
        Match.objects.filter(date__gte=(match.date - day), date__lte=(match.date + day))
            .filter(
                Q(pla=match.pla, plb=match.plb, sca=match.sca, scb=match.scb) |
                Q(pla=match.plb, plb=match.pla, sca=match.scb, scb=match.sca)
            )
    )

    return matches.exists()

def review_find_player(query):
    lst = shlex.split(query)
    override = find_race_override(lst)
    make_flag = '!MAKE' in lst
    lst = [l for l in lst if l != '!MAKE']

    return find_player(lst=lst, make=make_flag, soft=False), override


def fill_players(pm):
    messages = []

    if pm.pla is None:
        players, override = review_find_player(pm.pla_string)
        if players.count() > 1:
            messages.append("Not unique player: '%s'." % pm.pla_string)
        elif players.count() == 0:
            messages.append("Could not find player: '%s'." % pm.pla_string)
        else:
            pm.pla = players.first()
            pm.rca = override if override is not None else pm.pla.race

    if pm.plb is None:
        players, override = review_find_player(pm.plb_string)
        if players.count() > 1:
            messages.append("Not unique player: '%s'." % pm.plb_string)
        elif players.count() == 0:
            messages.append("Could not find player: '%s'." % pm.plb_string)
        else:
            pm.plb = players.first()
            pm.rcb = override if override is not None else pm.plb.race

    return messages
# }}}

# {{{ ReviewMatchesForm: Form for reviewing matches.
class ReviewMatchesForm(forms.Form):
    eventobj = forms.ChoiceField(
        choices=[
            (e['id'], e['fullname']) for e in Event.objects.filter(closed=False)
                .exclude(downlink__distance__gt=0)
                .order_by('fullname')
                .values('id', 'fullname')
        ],
        required=False, label='Event',
    )
    date = forms.DateField(required=False, label='Date', initial=None)
    approve = forms.BooleanField(required=False, label='Approve', initial=False)
    reject = forms.BooleanField(required=False, label='Reject', initial=False)
    dup_flag = forms.BooleanField(required=False, label='Ignore duplicates', initial=False)

    # {{{ Constructor
    def __init__(self, request=None, submitter=None):
        if request is not None:
            super(ReviewMatchesForm, self).__init__(request.POST)
            self.commit(request.POST, submitter)
        else:
            super(ReviewMatchesForm, self).__init__()

        self.label_suffix = ''
    # }}}
    
    # {{{ Custom validation
    def clean_eventobj(self):
        try:
            return Event.objects.get(id=self.cleaned_data['eventobj'])
        except:
            raise ValidationError('Could not find this event object.')

    def clean(self):
        if self.cleaned_data['approve'] == self.cleaned_data['reject']:
            raise ValidationError('You must either approve or reject.')
        return self.cleaned_data
    # }}}

    # {{{ Commit changes
    def commit(self, post, submitter):
        self.messages = []

        if not self.is_valid():
            self.messages.append(Message('Entered data was invalid, no changes made.', type=Message.ERROR))
            for field, errors in self.errors.items():
                for error in errors:
                    if field == '__all__':
                        self.messages.append(Message(error, type=Message.ERROR))
                    else:
                        self.messages.append(Message(error=error, field=self.fields[field].label))
            return

        prematches = [
            PreMatch.objects.get(id=int(key.split('-')[-1]))
            for key in sorted(post.keys())
            if key[0:6] == 'match-' and post[key] == 'y'
        ]

        matches = []
        for pm in prematches:
            if self.cleaned_data['reject']:
                group = pm.group
                pm.delete()
                if not group.prematch_set.exists():
                    group.delete()
                continue

            if pm.pla is None:
                pm.pla_string = post['match-%i-pla' % pm.id]
            if pm.plb is None:
                pm.plb_string = post['match-%i-plb' % pm.id]
            pm.save()

            for msg in fill_players(pm):
                self.messages.append(Message(msg, type=Message.ERROR))

            if pm.is_valid():
                m = Match(
                    pla       = pm.pla,
                    plb       = pm.plb,
                    sca       = pm.sca,
                    scb       = pm.scb,
                    rca       = pm.rca,
                    rcb       = pm.rcb,
                    date      = self.cleaned_data['date'] or pm.group.date,
                    eventobj  = self.cleaned_data['eventobj'],
                    event     = pm.group.event,
                    submitter = submitter,
                    offline   = pm.group.offline,
                    game      = pm.group.game,
                )

                if check_duplicates(m, self.cleaned_data['dup_flag']):
                    self.messages.append(Message(
                        "Could not make match %s vs %s: possible duplicate found." % (m.pla.tag, m.plb.tag),
                        type=Message.ERROR,
                    ))
                    continue

                m.set_period()
                m.set_ratings()
                m.save()

                matches.append(m)

                group = pm.group
                pm.delete()
                if not group.prematch_set.exists():
                    group.delete()
            else:
                pm.save()

        if self.cleaned_data['approve'] and len(matches) > 0:
            self.messages.append(
                Message('Successfully approved %i matches.' % len(matches), type=Message.SUCCESS))
        elif self.cleaned_data['reject'] and len(prematches) > 0:
            self.messages.append(
                Message('Successfully rejected %i matces.' % len(prematches), type=Message.SUCCESS))
    # }}}
# }}}

# {{{ AddMatchesForm: Form for adding matches (duh).
class AddMatchesForm(forms.Form):
    eventobj = forms.ChoiceField(
        choices=[
            (e['id'], e['fullname']) for e in Event.objects.filter(closed=False)
                .exclude(downlink__distance__gt=0)
                .order_by('fullname')
                .values('id', 'fullname')
        ],
        required=False, label='Event',
    )
    eventtext = StrippedCharField(max_length=200, required=False, label='Event')
    date      = forms.DateField(required=True, label='Date', initial=date.today())
    game      = forms.ChoiceField(choices=GAMES, label='Game version', initial=HOTS)
    offline   = forms.BooleanField(required=False, label='Offline', initial=False)
    source    = StrippedCharField(max_length=1000, required=False, label='Source')
    contact   = StrippedCharField(max_length=1000, required=False, label='Contact')
    notes     = forms.CharField(max_length=10000, required=False, label='Notes', initial='')
    matches   = forms.CharField(max_length=10000, required=True, label='Matches', initial='')

    # {{{ Constructor
    def __init__(self, is_adm, *args, **kwargs):
        super(AddMatchesForm, self).__init__(*args, **kwargs)
        self.label_suffix = ''
        self.is_adm = is_adm
    # }}}

    # {{{ Validation
    def clean_eventobj(self):
        if not self.is_adm:
            return self.cleaned_data['eventobj']
        try:
            return Event.objects.get(id=self.cleaned_data['eventobj'])
        except:
            raise ValidationError('Could not find this event object.')

    def clean_eventtext(self):
        if self.is_adm:
            return self.cleaned_data['eventtext']
        if self.cleaned_data['eventtext'] in [None, '']:
            raise ValidationError('This field is required.')
        return self.cleaned_data['eventtext']

    def clean_source(self):
        if self.is_adm:
            return self.cleaned_data['source']
        if self.cleaned_data['source'] in [None, '']:
            raise ValidationError('This field is required.')
        return self.cleaned_data['source']
    # }}}

    # {{{ Parse the matches
    def parse_matches(self, submitter):
        self.messages = []

        if not self.is_valid():
            self.messages.append(Message('Entered data was invalid, no changes made.', type=Message.ERROR))
            for field, errors in self.errors.items():
                for error in errors:
                    self.messages.append(Message(error=error, field=self.fields[field].label))
            return

        if not self.is_adm:
            self.prematchgroup = PreMatchGroup(
                date    = self.cleaned_data['date'],
                event   = self.cleaned_data['eventtext'],
                source  = self.cleaned_data['source'],
                contact = self.cleaned_data['contact'],
                notes   = self.cleaned_data['notes'],
                game    = self.cleaned_data['game'],
                offline = self.cleaned_data['offline'],
            )
            self.prematchgroup.save()

        error_lines, matches = [], []
        for line in self.cleaned_data['matches'].splitlines():
            if line.strip() == '':
                continue

            dashes = find_dashes(line)
            try:
                pla_query = shlex.split(line[:dashes[0]])
                middle = shlex.split(line[dashes[0]+1:dashes[1]])
                plb_query = middle[:-1]
                sca = int(middle[-1])
                end = shlex.split(line[dashes[1]+1:])
                scb = int(end[0])

                make_flag = '!MAKE' in end
                dup_flag = '!DUP' in end
            except Exception as e:
                self.messages.append(
                    Message("Could not parse '%s' (%s)." % (line, str(e)), type=Message.ERROR))
                error_lines.append(line)
                continue

            pla_race_override = find_race_override(pla_query)
            plb_race_override = find_race_override(plb_query)

            try:
                match = self.make_match(
                    pla_query, plb_query,
                    pla_race_override, plb_race_override,
                    sca, scb,
                    make_flag, dup_flag,
                )
                if match is None:
                    error_lines.append(line)
                    continue
            except Exception as e:
                self.messages.append(
                    Message("Error creating match '%s' (%s)." % (line, str(e)), type=Message.ERROR))
                error_lines.append(line)
                continue

            if self.is_adm:
                match.submitter = submitter
            matches.append(match)

        for m in matches:
            m.save()
        if len(matches) > 0:
            self.messages.append(
                Message('Successfully added %i matches.' % len(matches), type=Message.SUCCESS))

        self.data = self.data.copy()
        self.data['matches'] = '\n'.join(error_lines)

        return matches
    # }}}

    # {{{ get_player: Auxiliary function for searching for players
    def get_player(self, query, make_flag):
        players = find_player(lst=query, make=make_flag, soft=False)

        if players.count() != 1:
            if self.is_adm:
                if players.count() == 0:
                    self.messages.append(
                        Message("Could not find player: '%s'." % ' '.join(query), type=Message.ERROR))
                elif players.count() > 1:
                    self.messages.append(
                        Message("Not unique player: '%s'." % ' '.join(query), type=Message.ERROR))
            return None

        return players.first()
    # }}}

    # {{{ Make matches (called from parse_matches). DOES NOT SAVE THEM.
    def make_match(self, pla_query, plb_query, pla_race_or, plb_race_or, sca, scb, make_flag, dup_flag):
        pla = self.get_player(pla_query, make_flag)
        plb = self.get_player(plb_query, make_flag)

        if (pla is None or plb is None) and self.is_adm:
            return None

        if not self.is_adm:
            match = PreMatch(
                group      = self.prematchgroup,
                pla        = pla,
                plb        = plb,
                pla_string = ' '.join(pla_query),
                plb_string = ' '.join(plb_query),
                sca        = sca,
                scb        = scb,
                date       = self.cleaned_data['date'],
                rca        = pla_race_or,
                rcb        = plb_race_or,
            )
            return match
        else:
            match = Match(
                pla      = pla,
                plb      = plb,
                sca      = sca,
                scb      = scb,
                rca      = pla_race_or if pla_race_or is not None else pla.race,
                rcb      = plb_race_or if plb_race_or is not None else plb.race,
                date     = self.cleaned_data['date'],
                treated  = False,
                eventobj = self.cleaned_data['eventobj'],
                game     = self.cleaned_data['game'],
                offline  = self.cleaned_data['offline'],
            )
            if check_duplicates(match, dup_flag):
                self.messages.append(Message(
                    "Could not make match %s vs %s: possible duplicate found." % (pla.tag, plb.tag),
                    type=Message.ERROR,
                ))
                return None
            match.set_period()
            match.set_ratings()
            return match
    # }}}
# }}}

# {{{ AddEventsForm: Form for adding events.
class AddEventsForm(forms.Form):
    parent_id = forms.IntegerField(required=True, label='Parent ID')
    predef_names = forms.ChoiceField([
        ('other', 'Other'),
        ('Group Stage, Playoffs', 'Group stage and playoffs'),
        ('Group A,Group B,Group C,Group D', 'Groups A through D'),
        ('Group A,Group B,Group C,Group D,Group E,Group F,Group G,Group H', 'Groups A through H'),
        ('Ro64,Ro32,Ro16,Ro8,Ro4,Final', 'Ro64→Final'),
        ('Ro32,Ro16,Ro8,Ro4,Final', 'Ro32→Final'),
        ('Ro16,Ro8,Ro4,Final', 'Ro16→Final'),
        ('Ro8,Ro4,Final', 'Ro8→Final'),
        ('Ro4,Final', 'Ro4→Final'),
        ('Ro64,Ro32,Ro16,Ro8,Ro4,Third place match,Final', 'Ro64→Final + 3rd place'),
        ('Ro32,Ro16,Ro8,Ro4,Third place match,Final', 'Ro32→Final + 3rd place'),
        ('Ro16,Ro8,Ro4,Third place match,Final', 'Ro16→Final + 3rd place'),
        ('Ro8,Ro4,Third place match,Final', 'Ro8→Final + 3rd place'),
        ('Ro4,Third place match,Final', 'Ro4→Final + 3rd place'),
        ('Early rounds,Ro64,Ro32,Ro16,Ro8,Ro4,Final', 'Ro64→Final + early rounds'),
        ('Early rounds,Ro32,Ro16,Ro8,Ro4,Final', 'Ro32→Final + early rounds'),
        ('Early rounds,Ro16,Ro8,Ro4,Final', 'Ro16→Final + early rounds'),
        ('Early rounds,Ro8,Ro4,Final', 'Ro8→Final + early rounds'),
        ('Early rounds,Ro4,Final', 'Ro4→Final + early rounds'),
        ('Early rounds,Ro64,Ro32,Ro16,Ro8,Ro4,Third place match,Final', 
            'Ro64→Final + 3rd place and early rounds'),
        ('Early rounds,Ro32,Ro16,Ro8,Ro4,Third place match,Final', 'Ro32→Final + 3rd place and early rounds'),
        ('Early rounds,Ro16,Ro8,Ro4,Third place match,Final', 'Ro16→Final + 3rd place and early rounds'),
        ('Early rounds,Ro8,Ro4,Third place match,Final', 'Ro8→Final + 3rd place and early rounds'),
        ('Early rounds,Ro4,Third place match,Final', 'Ro4→Final + 3rd place and early rounds'),
        ('WB,LB,Final', 'WB, LB, Final'),
        ('Round 1,Round 2', 'LB: Round 1->Round 2'),
        ('Round 1,Round 2,Round 3,Round 4', 'LB: Round 1->Round 4'),
        ('Round 1,Round 2,Round 3,Round 4,Round 5,Round 6', 'LB: Round 1->Round 6'),
        ('Round 1,Round 2,Round 3,Round 4,Round 5,Round 6,Round 7,Round 8', 'LB: Round 1->Round 8'),
    ], required=True, label='Predefined names')
    custom_names = StrippedCharField(max_length=400, required=False, label='Custom names')
    type = forms.ChoiceField(choices=EVENT_TYPES, required=True, label='Type')
    big = forms.BooleanField(required=False, label='Big', initial=False)
    noprint = forms.BooleanField(required=False, label='No print', initial=False)

    # {{{ Constructor
    def __init__(self, request=None):
        if request is None:
            super(AddEventsForm, self).__init__()
        else:
            super(AddEventsForm, self).__init__(request.POST)
            if 'op' in request.POST and request.POST['op'] == 'Commit new sub-events':
                self.action = 'add'
            else:
                self.action = 'close'

        self.label_suffix = ''
    # }}}

    # {{{ Custom validation
    def clean_parent_id(self):
        try:
            if int(self.cleaned_data['parent_id']) != -1:
                return Event.objects.get(id=int(self.cleaned_data['parent_id']))
            return None
        except:
            raise ValidationError('Could not find event ID %s.' % self.cleaned_data['parent_id'])

    def clean(self):
        if self.action != 'add':
            if self.cleaned_data['parent_id'] is None:
                raise ValidationError('Must specify an event to close.')
            return self.cleaned_data

        if self.cleaned_data['predef_names'] == 'other' and self.cleaned_data['custom_names'] in ['', None]:
            raise ValidationError('No event names specified.')

        names = (
            self.cleaned_data['predef_names']
            if self.cleaned_data['predef_names'] != 'other'
            else self.cleaned_data['custom_names']
        )

        self.cleaned_data['names'] = [s.strip() for s in names.split(',') if s.strip() != '']
        return self.cleaned_data
    # }}}

    # {{{ Commit changes
    def commit(self):
        ret = []

        if not self.is_valid():
            ret.append(Message('Entered data was invalid, no changes made.', type=Message.ERROR))
            for field, errors in self.errors.items():
                for error in errors:
                    if field == '__all__':
                        ret.append(Message(error, type=Message.ERROR))
                    else:
                        ret.append(Message(error=error, field=self.fields[field].label))
            return ret

        if self.action == 'add':
            adder = (
                self.cleaned_data['parent_id'].add_child
                if self.cleaned_data['parent_id'] is not None else
                Event.add_root
            )
            for name in self.cleaned_data['names']:
                adder(
                    name=name, 
                    type=self.cleaned_data['type'],
                    big=self.cleaned_data['big'],
                    noprint=self.cleaned_data['noprint'],
                )
            ret.append(
                Message('Successfully created %i new events.' % len(self.cleaned_data['names']),
                type=Message.SUCCESS)
            )
        elif self.action == 'close':
            self.cleaned_data['parent_id'].close()
            ret.append(Message('Successfully closed event.', type=Message.SUCCESS))

        return ret
    # }}}
# }}}

# {{{ Add matches view
def add_matches(request):
    base = base_ctx('Submit', 'Matches', request)
    login_message(base)

    if request.method == 'POST' and 'submit' in request.POST:
        form = AddMatchesForm(base['adm'], request.POST)
        base['matches'] = display_matches(form.parse_matches(request.user), messages=False)
        base['messages'] += form.messages
    else:
        form = AddMatchesForm(base['adm'])

    base['form'] = form

    return render_to_response('add.html', base)
# }}}

# {{{ Review matches view
def review_matches(request):
    base = base_ctx('Submit', 'Review', request)
    if not base['adm']:
        return redirect('/login/')
    login_message(base)

    if request.method == 'POST':
        form = ReviewMatchesForm(request=request, submitter=request.user)
        base['messages'] += form.messages
    else:
        form = ReviewMatchesForm()

    base['form'] = form

    base['groups'] = (
        PreMatchGroup.objects.filter(prematch__isnull=False)
            .prefetch_related('prematch_set')
            .order_by('id', 'event')
            .distinct()
    )

    for g in base['groups']:
        g.prematches = display_matches(g.prematch_set.all(), messages=False)

    return render_to_response('review.html', base)
# }}}

# {{{ Event manager view
def events(request):
    base = base_ctx('Submit', 'Events', request)
    if not base['adm']:
        return redirect('/login/')
    login_message(base)

    if request.method == 'POST':
        form = AddEventsForm(request=request)
        base['messages'] += form.commit()
    else:
        form = AddEventsForm()

    base['form'] = form

    # {{{ Build event list
    events = list(Event.objects.filter(closed=False).annotate(Count('uplink')).order_by('fullname'))
    total_fold = 0
    for i, e in enumerate(events):
        fold = ntz(etn(lambda: events[i+1].uplink__count - e.uplink__count))
        if i == len(events) - 1:
            fold = -total_fold
        e.fold = fold
        total_fold += fold

    base['nodes'] = events
    # }}}

    return render_to_response('eventmgr.html', base)
# }}}

# {{{ Open events view
def open_events(request):
    base = base_ctx('Submit', 'Open events', request)
    if not base['adm']:
        return redirect('/login/')
    login_message(base)

    # {{{ Breadth-first search for closed events with unknown prizepool status
    pp_events = []
    search = Event.objects.filter(parent__isnull=True).exclude(category=CAT_TEAM, type=TYPE_ROUND)
    while search.exists():
        pp_events += list(search.filter(type=TYPE_EVENT, prizepool__isnull=True, closed=True))
        search = Event.objects.filter(parent__in=search).exclude(type=TYPE_ROUND)
    pp_events.sort(key=lambda e: e.fullname)
    base['pp_events'] = pp_events
    # }}}

    return render_to_response('events_open.html', base)
# }}}
