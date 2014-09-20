from datetime import date, timedelta
# Misc staff tools
import json
import re
import shlex
from urllib.request import Request, urlopen

from bs4 import UnicodeDammit
from countries import data
from django import forms
from django.core.exceptions import ValidationError
from django.db import connection
from django.db.models import (
    F,
    Max,
    Q,
    Count
)
from django.http import HttpResponse
from django.shortcuts import (
    redirect,
    render_to_response,
)
from django.utils.translation import ugettext_lazy as _
from django.utils.translation import ungettext_lazy
from mwparserfromhell import parse as parsemw

from aligulac.views import EXTRA_NULL_SELECT
from aligulac.tools import (
    base_ctx,
    etn,
    JsonResponse,
    login_message,
    Message,
    ntz,
    StrippedCharField,
)

from ratings.models import (
    CAT_TEAM,
    Earnings,
    Event,
    EventAdjacency,
    EVENT_TYPES,
    GAMES,
    GroupMembership,
    HOTS,
    Match,
    Player,
    PreMatch,
    PreMatchGroup,
    Rating,
    TYPE_CATEGORY,
    TYPE_EVENT,
    TYPE_ROUND,
)
from ratings.templatetags.ratings_extras import player as player_filter
from ratings.tools import (
    country_list,
    display_matches,
    find_player,
)

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
    matches = Match.objects.filter(date__gte=(match.date - day), date__lte=(match.date + day)).filter(
        Q(pla=match.pla, plb=match.plb, sca=match.sca, scb=match.scb) |
        Q(pla=match.plb, plb=match.pla, sca=match.scb, scb=match.sca)
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
            messages.append(_("Ambiguous player: '%s'.") % pm.pla_string)
        elif players.count() == 0:
            messages.append(_("Could not find player: '%s'.") % pm.pla_string)
        else:
            pm.pla = players.first()
            pm.rca = override if override is not None else pm.pla.race

    if pm.plb is None:
        players, override = review_find_player(pm.plb_string)
        if players.count() > 1:
            messages.append(_("Ambiguous player: '%s'.") % pm.plb_string)
        elif players.count() == 0:
            messages.append(_("Could not find player: '%s'.") % pm.plb_string)
        else:
            pm.plb = players.first()
            pm.rcb = override if override is not None else pm.plb.race

    return messages

def fill_aux_event(qset):
    for e in qset:
        e.up_homepage, e.up_tl_thread, e.up_lp_name, e.up_tlpd_id, e.up_tlpd_db = None, None, None, None, None
        for l in e.uplink.all():
            e.up_homepage = l.parent.homepage or e.up_homepage
            e.up_tl_thread = l.parent.tl_thread or e.up_tl_thread
            e.up_lp_name = l.parent.lp_name or e.up_lp_name
            if l.parent.tlpd_db is not None:
                e.up_tlpd_db = l.parent.tlpd_db
                e.up_tlpd_id = l.parent.tlpd_id

# Form for reviewing matches.
class ReviewMatchesForm(forms.Form):
    date = forms.DateField(required=False, label=_('Date'), initial=None)
    dup_flag = forms.BooleanField(required=False, label=_('Ignore duplicates'), initial=False)

    def __init__(self, request=None, submitter=None):
        if request is not None:
            super(ReviewMatchesForm, self).__init__(request.POST)
            self.eobj = request.POST['eventobj']
            self.approve = 'approve' in request.POST
            self.commit(request.POST, submitter)
        else:
            super(ReviewMatchesForm, self).__init__()

        self.label_suffix = ''

        self.fields['eventobj'] = forms.ChoiceField(
            choices=[
                (e['id'], e['fullname']) for e in Event.objects.filter(closed=False)
                    .annotate(num_downlinks=Count('downlink'))
                    .filter(num_downlinks=1)
                    .order_by('idx')
                    .values('id', 'fullname')
            ],
            required=False, label=_('Event'),
        )

    # Custom validation
    def clean(self):
        try:
            self.cleaned_data['eventobj'] = Event.objects.get(id=int(self.eobj))
        except:
            raise ValidationError(_('Could not find this event object.'))

        return self.cleaned_data

    # Commit changes
    def commit(self, post, submitter):
        self.messages = []

        if not self.is_valid():
            self.messages.append(Message(_('Entered data was invalid, no changes made.'), type=Message.ERROR))
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
            if not self.approve:
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
                    rca       = pm.rca or (pm.pla.race if pm.pla.race != 'S' else 'R'),
                    rcb       = pm.rcb or (pm.plb.race if pm.plb.race != 'S' else 'R'),
                    date      = self.cleaned_data['date'] or pm.group.date,
                    eventobj  = self.cleaned_data['eventobj'],
                    event     = pm.group.event,
                    submitter = submitter,
                    offline   = pm.group.offline,
                    game      = pm.group.game,
                )

                if check_duplicates(m, self.cleaned_data['dup_flag']):
                    self.messages.append(Message(
                        _("Could not make match %(pla)s vs %(plb)s: possible duplicate found.")
                            % {'pla': m.pla.tag, 'plb': m.plb.tag},
                        type=Message.ERROR,
                    ))
                    continue
                if 'R' in [m.rca, m.rcb]:
                    self.messages.append(Message(
                        _("Unknown race in %(pla)s vs %(plb)s: set to random.")
                            % {'pla': pla.tag, 'plb': plb.tag},
                        type=Message.WARNING,
                    ))

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

        if self.approve and len(matches) > 0:
            self.messages.append(Message(
                ungettext_lazy(
                    'Successfully approved %i match.',
                    'Successfully approved %i matches.',
                    len(matches)) % len(matches),
                type=Message.SUCCESS
            ))
        elif not self.approve and len(prematches) > 0:
            self.messages.append(Message(
                ungettext_lazy(
                    'Successfully rejected %i match.',
                    'Successfully rejected %i matches.',
                    len(prematches)) % len(prematches),
                type=Message.SUCCESS
            ))

# AddMatchesForm: Form for adding matches (duh).
class AddMatchesForm(forms.Form):
    eventtext = StrippedCharField(max_length=200, required=False, label=_('Event'))
    date      = forms.DateField(required=True, label=_('Date'))
    game      = forms.ChoiceField(choices=GAMES, label=_('Game version'), initial=HOTS)
    offline   = forms.BooleanField(required=False, label=_('Offline'), initial=False)
    source    = StrippedCharField(max_length=1000, required=False, label=_('Source'))
    contact   = StrippedCharField(max_length=1000, required=False, label=_('Contact'))
    notes     = forms.CharField(max_length=10000, required=False, label=_('Notes'), initial='')
    matches   = forms.CharField(max_length=10000, required=True, label=_('Matches'), initial='')

    def __init__(self, is_adm, request=None):
        if request is not None:
            super(AddMatchesForm, self).__init__(request.POST)
            self.close_after = 'commit_close' in request.POST
            self.eobj = etn(lambda: request.POST['eventobj'])
        else:
            super(AddMatchesForm, self).__init__(initial={'date': date.today()})
            self.close_after = False

        self.requested_close_after = self.close_after

        self.label_suffix = ''
        self.is_adm = is_adm

        self.fields['eventobj'] = forms.ChoiceField(
            choices=[
                (e['id'], e['fullname']) for e in Event.objects.filter(closed=False)
                    .annotate(num_downlinks=Count('downlink'))
                    .filter(num_downlinks=1)
                    .order_by('idx')
                    .values('id', 'fullname')
            ],
            required=False, label=_('Event'),
        )

    # Validation
    def clean_eventtext(self):
        if self.is_adm:
            return self.cleaned_data['eventtext']
        if self.cleaned_data['eventtext'] in [None, '']:
            raise ValidationError(_('This field is required.'))
        return self.cleaned_data['eventtext']

    def clean_source(self):
        if self.is_adm:
            return self.cleaned_data['source']
        if self.cleaned_data['source'] in [None, '']:
            raise ValidationError(_('This field is required.'))
        return self.cleaned_data['source']

    def clean(self):
        if self.is_adm:
            try:
                self.cleaned_data['eventobj'] = Event.objects.get(id=int(self.eobj))
            except:
                raise ValidationError(_('Could not find this event object.'))
        return self.cleaned_data

    # Parse the matches
    def parse_matches(self, submitter):
        self.messages = []

        if not self.is_valid():
            self.messages.append(Message(_('Entered data was invalid, no changes made.'), type=Message.ERROR))
            for field, errors in self.errors.items():
                for error in errors:
                    self.messages.append(Message(error=error, field=self.fields[field].label))
            return []

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
                self.messages.append(Message(
                    _("Could not parse '%(line)s' (%(error)s).") % {'line': line, 'error': str(e)},
                    type=Message.ERROR
                ))
                self.close_after = False
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
                self.messages.append(Message(
                    _("Error creating match '%(line)s' (%(error)s).") % {'line': line, 'error': str(e)},
                    type=Message.ERROR
                ))
                self.close_after = False
                error_lines.append(line)
                continue

            if self.is_adm:
                match.submitter = submitter
            matches.append(match)

        for m in matches:
            m.save()
        if len(matches) > 0:
            self.messages.append(Message(
                ungettext_lazy(
                    'Successfully added %i match.',
                    'Successfully added %i matches.',
                    len(matches)) % len(matches),
                type=Message.SUCCESS
            ))

        if self.close_after:
            self.cleaned_data['eventobj'].close()
            self.messages.append(
                Message(_("Closed '%s'.") % self.cleaned_data['eventobj'].fullname, type=Message.SUCCESS))
        elif self.requested_close_after:
            self.messages.append(
                Message(_("Did not close '%s'.") % self.cleaned_data['eventobj'].fullname, type=Message.INFO))

        self.data = self.data.copy()
        self.data['matches'] = '\n'.join(error_lines)

        return matches

    # Auxiliary function for searching for players
    def get_player(self, query, make_flag):
        players = find_player(lst=query, make=make_flag, soft=False)

        if players.count() != 1:
            if self.is_adm:
                if players.count() == 0:
                    self.messages.append(
                        Message(_("Could not find player: '%s'.") % ' '.join(query), type=Message.ERROR))
                    self.close_after = False
                elif players.count() > 1:
                    self.messages.append(
                        Message(_("Ambiguous player: '%s'.") % ' '.join(query), type=Message.ERROR))
                    self.close_after = False
            return None

        return players.first()

    # Make matches (called from parse_matches). DOES NOT SAVE THEM.
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
                rca      = pla_race_or or (pla.race if pla.race != 'S' else 'R'),
                rcb      = plb_race_or or (plb.race if plb.race != 'S' else 'R'),
                date     = self.cleaned_data['date'],
                treated  = False,
                eventobj = self.cleaned_data['eventobj'],
                game     = self.cleaned_data['game'],
                offline  = self.cleaned_data['offline'],
            )
            if check_duplicates(match, dup_flag):
                self.messages.append(Message(
                    _("Could not make match %(pla)s vs %(plb)s: possible duplicate found.") 
                        % {'pla': pla.tag, 'plb': plb.tag},
                    type=Message.ERROR,
                ))
                self.close_after = False
                return None
            if 'R' in [match.rca, match.rcb]:
                self.messages.append(Message(
                    _("Unknown race in %(pla)s vs %(plb)s: set to random.")
                        % {'pla': pla.tag, 'plb': plb.tag},
                    type=Message.WARNING,
                ))
            match.set_period()
            match.set_ratings()
            return match

# Form for adding events.
class AddEventsForm(forms.Form):
    parent_id = forms.IntegerField(required=True, label=_('Parent ID'))
    predef_names = forms.ChoiceField([
        ('other', _('Other')),
        ('Group Stage, Playoffs', _('Group stage and playoffs')),
        ('Group A,Group B,Group C,Group D', _('Groups A through D')),
        ('Group A,Group B,Group C,Group D,Group E,Group F,Group G,Group H', _('Groups A through H')),
        ('Ro64,Ro32,Ro16,Ro8,Ro4,Final', _('Ro64→Final')),
        ('Ro32,Ro16,Ro8,Ro4,Final', _('Ro32→Final')),
        ('Ro16,Ro8,Ro4,Final', _('Ro16→Final')),
        ('Ro8,Ro4,Final', _('Ro8→Final')),
        ('Ro4,Final', _('Ro4→Final')),
        ('Ro64,Ro32,Ro16,Ro8,Ro4,Third place match,Final', _('Ro64→Final + 3rd place')),
        ('Ro32,Ro16,Ro8,Ro4,Third place match,Final', _('Ro32→Final + 3rd place')),
        ('Ro16,Ro8,Ro4,Third place match,Final', _('Ro16→Final + 3rd place')),
        ('Ro8,Ro4,Third place match,Final', _('Ro8→Final + 3rd place')),
        ('Ro4,Third place match,Final', _('Ro4→Final + 3rd place')),
        ('Early rounds,Ro64,Ro32,Ro16,Ro8,Ro4,Final', _('Ro64→Final + early rounds')),
        ('Early rounds,Ro32,Ro16,Ro8,Ro4,Final', _('Ro32→Final + early rounds')),
        ('Early rounds,Ro16,Ro8,Ro4,Final', _('Ro16→Final + early rounds')),
        ('Early rounds,Ro8,Ro4,Final', _('Ro8→Final + early rounds')),
        ('Early rounds,Ro4,Final', _('Ro4→Final + early rounds')),
        ('Early rounds,Ro64,Ro32,Ro16,Ro8,Ro4,Third place match,Final', 
            _('Ro64→Final + 3rd place and early rounds')),
        ('Early rounds,Ro32,Ro16,Ro8,Ro4,Third place match,Final', _('Ro32→Final + 3rd place and early rounds')),
        ('Early rounds,Ro16,Ro8,Ro4,Third place match,Final', _('Ro16→Final + 3rd place and early rounds')),
        ('Early rounds,Ro8,Ro4,Third place match,Final', _('Ro8→Final + 3rd place and early rounds')),
        ('Early rounds,Ro4,Third place match,Final', _('Ro4→Final + 3rd place and early rounds')),
        ('WB,LB,Final', _('WB, LB, Final')),
        ('Round 1,Round 2', _('LB: Round 1->Round 2')),
        ('Round 1,Round 2,Round 3,Round 4', _('LB: Round 1->Round 4')),
        ('Round 1,Round 2,Round 3,Round 4,Round 5,Round 6', _('LB: Round 1->Round 6')),
        ('Round 1,Round 2,Round 3,Round 4,Round 5,Round 6,Round 7,Round 8', _('LB: Round 1->Round 8')),
    ], required=True, label=_('Predefined names'))
    custom_names = StrippedCharField(max_length=400, required=False, label=_('Custom names'))
    type = forms.ChoiceField(choices=EVENT_TYPES, required=True, label=_('Type'))
    big = forms.BooleanField(required=False, label=_('Big'), initial=False)
    noprint = forms.BooleanField(required=False, label=_('No print'), initial=False)

    def __init__(self, request=None):
        if request is None:
            super(AddEventsForm, self).__init__()
        else:
            super(AddEventsForm, self).__init__(request.POST)
            if 'commit' in request.POST:
                self.action = 'add'
            else:
                self.action = 'close'

        self.label_suffix = ''

    # Custom validation
    def clean_parent_id(self):
        try:
            if int(self.cleaned_data['parent_id']) != -1:
                return Event.objects.get(id=int(self.cleaned_data['parent_id']))
            return None
        except:
            raise ValidationError(_('Could not find event ID %s.') % self.cleaned_data['parent_id'])

    def clean(self):
        if self.action != 'add':
            if self.cleaned_data['parent_id'] is None:
                raise ValidationError(_('Must specify an event to close.'))
            return self.cleaned_data

        if self.cleaned_data['predef_names'] == 'other' and self.cleaned_data['custom_names'] in ['', None]:
            raise ValidationError(_('No event names specified.'))

        names = (
            self.cleaned_data['predef_names']
            if self.cleaned_data['predef_names'] != 'other'
            else self.cleaned_data['custom_names']
        )

        self.cleaned_data['names'] = [s.strip() for s in names.split(',') if s.strip() != '']
        return self.cleaned_data

    # Commit changes
    def commit(self):
        ret = []

        if not self.is_valid():
            ret.append(Message(_('Entered data was invalid, no changes made.'), type=Message.ERROR))
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
            ret.append(Message(
                ungettext_lazy(
                    'Successfully created %i new event.',
                    'Successfully created %i new events.',
                    len(self.cleaned_data['names'])) % len(self.cleaned_data['names']),
                type=Message.SUCCESS)
            )
        elif self.action == 'close':
            self.cleaned_data['parent_id'].close()
            ret.append(Message(_('Successfully closed event.'), type=Message.SUCCESS))

        return ret

# Form for merging players.
class MergePlayersForm(forms.Form):
    source = forms.IntegerField(required=True, label=_('Source ID'))
    target = forms.IntegerField(required=True, label=_('Target ID'))
    confirm = forms.BooleanField(required=False, label=_('Confirm'), initial=False)

    def __init__(self, request=None):
        if request is not None:
            super(MergePlayersForm, self).__init__(request.POST)
        else:
            super(MergePlayersForm, self).__init__()
        self.label_suffix = ''

    # Validation
    def clean_source(self):
        try:
            return Player.objects.get(id=int(self.cleaned_data['source']))
        except:
            raise ValidationError(_('No player with ID %i.') % self.cleaned_data['source'])

    def clean_target(self):
        try:
            return Player.objects.get(id=int(self.cleaned_data['target']))
        except:
            raise ValidationError(_('No player with ID %i.') % self.cleaned_data['target'])

    # Do stuff
    def merge(self):
        ret = []

        if not self.is_valid():
            ret.append(Message(_('Entered data was invalid, no changes made.'), type=Message.ERROR))
            for field, errors in self.errors.items():
                for error in errors:
                    ret.append(Message(error=error, field=self.fields[field].label))
            return ret

        if not self.cleaned_data['confirm']:
            ret.append(Message(_('Please confirm player merge.'), type=Message.WARNING))
            return ret

        source, target = self.cleaned_data['source'], self.cleaned_data['target']

        Match.objects.filter(pla=source).update(pla=target, treated=False)
        Match.objects.filter(plb=source).update(plb=target, treated=False)
        Match.objects.filter(rta__player=source).update(rta=None)
        Match.objects.filter(rtb__player=source).update(rtb=None)

        try:
            recompute = Rating.objects.filter(player=source).earliest('period').period
            recompute.needs_recompute = True
            recompute.save()
        except:
            pass

        Rating.objects.filter(player=source).delete()
        GroupMembership.objects.filter(player=source).delete()
        Earnings.objects.filter(player=source).update(player=target)

        ret.append(Message(
            _('%(source)s was successfully merged into %(target)s.') % {
                'source': source.tag,
                'target': target.tag},
            # Translate: Merging of two players, this is a reference to the archon from SC:BW.
            title=_('The merging is complete'), type=Message.SUCCESS
        ))

        source.delete()

        return ret

# Form for merging players.
class MoveEventForm(forms.Form):
    subject = forms.IntegerField(required=True, label=_('Event ID to move'))
    target = forms.IntegerField(required=True, label=_('New parent ID'))
    confirm = forms.BooleanField(required=False, label=_('Confirm'), initial=False)

    def __init__(self, request=None):
        if request is not None:
            super(MoveEventForm, self).__init__(request.POST)
        else:
            super(MoveEventForm, self).__init__()
        self.label_suffix = ''

    # Validation
    def clean_subject(self):
        try:
            return Event.objects.get(id=int(self.cleaned_data['subject']))
        except:
            raise ValidationError(_('No event with ID %i.') % self.cleaned_data['subject'])

    def clean_target(self):
        try:
            return Event.objects.get(id=int(self.cleaned_data['target']))
        except:
            raise ValidationError(_('No event with ID %i.') % self.cleaned_data['target'])

    def clean(self):
        print(self.cleaned_data)
        if EventAdjacency.objects.filter(
            parent=self.cleaned_data['subject'],
            child=self.cleaned_data['target'],
        ).exists():
            raise ValidationError(_("Can't move an event to one of its descendants."))
        return self.cleaned_data

    # Do stuff
    def move(self):
        ret = []

        if not self.is_valid():
            ret.append(Message(_('Entered data was invalid, no changes made.'), type=Message.ERROR))
            for field, errors in self.errors.items():
                for error in errors:
                    if field == '__all__':
                        ret.append(Message(error, type=Message.ERROR))
                    else:
                        ret.append(Message(error=error, field=self.fields[field].label))
            return ret

        if not self.cleaned_data['confirm']:
            ret.append(Message(_('Please confirm event move.'), type=Message.WARNING))
            return ret

        subject, target = self.cleaned_data['subject'], self.cleaned_data['target']

        downlinks = EventAdjacency.objects.filter(parent=subject).select_related('child')
        child_ids = [dl.child_id for dl in downlinks]
        EventAdjacency.objects.filter(child_id__in=child_ids).exclude(parent_id__in=child_ids).delete()

        links = []
        for ul in EventAdjacency.objects.filter(child=target):
            for dl in downlinks:
                links.append(EventAdjacency(
                    parent_id = ul.parent_id,
                    child_id  = dl.child_id,
                    distance  = ul.distance + dl.distance + 1,
                ))
        EventAdjacency.objects.bulk_create(links)

        subject.parent = target
        subject.save()

        prevname = subject.fullname

        for dl in downlinks:
            if dl.child_id == subject.id:
                subject.update_name()  # select_related causes the parent to be overwritten otherwise
            else:
                dl.child.update_name()

        ret.append(Message(
            "Moved '%(source)s' to '%(target)s'. It's now called '%(name)s'." % {
                'source': prevname,
                'target': target.fullname,
                'name': subject.fullname,
            }, type=Message.SUCCESS
        ))

        return ret

# View for adding matches
def add_matches(request):
    base = base_ctx('Submit', 'Matches', request)
    login_message(base)

    if request.method == 'POST' and 'submit' in request.POST:
        form = AddMatchesForm(base['adm'], request=request)
        base['matches'] = display_matches(form.parse_matches(request.user), messages=False)
        base['messages'] += form.messages
    else:
        form = AddMatchesForm(base['adm'])
        try:
            get_event = Event.objects.get(id=request.GET['eventid'])
            if get_event.closed:
                get_event.open()
                base['messages'].append(Message(_("Reopened '%s'.") % get_event.fullname, type=Message.SUCCESS))
            form['eventobj'].field.choices.append((get_event.id, get_event.fullname))
            form['eventobj'].field.choices.sort(key=lambda e: e[1])
            base['event_override'] = get_event.id
        except:
            pass

    base['form'] = form

    return render_to_response('add.djhtml', base)

# View for reviewing matches
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
        g.prematches = display_matches(g.prematch_set.all(), messages=False, no_events=True)

    return render_to_response('review.djhtml', base)

# View for event manager
def events(request):
    base = base_ctx('Submit', 'Events', request)
    if not base['adm']:
        return redirect('/login/')
    login_message(base)

    base['messages'].append(Message(
        _("If you haven't used this tool before, ask before you do anything."), type=Message.WARNING))

    if request.method == 'POST':
        form = AddEventsForm(request=request)
        base['messages'] += form.commit()
    else:
        form = AddEventsForm()

    base['form'] = form

    # Build event list
    root_events = (
        Event.objects.filter(downlink__child__closed=False)
                     .filter(parent__isnull=True)
                     .order_by('idx')
                     .distinct()
    )

    subtreemap = {
        e.id: []
        for e in root_events
    }

    tree = [{ 
        'event': e,
        'subtree': subtreemap[e.id],
        'inc': 0,
    } for e in root_events]

    events = root_events
    while events:
        events = (
            Event.objects.filter(downlink__child__closed=False)
                         .filter(parent__in=events)
                         .order_by('idx')
                         .distinct()
        )

        for e in events:
            subtreemap[e.id] = []
            subtreemap[e.parent_id].append({
                'event': e,
                'subtree': subtreemap[e.id],
                'inc': 0,
            })

    base['tree'] = []

    def do_level(level, indent):
        for e in level:
            e['indent'] = indent
            base['tree'].append(e)
            if e['subtree']:
                base['tree'][-1]['inc'] += 1
                do_level(e['subtree'], indent+1)
                base['tree'][-1]['inc'] -= 1

    do_level(tree, 0)

    return render_to_response('eventmgr.djhtml', base)

# Auxiliary view called by JS code in the event manager for progressively opening subtrees
def event_children(request, id):
    event = Event.objects.get(id=id)
    ret = [dict(q) for q in
        event.get_immediate_children().filter(closed=False)
            .order_by('name')
            .values('id','type','name','fullname')
    ]

    depth = ntz(event.uplink.aggregate(Max('distance'))['distance__max'])

    for q in ret:
        q['has_subtree'] = (
            Event.objects.filter(uplink__parent_id=q['id'], uplink__distance=1, closed=False).exists()
        )
        q['uplink__distance__max'] = depth + 1

    return HttpResponse(json.dumps(ret))

# Event overview
def open_events(request):
    base = base_ctx('Submit', 'Open events', request)
    if not base['adm']:
        return redirect('/login/')
    login_message(base)

    # Handle modifications
    if base['adm'] and 'open_games' in request.POST:
        ids = [int(i) for i in request.POST.getlist('open_games_ids')]
        for id in ids:
            Event.objects.get(id=id).close()
        base['messages'].append(Message(
            ungettext_lazy(
                'Successfully closed %i event.',
                'Successfully closed %i events.',
                len(ids)) % len(ids),
            type=Message.SUCCESS
        ))
    elif base['adm'] and 'pp_events' in request.POST:
        ids = [int(i) for i in request.POST.getlist('pp_events_ids')]
        nevents = Event.objects.filter(id__in=ids).update(prizepool=False)
        base['messages'].append(Message(
            ungettext_lazy(
                'Successfully marked %i event as having no prize pool.',
                'Successfully marked %i events as having no prize pool.',
                nevents) % nevents,
            type=Message.SUCCESS
        ))

    # Open events with games
    base['open_games'] = (
        Event.objects.filter(type=TYPE_EVENT, closed=False)
            .filter(downlink__child__match__isnull=False)
            .distinct()
            .prefetch_related('uplink__parent')
            .order_by('latest', 'idx', 'fullname')
    )

    # Open events without games
    base['open_nogames'] = (
        Event.objects.filter(type=TYPE_EVENT, closed=False)
            .exclude(id__in=Event.objects.filter(downlink__child__match__isnull=False).distinct())
            .distinct()
            .exclude(id=2)
            .prefetch_related('uplink__parent')
            .order_by('fullname')
    )

    # Closed non-team events with unknown prizepool status.
    base['pp_events'] = (
        Event.objects.filter(type=TYPE_EVENT, prizepool__isnull=True)
            .filter(match__isnull=False, closed=True)
            .exclude(uplink__parent__category=CAT_TEAM)
            .distinct()
            .prefetch_related('uplink__parent')
            .order_by('idx', 'fullname')
    )

    fill_aux_event(base['open_games'])
    fill_aux_event(base['open_nogames'])
    fill_aux_event(base['pp_events'])

    return render_to_response('events_open.djhtml', base)

class PlayerInfoForm(forms.Form):
    id = forms.IntegerField(required=True)
    name = StrippedCharField(required=False, label=_('Name'))
    romanized_name = StrippedCharField(
        required=False,
        label=_('Romanized name')
    )
    birthday = forms.DateField(required=False, label=_('Birthday'))
    country = forms.ChoiceField(
        choices=data.countries,
        required=False,
        label=_('Country')
    )

    def commit(self):
        data = dict(self.cleaned_data)
        player = Player.objects.get(id=data['id'])

        for k, v in data.items():
            if getattr(player, k) != v:
                setattr(player, k, v)
                print(k, v)

        player.save()

        return player

def player_info(request, choice=None):
    base = base_ctx('Submit', 'Player Info', request)
    if not base['adm']:
        return redirect('/login/')
    login_message(base)

    if request.method == 'POST':
        form = PlayerInfoForm(request.POST)
        if form.is_valid():
            player = form.commit()
            base['messages'].append(
                Message(
                    # Translators: Updated a player
                    text=_("Updated %s") % player_filter(player),
                    type=Message.SUCCESS
                )
            )

    page = 1
    if 'page' in request.GET:
        try:
            page = int(request.GET['page'])
        except:
            pass
    country = 'all' if 'country' not in request.GET else request.GET['country']
    base['country'] = country
    base['countries'] = country_list(Player.objects.all())

    if country == 'all':
        all_count = Player.objects.count()
    else:
        all_count = Player.objects.filter(country=country).count()
    base["all_count"] = all_count
    q = Player.objects.all()
    if country != 'all':
        q = q.filter(country=country)

    queries = {
        'birthday': q.filter(birthday__isnull=True),
        'name': q.filter(name__isnull=True),
        'country': q.filter(country__isnull=True)
    }

    base["subnav"] = [(_('Progress'), '/add/player_info/')]

    if all_count == 0:
        base['no_players'] = True
    elif choice is not None and choice in ('birthday', 'name', 'country'):
        q = queries[choice].extra(select=EXTRA_NULL_SELECT)\
                           .order_by(
                               "-null_curr",
                               "-current_rating__rating",
                               "id"
                           )
        base["players"] = q[(page-1)*50:page*50]
        base["page"] = page
        base["next_page"] = q.count() > page * 50
        base["form"] = PlayerInfoForm()
    else:
        values = dict()
        for k, v in queries.items():
            c = all_count - v.count()
            values[k] = {
                'count': c,
                'pctg': '%.2f' % (100*float(c)/float(all_count))
            }

        values["birthday"]["title"] = _("Players with birthday")
        values["name"]["title"] = _("Players with name")
        values["country"]["title"] = _("Players with country")

        base["values"] = list(values.items())
        base["values"].sort(key=lambda x: x[0])

    return render_to_response('player_info.djhtml', base)

# Helper view for grabbing LP-info
def player_info_lp(request):
    base = base_ctx('Submit', 'Player Info', request)
    if not base['adm']:
        return HttpResponse(status=403)

    if 'title' not in request.GET:
        return JsonResponse({"message": "Missing title"})

    return player_info_lp_helper(request.GET['title'])

def player_info_lp_helper(title):
    API_URL_BASE = (
        "http://wiki.teamliquid.net/starcraft2/api.php?"
        "format=json&"
        "action=query&"
        "titles={title}&"
        "prop=revisions&"
        "rvprop=content"
    )
    def get_lp_api_url(page_title):
        return API_URL_BASE.format(title=page_title)

    req = Request(get_lp_api_url(title))
    resp = urlopen(req)

    text = UnicodeDammit(resp.read()).unicode_markup
    data = json.loads(text)

    pages = list(data["query"]["pages"].items())
    page = pages[0][1]
    raw_text = page["revisions"][0]["*"]

    m = re.match(r"#REDIRECT(?:\s*)\[\[(.*?)\]\]", raw_text)
    if m is not None:
        return player_info_lp_helper(m.group(1))

    mw = parsemw(raw_text)

    def get_birthday(code):
        for t in code.ifilter_templates():
            if t.name.matches("Birth date and age"):
                return "{}-{}-{}".format(
                    *[str(t.get(i)).strip() for i in range(1, 4)]
                )

    for t in mw.ifilter_templates():
        if t.name.matches('Infobox Player 2'):
            return_data = dict()
            if t.has('birth_date', ignore_empty=True):
                return_data['birthday'] = (
                    get_birthday(t.get('birth_date').value)
                )
            if t.has('name', ignore_empty=True):
                return_data['name'] = (
                    str(t.get('name').value).strip()
                )
            if t.has('romanized_name', ignore_empty=True):
                return_data['romanized_name'] = (
                    str(t.get('romanized_name').value).strip()
                )
            return JsonResponse({"message": "Success", "data": return_data})
    return JsonResponse({"message": "No data found"})

# Misc staff tools
def misc(request):
    base = base_ctx('Submit', 'Misc', request)
    if not base['adm']:
        return redirect('/login/')
    login_message(base)

    mergeform = (
        MergePlayersForm(request=request)
        if request.method == 'POST' and 'merge' in request.POST
        else MergePlayersForm()
    )
    moveform = (
        MoveEventForm(request=request)
        if request.method == 'POST' and 'move' in request.POST
        else MoveEventForm()
    )

    if mergeform.is_bound:
        base['messages'] += mergeform.merge()
    if moveform.is_bound:
        base['messages'] += moveform.move()

    base.update({
        'mergeform':  mergeform,
        'moveform':   moveform,
    })

    return render_to_response('manage.djhtml', base)
