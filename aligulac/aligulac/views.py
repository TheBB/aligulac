# {{{ Imports
from datetime import datetime
from itertools import zip_longest
import os

from django import forms
from django.contrib.auth import logout
from django.contrib.auth.models import User
from django.db.models import (
    Count,
    Q,
)
from django.http import HttpResponseNotFound
from django.shortcuts import (
    redirect,
    render_to_response,
)
from django.template.loader import render_to_string
from django.utils.translation import ugettext_lazy as _

from aligulac.cache import cache_page
from aligulac.settings import (
    DUMP_PATH,
    PROJECT_PATH,
    LANGUAGES,
)
from aligulac.tools import (
    base_ctx,
    get_param,
    login_message,
    JsonResponse,
    Message,
    StrippedCharField,
    search as tools_search,
)

from blog.models import Post

from ratings.models import (
    APIKey,
    Event,
    Group,
    HOTS,
    LOTV,
    Match,
    Player,
    Rating,
    WOL,
)
from ratings.templatetags.ratings_extras import urlfilter
from ratings.tools import (
    count_winloss_games,
    filter_active,
    populate_teams,
)
# }}}

# {{{ DB table specification
DBTABLES = [{
        'name': 'player',
        'desc': _('Contains player information.'),
        'cols': [
            ('id', 'integer not null', _('primary key')),
            ('tag', 'character varying(30) not null', _('in-game name of the player')),
            ('name', 'character varying(100)', _('real name')),
            ('birthday', 'date', _('birthday')),
            ('mcnum', 'integer', _('MC number')),
            ('tlpd_id', 'integer', _('external TLPD ID')),
            ('tlpd_db', 'integer', 
                _('bit-flag value denoting which TLPD databases this player is in ('
                  '1 = KR WoL, 2 = IN WoL, 4 = HotS, 8 = HotS beta, 16 = WoL beta)')),
            ('lp_name', 'integer', 
                _('title of Liquipedia page ('
                  'the part after http://wiki.teamliquid.net/starcraft2/)')),
            ('sc2e_id', 'integer', _('external sc2earnings.com ID')),
            ('country', 'character varying(2)', _('ISO-3166-1 alpha-2 country code')),
            ('race', 'character varying(1) not null', 
                _('P, T or Z for normal races, R for random and S for race switcher')),
            ('dom_val', 'double precision', 
                _('their PP score (' +
                  'see <a href="%s">Hall of Fame</a> for explanation)') % '/results/hof/'),
            ('dom_start_id', 'integer', _('foreign key to period (start of PP-period)')),
            ('dom_end_id', 'integer', _('foreign key to period (first period after end of PP-period)')),
            ('current_rating_id', 'integer', 
                # Translators: rating is a table name and must be in English
                _('foreign key to rating ('
                  'should link to the latest published rating of the player)')),
        ]
    }, {
        'name': 'match',
        'desc': _('Contains game information.'),
        'cols': [
            ('id', 'integer not null', _('primary key')),
            ('period_id', 'integer not null',
                # Translators: period is a table name and must be in English
                _('foreign key to period (the period this match was played in)')),
            ('date', 'date not null', _('when the match was played (often approximate)')),
            ('pla_id', 'integer not null', _('foreign key to player (player A)')),
            ('plb_id', 'integer not null', _('foreign key to player (player B)')),
            ('sca', 'smallint not null', _('score for player A')),
            ('scb', 'smallint not null', _('score for player B')),
            ('rca', 'character varying(1) not null', 
                _('race for player A ('
                  'not necessarily same as pla.race, S is not allowed)')),
            ('rcb', 'character varying(1) not null', 
                _('race for player B ('
                  'not necessarily same as plb.race, S is not allowed)')),
            ('treated', 'boolean not null', _('true if the match has been rated')),
            ('event', 'character varying(200) not null', 
                _('tournament, round, group etc. ('
                  'superceded by eventobj_id if latter is not null)')),
            # Translators: event is a table name and must be in English
            ('eventobj_id', 'integer', _('foreign key to event (supercedes event field)')),
            ('submitter_id', 'integer', _('foreign key to a table removed from the dump')),
            ('game', 'character varying(200) not null', _('game version used (WoL, HotS, LotV)')),
            ('offline', 'boolean not null', _('whether this match was played offline')),
            ('rta_id', 'integer', 
                # Translators: rating is a table name and must be in English
                _('foreign key to rating ('
                  'rating of player A at the time of the match)')),
            ('rtb_id', 'integer', 
                # Translators: rating is a table name and must be in English
                _('foreign key to rating ('
                  'rating of player B at the time of the match)')),
        ]
    }, {
        'name': 'event',
        'desc': _(
            'Contains event information. Events are organized in a tree as defined by the <strong>'
            'eventadjacency</strong> table. “Event” in this case means anything from organizer, season, '
            'tournament, round (including qualifiers), group, days and weeks, etc.'),
        'cols': [
            ('id', 'integer not null', _('primary key')),
            ('name', 'character varying(100) not null', _('name of this node')),
            ('parent_id', 'integer', _('parent node')),
            ('lft', 'integer', _('deprecated')),
            ('rgt', 'integer', _('deprecated')),
            ('closed', 'boolean not null', _('whether the event is finished or not')),
            ('big', 'boolean not null', _('whether the event is considered large (many games)')),
            ('noprint', 'boolean not null', 
                _('whether this event should be skipped in the fullname of descendants')),
            ('fullname', 'character varying(500) not null', 
                _('full name of this event (including names of ancestors)')),
            ('homepage', 'character varying(200)', _('URL of the event website')),
            ('lp_name', 'character varying(200)', 
                _('title of Liquipedia page ('
                  'the part after http://wiki.teamliquid.net/starcraft2/)')),
            ('tlpd_id', 'integer', _('external TLPD ID')),
            ('tlpd_db', 'integer', 
                _('bit-flag value denoting which TLPD databases this event is in: ('
                  '1 = KR WoL, 2 = IN WoL, 4 = HotS, 8 = HotS beta, 16 = WoL beta)')),
            ('tl_thread', 'integer', _('TL.net forum thread ID')),
            ('prizepool', 'boolean', _('whether this event has an associated prizepool (NULL if unknown)')),
            ('earliest', 'date', _('date of earliest match')),
            ('latest', 'date', _('date of latest match')),
            ('category', 'character varying(50)',
                # Translators: These are literals so must be in English, i.e. team (translation)…
                _('team, individual or frequent (only set for root nodes)')),
            ('type', 'character varying(50) not null', 
                # Translators: These are literals so must be in English, i.e. category (translation)…
                _('category, event (i.e. tournament) or round ('
                  'you can assume that ancestors of events are always categories and that descendants of '
                  'events are always rounds)')),
            ('idx', 'integer not null', _('sorting index')),
        ]
    }, {
        'name': 'eventadjacency',
        'desc': _(
            'Contains the tree information for events. There is a row here for every ancestor-descendant '
            'relationship. This table contains the transitive closure, so links of any distance are listed.'),
        'cols': [
            ('id', 'integer not null', _('primary key')),
            # Translators: event is a table name and must be in English
            ('parent_id', 'integer not null', _('foreign key to event')),
            # Translators: event is a table name and must be in English
            ('child_id', 'integer not null', _('foreign key to event')),
            ('distance', 'integer', _('how many edges between the nodes')),
        ]
    }, {
        'name': 'rating',
        'desc': _('Contains rating information.'),
        'cols': [
            ('id', 'integer not null', _('primary key')),
            # Translators: period is a table name and must be in English
            ('period_id', 'integer not null', _('foreign key to period')),
            # Translators: player is a table name and must be in English
            ('player_id', 'integer not null', _('foreign key to player')),
            ('rating', 'double precision not null', _('current rating')),
            ('rating_vp', 'double precision not null', _('current rating delta vP')),
            ('rating_vt', 'double precision not null', _('current rating delta vT')),
            ('rating_vz', 'double precision not null', _('current rating delta vZ')),
            # Translators: RD = Rating Deviation
            ('dev', 'double precision not null', _('current RD')),
            ('dev_vp', 'double precision not null', _('current RD vP')),
            ('dev_vt', 'double precision not null', _('current RD vT')),
            ('dev_vz', 'double precision not null', _('current RD vZ')),
            ('comp_rat', 'double precision', _('performance rating in this period')),
            ('comp_rat_vp', 'double precision', _('performance rating vP in this period')),
            ('comp_rat_vz', 'double precision', _('performance rating vT in this period')),
            ('comp_rat_vt', 'double precision', _('performance rating vZ in this period')),
            ('bf_rating', 'double precision not null', _('smoothed rating')),
            ('bf_rating_vp', 'double precision not null', _('smoothed rating vP')),
            ('bf_rating_vt', 'double precision not null', _('smoothed rating vT')),
            ('bf_rating_vz', 'double precision not null', _('smoothed rating vZ')),
            ('bf_dev', 'double precision', _('smoothed RD')),
            ('bf_dev_vp', 'double precision', _('smoothed RD vP')),
            ('bf_dev_vt', 'double precision', _('smoothed RD vZ')),
            ('bf_dev_vz', 'double precision', _('smoothed RD vT')),
            ('position', 'integer', _('rank')),
            ('position_vp', 'integer', _('rank vP')),
            ('position_vt', 'integer', _('rank vT')),
            ('position_vz', 'integer', _('rank vZ')),
            ('decay', 'integer not null', _('number of periods since last game')),
            ('domination', 'double precision', 
                _('rating gap to number 7 ('
                  'used in the <a href="%s">Hall of Fame</a>)') % '/recods/hof/'),
            # Translators: rating is a table name and must be in English
            ('prev_id', 'integer', _('foreign key to rating; previous rating for this player')),
        ]
    }, {
        'name': 'period',
        'desc': _('A period represent a discrete time interval used for rating computation purposes.'),
        'cols': [
            ('id', 'integer not null', _('primary key')),
            ('start', 'date', _('starting date (inclusive)')),
            ('end', 'date', _('ending date (inclusive)')),
            ('computed', 'boolean not null', _('whether this period has been rated')),
            ('needs_recompute', 'boolean not null', 
                _('whether this period needs re-rating (something has changed)')),
            ('num_retplayers', 'integer not null', _('number of returning players')),
            ('num_newplayers', 'integer not null', _('number of new players')),
            ('num_games', 'integer not null', _('number of games played')),
            ('dom_p', 'double precision', _('OP-score for Protoss')),
            ('dom_t', 'double precision', _('OP-score for Terran')),
            ('dom_p', 'double precision', _('OP-score for Zerg')),
        ]
    }, {
        'name': 'group',
        'desc': _('Contains group information (for now, this means teams).'),
        'cols': [
            ('id', 'integer not null', _('primary key')),
            ('name', 'character varying (100) not null', _('name of group')),
            ('shortname', 'character varying (25)', _('short name of group')),
            ('scoreak', 'double precision', _('all-kill score (if team)')),
            ('scorepl', 'double precision', _('proleague score (if team)')),
            ('founded', 'date', _('date founded')),
            ('disbanded', 'date', _('date disbanded')),
            ('active', 'boolean not null', _('whether the group is active')),
            ('homepage', 'character varying (200)', _('URL of team website')),
            ('lp_name', 'character varying (200)', 
                _('title of Liquipedia page ('
                  'the part after http://wiki.teamliquid.net/starcraft2/)')),
            ('is_team', 'boolean not null', _('whether this group is a proper team')),
            ('is_manual', 'boolean not null', 
                _('whether this group has manually added members or not ('
                  'currently has no effect, there are no automatic groups)')),
        ]
    }, {
        'name': 'groupmembership',
        'desc': _('Links teams and players together in a many-to-many relationship.'),
        'cols': [
            ('id', 'integer not null', _('primary key')),
            # Translators: player is a table name and must be in English
            ('player_id', 'integer not null', _('foreign key to player')),
            # Translators: group is a table name and must be in English
            ('group_id', 'integer not null', _('foreign key to group')),
            ('start', 'date', _('start date of membership')),
            ('end', 'date', _('end date of membership')),
            ('current', 'boolean not null',
                _('whether the membership is in effect ('
                  'many end dates are unknown, so this is needed)')),
            ('playing', 'boolean not null',
                _('whether the player is a playing member ('
                  'false for coaches, among others)')),
        ]
    }, {
        'name': 'earnings',
        'desc': _('Contains prize pool information. Each row represents a single payout to a single player.'),
        'cols': [
            ('id', 'integer not null', _('primary key')),
            # Translators: event is a table name and must be in English
            ('event_id', 'integer not null', _('foreign key to event')),
            # Translators: player is a table name and must be in English
            ('player_id', 'integer not null', _('foreign key to player')),
            ('earnings', 'integer', _('amount in USD at the time of the win')),
            ('origearnings', 'numeric(20,8)', _('amount in original currency')),
            ('currency', 'character varying(30) not null', _('currency code')),
            ('placement', 'integer not null', _('place in the event')),
        ]
    }, {
        'name': 'alias',
        'desc': _('Contains aliases for teams and players (common nicknames and shortened names.)'),
        'cols': [
            ('id', 'integer not null', _('primary key')),
            ('name', 'character varying(100)', _('the alias')),
            # Translators: player is a table name and must be in English
            ('player_id', 'integer', _('foreign key to player')),
            # Translators: group is a table name and must be in English
            ('group_id', 'integer', _('foreign key to group')),
        ]
    }, {
        'name': 'message',
        'desc': _('Contains messages associated with some objects, containing perhaps relevant information.'),
        'cols': [
            ('id', 'integer not null', _('primary key')),
            # Translator: These are literals so must be in English: info (translation), etc.
            ('type', 'character varying(10) not null', _('info, warning, sucess or error')),
            ('message', 'character varying(1000) not null', _('text describing this message')),
            ('params', 'character varying(1000) not null', _('parameters for string interpolation')),
            # Translators: player is a table name and must be in English
            ('player_id', 'integer', _('foreign key to player')),
            # Translators: event is a table name and must be in English
            ('event_id', 'integer', _('foreign key to event')),
            # Translators: group is a table name and must be in English
            ('group_id', 'integer', _('foreign key to group')),
            # Translators: match is a table name and must be in English
            ('match_id', 'integer', _('foreign key to match')),
        ]
    }, {
        'name': 'story',
        'desc': _('Contains stories (dots plotted in some players\' rating charts.)'),
        'cols': [
            ('id', 'integer not null', _('primary key')),
            ('player_id', 'integer not null', _('foreign key to player')),
            ('message', 'character varying(1000) not null', _('text describing this story')),
            ('params', 'character varying(1000) not null', _('parameters for string interpolation')),
            ('date', 'date not null', _('when it happened')),
            # Translators: event is a table name and must be in English
            ('event_id', 'integer', _('foreign key to event (if applicable)')),
        ]
    },
]
# }}}

# {{{ Home page
@cache_page
def home(request):
    base = base_ctx(request=request)

    if request.LANGUAGE_CODE != 'en':
        base['messages'].append(Message(
            _('The blog/news section is only in English, sorry.'),
            type=Message.INFO,
        ))

    entries = filter_active(Rating.objects.filter(period=base['curp']))\
              .order_by('-rating')\
              .select_related('player', 'prev')[0:10]

    entries = populate_teams(entries)

    blogs = Post.objects.order_by('-date')[0:3]

    base.update({
        'entries': entries,
        'blogposts': blogs
    })

    return render_to_response('index.djhtml', base)
# }}}

# {{{ Language change page
def language(request):
    base = base_ctx(request=request)

    base['languages'] = LANGUAGES

    return render_to_response('language.djhtml', base)
# }}}

# {{{ db view
@cache_page
def db(request):
    base = base_ctx('About', 'Database', request)

    base.update({
        'nmatches':      Match.objects.all().count(),
        'nuntreated':    Match.objects.filter(treated=False).count(),
        'ngames':        sum(count_winloss_games(Match.objects.all())),

        'nwol':          Match.objects.filter(game=WOL).count(),
        'nhots':         Match.objects.filter(game=HOTS).count(),
        'nlotv':         Match.objects.filter(game=LOTV).count(),
        'nwolgames':     sum(count_winloss_games(Match.objects.filter(game=WOL))),
        'nhotsgames':    sum(count_winloss_games(Match.objects.filter(game=HOTS))),
        'nlotvgames':    sum(count_winloss_games(Match.objects.filter(game=LOTV))),

        'nonline':       Match.objects.filter(offline=False).count(),
        'nonlinegames':  sum(count_winloss_games(Match.objects.filter(offline=False))),

        'npartial':      Match.objects.exclude(eventobj__isnull=True, event='').count(),
        'nfull':         Match.objects.filter(eventobj__isnull=False).count(),

        'nplayers':      Player.objects.all().count(),
        'nkoreans':      Player.objects.filter(country='KR').count(),
        'nteams':        Group.objects.filter(is_team=True).count(),
        'nactive':       Group.objects.filter(active=True, is_team=True).count(),

        'submitters':    [
            u for u in User.objects.all().annotate(nmatches=Count('match')).order_by('-nmatches')
            if u.nmatches > 0
        ],

        'dump':          os.path.exists(DUMP_PATH),
        'updated':       datetime.fromtimestamp(os.stat(PROJECT_PATH + 'update').st_mtime),

        'dbtables':      DBTABLES,
    })

    base.update({
        'noffline':       base['nmatches'] - base['nonline'],
        'nofflinegames':  base['ngames']   - base['nonlinegames'],
        'nuncatalogued':  base['nmatches'] - base['nfull'],
        'ninactive':      base['nteams']   - base['nactive'],
    })

    if base['dump']:
        stat = os.stat(os.path.join(DUMP_PATH, 'aligulac.sql'))
        base.update({
            'megabytes':  stat.st_size / 1048576,
            'modified':   datetime.fromtimestamp(stat.st_mtime),
        })
        stat = os.stat(os.path.join(DUMP_PATH, 'aligulac.sql.gz'))
        base.update({
            'gz_megabytes':  stat.st_size / 1048576
        })

    return render_to_response('db.djhtml', base)
# }}}

# {{{ API documentation and keys
class APIKeyForm(forms.Form):
    organization = StrippedCharField(max_length=200, required=True, label=_('Name/organization'))
    contact = forms.EmailField(max_length=200, required=True, label=_('Contact'))

    # {{{ Constructor
    def __init__(self, request=None, player=None):
        if request is not None:
            super(APIKeyForm, self).__init__(request.POST)
        else:
            super(APIKeyForm, self).__init__()

        self.label_suffix = ''
    # }}}

    # {{{ add_key: Adds key if valid, returns messages
    def add_key(self):
        ret = []

        if not self.is_valid():
            ret.append(Message(_('Entered data was invalid.'), type=Message.ERROR))
            for field, errors in self.errors.items():
                for error in errors:
                    ret.append(Message(error=error, field=self.fields[field].label))
            return ret

        key = APIKey(
            organization=self.cleaned_data['organization'],
            contact=self.cleaned_data['contact'],
            requests=0
        )

        key.generate_key()
        key.save()

        ret.append(Message(
            _("Your API key is <code>%s</code>. Please keep it safe.") % key.key, type=Message.SUCCESS))

        return ret
# }}}

def api(request):
    base = base_ctx('About', 'API', request)

    if request.LANGUAGE_CODE != 'en':
        base['messages'].append(Message(
            _('The API documentation is only in English, sorry.'),
            type=Message.INFO,
        ))

    if request.method == 'POST':
        form = APIKeyForm(request)
        base['messages'] += form.add_key()
    else:
        form = APIKeyForm()

    base.update({'form': form})

    return render_to_response('api.djhtml', base)
# }}}

# {{{ search view
@cache_page
def search(request):
    base = base_ctx(request=request)

    query = get_param(request, 'q', '')
    results = tools_search(query)
    if results is None:
        return redirect('/')

    players, teams, events = results

    # {{{ Redirect if only one hit
    if   players.count() == 1 and teams.count() == 0 and events.count() == 0:
        return redirect('/players/%i-%s/' % (players.first().id, urlfilter(players.first().tag)))
    elif players.count() == 0 and teams.count() == 1 and events.count() == 0:
        return redirect('/teams/%i-%s/' % (teams.first().id, urlfilter(teams.first().name)))
    elif players.count() == 0 and teams.count() == 0 and events.count() == 1:
        return redirect('/results/events/%i-%s/' % (events.first().id, urlfilter(events.first().fullname)))
    # }}}

    base.update({
        'results':  zip_longest(players, teams, events, fillvalue=None),
        'players':  players,
        'teams':    teams,
        'events':   events,
        'query':    query,
    })

    return render_to_response('search.djhtml', base)
# }}}

# {{{ auto-complete search view
EXTRA_NULL_SELECT = {
    'null_curr': 'CASE WHEN player.current_rating_id IS NULL THEN 0 ELSE 1 END'
}
@cache_page
def auto_complete_search(request):
    query = get_param(request, 'q', '')
    search_for = get_param(request, 'search_for', 'players,teams,events')
    search_for = search_for.split(',')

    results = tools_search(query, search_for, strict=True)

    data = {}
    if results is None:
        return JsonResponse(data)

    players, teams, events = results

    if players is not None:
        players = players.extra(select=EXTRA_NULL_SELECT)\
                         .order_by("-null_curr", "-current_rating__rating")

        num = 5 if teams is not None or events is not None else 10
        data['players'] = [{
            "id": p.id,
            "tag": p.tag,
            "race": p.race,
            "country": p.country,
            "aliases": [a.name for a in p.alias_set.all()],
            "teams": [
                (t.group.name, t.group.shortname)
                for t in p.groupmembership_set.filter(
                        current=True,
                        group__is_team=True
                )]
        } for p in players[:num]]

    if teams is not None:
        teams = teams.order_by('name')

        num = 5 if players is not None or events is not None else 10
        data['teams'] = [{
            "id": t.id,
            "name": t.name
            } for t in teams[:num]]

    if events is not None:
        events = events.order_by("fullname")

        num = 5 if players is not None or teams is not None else 10
        data['events'] = [{
            "id": e.id,
            "fullname": e.fullname
            } for e in events[:num]]

    return JsonResponse(data)
# }}}

# {{{ Login, logout and change password
def login_view(request):
    base = base_ctx(request=request)
    login_message(base)

    return render_to_response('login.djhtml', base)

def logout_view(request):
    logout(request)
    return redirect('/login/')

def changepwd(request):
    if not request.user.is_authenticated():
        return redirect('/login/')

    base = base_ctx(request=request)
    login_message(base)

    if not ('old' in request.POST and 'new' in request.POST and 'newre' in request.POST):
        return render_to_response('changepwd.djhtml', base)

    if not request.user.check_password(request.POST['old']):
        base['messages'].append(
            Message(_("The old password didn't match. Your password was not changed."), type=Message.ERROR)
        )
        return render_to_response('changepwd.djhtml', base)

    if request.POST['new'] != request.POST['newre']:
        base['messages'].append(
            Message(_("The new passwords didn't match. Your password was not changed."), type=Message.ERROR)
        )
        return render_to_response('changepwd.djhtml', base)

    request.user.set_password(request.POST['new'])
    request.user.save()
    base['messages'].append(
        Message(_('The password for %s was successfully changed.') % request.user.username, type=Message.SUCCESS)
    )

    return render_to_response('changepwd.djhtml', base)
# }}}

# {{{ Error handlers
@cache_page
def h404(request):
    base = base_ctx(request=request)
    return HttpResponseNotFound(render_to_string('404.djhtml', base))

@cache_page
def h500(request):
    base = base_ctx(request=request)
    return HttpResponseNotFound(render_to_string('500.djhtml', base))
# }}}
