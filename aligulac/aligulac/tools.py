import random
import string

from django.core.context_processors import csrf
from django import forms

from aligulac.settings import DEBUG

from ratings.models import Player, Rating, Earnings
from ratings.tools import get_latest_period
from ratings.templatetags.ratings_extras import urlfilter

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

# {{{ generate_messages: Generates a list of message objects for an object that supports them.
def generate_messages(obj):
    return [Message(m.text, m.title, m.type) for m in obj.message_set.all()]
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

    menu = [('Ranking', '/periods/%i' % curp.id),\
            ('Teams', '/teams/'),\
            ('Records', '/records/history'),\
            ('Results', '/results/'),\
            ('Reports', '/reports/'),\
            ('Predict', '/predict/'),\
            ('About', '/faq/'),\
            ('Submit', '/add/')]

    base = {
        'curp': curp,
        'menu': menu,
        'debug': DEBUG,
        'cur_path': request.get_full_path(),
        'messages': [],
    }
    base.update(csrf(request))

    # Check for admin rights.
    if request != None:
        base['adm'] = request.user.is_authenticated()
        base['user'] = request.user.username

    # Fill in submenu depending on section.
    if section == 'Records':
        base['submenu'] = [('History', '/records/history/'),
                           ('HoF', '/records/hof/'),\
                           ('All', '/records/race/?race=all'),\
                           ('Protoss', '/records/race/?race=P'),\
                           ('Terran', '/records/race/?race=T'),\
                           ('Zerg', '/records/race/?race=Z')]
    elif section == 'Results':
        base['submenu'] = [('By Date', '/results/'),\
                           ('By Event', '/results/events/'),\
                           ('Search', '/results/search/')]
    elif section == 'Submit' and base['adm']:
        base['submenu'] = [('Matches', '/add/'),\
                           ('Review', '/add/review/'),\
                           ('Events', '/add/events/'),\
                           ('Open events', '/add/open_events/'),\
                           ('Integrity', '/add/integrity/'),\
                           ('Misc', '/add/misc/')]
    elif section == 'Teams':
        base['submenu'] = [('Ranking', '/teams/'),\
                           ('Transfers', '/player_transfers/')]
    elif section == 'Ranking':
        base['submenu'] = [('Current', '/periods/%i' % curp.id),\
                           ('History', '/periods/'),\
                           ('Earnings', '/earnings/')]
    elif section == 'Predict':
        base['submenu'] = [('Predict', '/predict/'),
                           #('Factoids', '/factoids/'),
                           ('Compare', '/compare/')]
    elif section == 'About':
        base['submenu'] = [('FAQ', '/faq/'),
                           ('Blog', '/blog/'),
                           #('Staff', '/staff/'),
                           ('Database', '/db/')]
    elif section == 'Reports':
        pass

    if section is not None:
        base['curpage'] = section

    if subpage is not None:
        base['cursubpage'] = subpage

    if context is not None:
        if isinstance(context, Player):
            rating = context.get_latest_rating_update()
            earnings = context.has_earnings()

            base_url = '/players/%i-%s/' % (context.id, urlfilter(context.tag))
            base['submenu'] += [None, ('%s:' % context.tag, base_url)]

            if rating is not None:
                base['submenu'].append(('Rating history', base_url + 'historical/'))

            base['submenu'].append(('Match history', base_url + 'results/'))

            if context.has_earnings():
                base['submenu'].append(('Earnings', base_url + 'earnings/'))

            if rating is not None:
                base['submenu'].append(('Adjustments', base_url + 'period/%i/' % rating.period.id))

    return base
# }}}

# {{{ etn: Executes a function and returns its result if it doesn't throw an exception, or None if it does.
def etn(f):
    try:
        return f()
    except:
        return None
# }}}
