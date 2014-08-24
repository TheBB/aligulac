# {{{ Imports
from itertools import chain
import json
import random
import shlex
import string
from datetime import (
    date, 
    datetime,
)

from django import forms
from django.contrib.auth import (
    authenticate,
    login,
)
from django.core.context_processors import csrf
from django.db.models import Q, F
from django.http import HttpResponse
from django.template.loader import render_to_string
from django.views.decorators.csrf import csrf_protect

from aligulac.cache import cache_page
from aligulac.settings import DEBUG

from ratings.models import (
    Earnings,
    Event,
    Group,
    Player,
    Rating,
    TYPE_CATEGORY,
    TYPE_EVENT,
    TYPE_ROUND
)
from ratings.tools import get_latest_period, find_player
from ratings.templatetags.ratings_extras import urlfilter
from django.utils.translation import ugettext as _
# }}}

# {{{ JsonResponse
# Works similarily to HttpResponse but returns JSON instead.
class JsonResponse(HttpResponse):

    def __init__(self, content, *args, **kwargs):
        scontent = json.dumps(content)

        if "content_type" not in kwargs:
            kwargs["content_type"] = "application/json"

        super().__init__(scontent, *args, **kwargs)
# }}}


# {{{ Message
# This class encodes error/success/warning messages sent to the templates.
# context['messages'] should point to a list of Message objects.
class Message:
    WARNING = 'warning'
    ERROR = 'error'
    INFO = 'info'
    SUCCESS = 'success'

    def __init__(self, text=None, title='', type='info', error=None, field=None, msg=None):
        if error is None and msg is None:
            self.title = title
            self.text = text
            self.type = type
        elif msg is not None:
            self.title = msg.get_title()
            self.text = msg.get_message()
            self.type = type or msg.type
        else:
            self.title = None
            self.text = field + ': ' + error
            self.type = self.ERROR
        self.id = ''.join([random.choice(string.ascii_letters+string.digits) for _ in range(10)])
# }}}

# {{{ NotUniquePlayerMessage
class NotUniquePlayerMessage(Message):

    def __init__(self, search, players, update=None, updateline=None, type='error'):
        id = ''.join([random.choice(string.ascii_letters+string.digits) for _ in range(10)])

        ctx = dict()
        ctx['msg_id'] = id
        player_list = list(
            chain(
                players.filter(current_rating__isnull=False)
                  .order_by('-current_rating__rating'),
                players.filter(current_rating__isnull=True)
                  .order_by('tag')
            )
        )
        ctx['players'] = player_list
        if len(player_list) >= 5:
            ctx['extra_players'] = len(player_list) - 5
        ctx['update'] = update
        ctx['updateline'] = updateline

        s = render_to_string("message.notuniqueplayer.djhtml", ctx)

        Message.__init__(self, s, _('\'%s\' not unique') % search, type)
        self.id = id
# }}}

# {{{ generate_messages: Generates a list of message objects for an object that supports them.
def generate_messages(obj):
    return [Message(m.get_message(), m.get_title(), m.type) for m in obj.message_set.all()]
# }}}

# {{{ login_message: Generates a message notifying about login status.
def login_message(base, extra=''):
    if not base['adm']:
        text = ' '.join([_('You are not logged in.'), extra, '(<a href="/login/">%s</a>)' % _('login')])
    else:
        text = ' '.join([
            _('You are logged in as %s') % base['user'],
            '(<a href="/logout/">%s</a>, <a href="/changepwd/">%s</a>)' % (
                _('logout'),
                _('change password')
            )
        ])
    base['messages'].append(Message(text, type=Message.INFO))
# }}}

# {{{ StrippedCharField: Subclass of CharField that performs stripping.
class StrippedCharField(forms.CharField):
    def clean(self, value):
        value = super(StrippedCharField, self).clean(value)
        if value is not None:
            value = value.strip()
            if self.required and value == '':
                raise ValidationError(_('This field is required.'))
            elif value == '':
                return None
            return value
        return None
# }}}

# {{{ get_param(request, param, default): Returns request.GET[param] if available, default if not.
def get_param(request, param, default):
    try:
        return request.GET[param]
    except:
        return default
# }}}

# {{{ get_param_choice(request, param, choices, default): Returns request.GET[param] if available and in
# the list choices, default if not.
def get_param_choice(request, param, choices, default):
    try:
        val = request.GET[param]
        assert(val in choices)
        return val
    except:
        return default
# }}}

# {{{ get_param_range(request, param, range, default): Returns request.GET[param] as an int, restricted to the
# range given (a tuple (min,max)), or default if not.
def get_param_range(request, param, rng, default):
    try:
        val = int(request.GET[param])
        return min(max(val, rng[0]), rng[1])
    except:
        return default
# }}}

# {{{ get_param_date(request, param, default): Converts a GET param to a date.
def get_param_date(request, param, default):
    param = get_param(request, param, None)
    try:
        return datetime.strptime(param, '%Y-%m-%d').date()
    except:
        return default
# }}}

# {{{ post_param(request, param, default): Returns request.POST[param] if available, default if not.
# If you're using this method, consider deploying a form instead.
def post_param(request, param, default):
    try:
        return request.POST[param]
    except:
        return default
# }}}

# {{{ base_ctx: Generates a minimal context, required to render the site layout and menus
# Parameters:
# - section: A string, name of the current major section (or None)
# - subpage: A string, name of the current subsection (or None)
# - request: The request that was passed to the view function (necessary to enable admin features)
# - context: Additional information which can be used depending on section and subsection
# Returns: A dictionary to be extended by the view function, and then passed to template rendering.
def base_ctx(section=None, subpage=None, request=None, context=None):
    curp = get_latest_period()

    base = {
        'curp':      curp,
        'debug':     DEBUG,
        'cur_path':  request.get_full_path(),
        'messages':  [],
        'lang':      request.LANGUAGE_CODE,
        'menu':      [{
            'id': 'Ranking',
            'name': _('Ranking'),
            'url': '/periods/latest/',
            'submenu': [
                ('Current', _('Current'),  '/periods/latest/'),
                ('History', _('History'),  '/periods/'),
                ('Earnings', _('Earnings'), '/earnings/'),
        ]}, {
            'id': 'Teams',
            'name': _('Teams'),
            'url': '/teams/',
            'submenu': [
                ('Ranking', _('Ranking'), '/teams/'),
                ('Transfers', _('Transfers'), '/transfers/'),
        ]}, {
            'id': 'Records',
            'name': _('Records'),
            'url': '/records/history/',
            'submenu': [
                ('History', _('History'), '/records/history/'),
                # Translators: Hall of fame
                ('HoF', _('HoF'), '/records/hof/'),
                ('All', _('All'), '/records/race/?race=all'),
                ('Protoss', _('Protoss'), '/records/race/?race=P'),
                ('Terran', _('Terran'), '/records/race/?race=T'),
                ('Zerg', _('Zerg'), '/records/race/?race=Z'),
        ]}, {
            'id': 'Results',
            'name': _('Results'),
            'url': '/results/',
            'submenu': [
                ('By Date', _('By Date'), '/results/'),
                ('By Event', _('By Event'), '/results/events/'),
                ('Search', _('Search'), '/results/search/'),
        ]}, {
            'id': 'Inference',
            'name': _('Inference'),
            'url': '/inference/',
            'submenu': [
                ('Predict', _('Predict'), '/inference/'),
        ]}, {
            'id': 'Misc',
            'name': _('Misc'),
            'url': '/misc/',
            'submenu': [
                ('Balance Report', _('Balance Report'), '/misc/balance/'),
                ('Days Since…', _('Days Since…'), '/misc/days/'),
                ('Compare', _('Compare'), '/misc/compare/')
        ]}, {
            'id': 'About',
            'name': _('About'),
            'url': '/about/faq/',
            'submenu': [
                ('FAQ', _('FAQ'), '/about/faq/'),
                ('Blog', _('Blog'), '/about/blog/'),
                ('Database', _('Database'), '/about/db/'),
                ('API', _('API'), '/about/api/'),
        ]}, {
            'id': 'Submit',
            'name': _('Submit'),
            'url': '/add/',
            'submenu': [
                # Translators: Matches as in SC2-matches, not search matches.
                ('Matches', _('Matches'), '/add/'),
                ('Review', _('Review'), '/add/review/'),
                ('Events', _('Events'), '/add/events/'),
                ('Open events', _('Open events'), '/add/open_events/'),
                ('Player info', _('Player info'), '/add/player_info/'),
                ('Misc', _('Misc'), '/add/misc/'),
        ]}]
    }
    base.update({"subnav": None})
    def add_subnav(title, url):
        if base["subnav"] is None:
            base["subnav"] = []
        base["subnav"].append((title, url))
    base.update(csrf(request))

    # Log in if possible
    if request.method == 'POST' and 'username' in request.POST and 'password' in request.POST:
        user = authenticate(username=request.POST['username'], password=request.POST['password'])
        if user != None and user.is_active:
            login(request, user)

    # Check for admin rights (must belong to match uploader group, but this is the only group that exists)
    if request != None:
        base['adm'] = request.user.is_authenticated() and request.user.groups.exists()
        base['user'] = request.user.username
    else:
        base['adm'] = False

    if not base['adm']:
        base['menu'][-1]['submenu'] = base['menu'][-1]['submenu'][:1]

    if section is not None:
        base['curpage'] = section

    if subpage is not None:
        base['cursubpage'] = subpage

    if context is not None:
        if isinstance(context, Player):
            rating = context.get_latest_rating_update()
            earnings = context.has_earnings()

            base_url = '/players/%i-%s/' % (context.id, urlfilter(context.tag))
            add_subnav(_('Summary'), base_url)

            if rating is not None:
                add_subnav(_('Rating history'), base_url + 'historical/')

            add_subnav(_('Match history'), base_url + 'results/')

            if context.has_earnings():
                add_subnav(_('Earnings'), base_url + 'earnings/')

            if rating is not None:
                add_subnav(_('Adjustments'), base_url + 'period/%i/' % rating.period.id)

    return base
# }}}

# {{{ cache_login_protect: Decorator for caching only if user is not logged in.
# Use this in place of BOTH cache_page and csrf_protect, and only on pages that require a CSRF token IF AND
# ONLY IF the user is logged in. If the view ALWAYS issues a CSRF token (or SOMETIMES does, but you can't tell
# when easily), use neither cache_page nor csrf_protect. If the view NEVER issues a CSRF token, use cache_page
# alone.
def cache_login_protect(view):
    def handler(request, *args, **kwargs):
        if request.user.is_authenticated():
            final_view = view
        else:
            final_view = cache_page(view)
        return final_view(request, *args, **kwargs)
    return handler
# }}}

# {{{ etn: Executes a function and returns its result if it doesn't throw an exception, or None if it does.
def etn(f):
    try:
        return f()
    except:
        return None
# }}}

# {{{ ntz: Helper function with aggregation, sending None to 0, so that the sum of an empty list is 0.
# AS IT FUCKING SHOULD BE.
ntz = lambda k: k if k is not None else 0
# }}}


# {{{ search: Helper function for performing searches
def search(query, search_for=['players', 'teams', 'events'], strict=False):
    # {{{ Split query
    lex = shlex.shlex(query, posix=True)
    lex.wordchars += "'#-"
    lex.commenters = ''
    lex.quotes = '"'

    terms = [s.strip() for s in list(lex) if s.strip() != '']
    if len(terms) == 0:
        return None
    # }}}

    # {{{ Search for players, teams and events
    if 'players' in search_for:
        players = find_player(lst=terms, make=False, soft=True, strict=strict)
    else:
        players = None

    if 'teams' in search_for:
        teams = Group.objects.filter(is_team=True)
    else:
        teams = None

    if 'events' in search_for:
        events = Event.objects.filter(type__in=[TYPE_CATEGORY, TYPE_EVENT]).order_by('idx')
        events = events.filter(
            fullname__iregex=(
                r"\s".join(r".*{}.*".format(term) for term in terms)
            )
        )
    else:
        events = None

    for term in terms:
        if 'teams' in search_for:
            teams = teams.filter(Q(name__icontains=term) | Q(alias__name__icontains=term))

    if 'teams' in search_for:
        teams = teams.distinct()
    # }}}

    return players, teams, events
# }}}
