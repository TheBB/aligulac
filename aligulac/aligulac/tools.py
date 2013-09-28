# {{{ Imports
import random
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
from django.views.decorators.csrf import csrf_protect

from aligulac.cache import cache_page
from aligulac.settings import DEBUG

from ratings.models import (
    Earnings,
    Player,
    Rating,
)
from ratings.tools import get_latest_period
from ratings.templatetags.ratings_extras import urlfilter
# }}}

# {{{ Message
# This class encodes error/success/warning messages sent to the templates.
# context['messages'] should point to a list of Message objects.
class Message:
    WARNING = 'warning'
    ERROR = 'error'
    INFO = 'info'
    SUCCESS = 'success'

    def __init__(self, text=None, title='', type='info', error=None, field=None):
        if error is None:
            self.title = title
            self.text = text
            self.type = type
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

        lst = []
        for p in players:
            s = ''
            if p.country is not None and p.country != '':
                s += '<img src="http://static.aligulac.com/flags/%s.png" /> ' % p.country.lower()
            s += '<img src="http://static.aligulac.com/%s.png" /> ' % p.race

            if update is None:
                s += '<a href="/players/%i-%s/">%s</a>' % (p.id, p.tag, p.tag)
            elif updateline is None:
                s += ((
                    '<a href="#" onclick="set_textbox(\'%s\',\'%s %i\'); '
                    'togvis(\'%s\',\'none\'); return false;">%s</a>'
                ) % (update, p.tag, p.id, id, p.tag))
            else:
                s += ((
                    '<a href="#" onclick="set_textarea_line(\'%s\',\'%s %i\',%i); '
                    'togvis(\'%s\',\'none\'); return false;">%s</a>'
                ) % (update, p.tag, p.id, updateline, id, p.tag))

            lst.append(s)

        num = 5
        if len(lst) < num:
            s = 'Possible matches: ' + ', '.join(lst[:-1]) + ' and ' + lst[-1] + '.'
        else:
            rand = ''.join(random.choice(string.ascii_lowercase) for _ in range(10))
            s = (
                'Possible matches: <span id="%s-a">' % rand + ', '.join(lst[:num-1]) +
                ' and <a href="#" onclick="togvis(\'%s-a\',\'none\'); ' % rand +
                'togvis(\'%s-b\',\'inline\'); return false;">' % rand +
                '%i more</a></span>' % (len(lst) - num + 1) +
                '<span id="%s-b" style="display: none;">%s</span>' %
                    (rand, ', '.join(lst[:-1]) + ' and ' + lst[-1]) +
                '.'
            )

        Message.__init__(self, s, '\'%s\' not unique' % search, type)
        self.id = id
# }}}

# {{{ generate_messages: Generates a list of message objects for an object that supports them.
def generate_messages(obj):
    return [Message(m.text, m.title, m.type) for m in obj.message_set.all()]
# }}}

# {{{ login_message: Generates a message notifying about login status.
def login_message(base, extra=''):
    if not base['adm']:
        text = ' '.join(['You are not logged in.', extra, '(<a href="/login/">login</a>)'])
    else:
        text = ' '.join([
            'You are logged in as',
            base['user'],
            '(<a href="/logout/">logout</a>, <a href="/changepwd/">change password</a>)'
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
                raise ValidationError('This field is required.')
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

    menu = [
        ('Ranking',    '/periods/%i/' % curp.id),
        ('Teams',      '/teams/'),
        ('Records',    '/records/history'),
        ('Results',    '/results/'),
        ('Reports',    '/reports/'),
        ('Inference',  '/inference/'),
        ('About',      '/faq/'),
        ('Submit',     '/add/'),
    ]

    base = {
        'curp':      curp,
        'menu':      menu,
        'debug':     DEBUG,
        'cur_path':  request.get_full_path(),
        'messages':  [],
        'menu':      [{
            'name': 'Ranking',
            'url': '/periods/%i' % curp.id,
            'submenu': [
                ('Current',  '/periods/%i/' % curp.id),
                ('History',  '/periods/'),
                ('Earnings', '/earnings/'),
        ]}, {
            'name': 'Teams',
            'url': '/teams/',
            'submenu': [
                ('Ranking', '/teams/'),
                ('Transfers', '/transfers/'),
        ]}, {
            'name': 'Records',
            'url': '/records/history/',
            'submenu': [
                ('History', '/records/history/'),
                ('HoF', '/records/hof/'),
                ('All', '/records/race/?race=all'),
                ('Protoss', '/records/race/?race=P'),
                ('Terran', '/records/race/?race=T'),
                ('Zerg', '/records/race/?race=Z'),
        ]}, {
            'name': 'Results',
            'url': '/results/',
            'submenu': [
                ('By Date', '/results/'),
                ('By Event', '/results/events/'),
                ('Search', '/results/search/'),
        ]}, {
            'name': 'Reports',
            'url': '/reports/',
            'submenu': [
                ('Balance', '/reports/balance/'),
        ]}, {
            'name': 'Inference',
            'url': '/inference/',
            'submenu': [
                ('Predict', '/inference/'),
        ]}, {
            'name': 'About',
            'url': '/faq/',
            'submenu': [
                ('FAQ', '/faq/'),
                ('Blog', '/blog/'),
                ('Database', '/db/'),
        ]}, {
            'name': 'Submit',
            'url': '/add/',
            'submenu': [
                ('Matches', '/add/'),
                ('Review', '/add/review/'),
                ('Events', '/add/events/'),
                ('Open events', '/add/open_events/'),
                ('Misc', '/add/misc/'),
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

    # Check for admin rights.
    if request != None:
        base['adm'] = request.user.is_authenticated()
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
            add_subnav('Summary', base_url)

            if rating is not None:
                add_subnav('Rating history', base_url + 'historical/')

            add_subnav('Match history', base_url + 'results/')

            if context.has_earnings():
                add_subnav('Earnings', base_url + 'earnings/')

            if rating is not None:
                add_subnav('Adjustments', base_url + 'period/%i/' % rating.period.id)

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
