# {{{ Imports
from datetime import datetime
import shlex
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

from aligulac.cache import cache_page
from aligulac.settings import (
    DUMP_PATH,
    PROJECT_PATH,
)
from aligulac.tools import (
    base_ctx,
    get_param,
    login_message,
    Message,
    StrippedCharField,
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
    TYPE_CATEGORY,
    TYPE_EVENT,
    WOL,
)
from ratings.templatetags.ratings_extras import urlfilter
from ratings.tools import (
    count_winloss_games,
    filter_active,
    find_player,
    populate_teams,
)
# }}}

# {{{ Home page
@cache_page
def home(request):
    base = base_ctx(request=request)

    entries = filter_active(Rating.objects.filter(period=base['curp']))\
              .order_by('-rating')\
              .select_related('player')[0:10]

    populate_teams(entries)

    blogs = Post.objects.order_by('-date')[0:3]

    base.update({
        'entries': entries,
        'blogposts': blogs
    })

    return render_to_response('index.html', base)
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

    base.update({"title": "Database status"})

    return render_to_response('db.html', base)
# }}}

# {{{ API documentation and keys
class APIKeyForm(forms.Form):
    organization = StrippedCharField(max_length=200, required=True, label='Name/organization')
    contact = forms.EmailField(max_length=200, required=True, label='Contact')

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
            ret.append(Message('Entered data was invalid.', type=Message.ERROR))
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

        ret.append(Message("Your API key is '%s'. Please keep it safe." % key.key, type=Message.SUCCESS))

        return ret
    # }}}

def api(request):
    base = base_ctx('About', 'API', request)

    #base['messages'].append(Message(
        #'The API is currently in beta. Do not rely on it in production yet! We may disable features without '
        #'prior warning until the release of version 1. When this happens, the root URL will be changed to '
        #'<code>/api/v1/</code> and the beta URL will be removed.',
        #type=Message.WARNING,
    #))

    if request.method == 'POST':
        form = APIKeyForm(request)
        base['messages'] += form.add_key()
    else:
        form = APIKeyForm()

    base.update({
        'title': 'API documentation',
        'form': form,
    })

    return render_to_response('api.html', base)
# }}}

# {{{ search view
@cache_page
def search(request):
    base = base_ctx(request=request)

    # {{{ Split query
    query = get_param(request, 'q', '')
    terms = [s.strip() for s in shlex.split(query) if s.strip() != '']
    if len(terms) == 0:
        return redirect('/')
    # }}}

    # {{{ Search for players, teams and events
    players = find_player(lst=terms, make=False, soft=True)

    teams = Group.objects.filter(is_team=True)
    events = Event.objects.filter(type__in=[TYPE_CATEGORY, TYPE_EVENT]).order_by('idx')
    for term in terms:
        teams = teams.filter(Q(name__icontains=term) | Q(alias__name__icontains=term))
        events = events.filter(Q(fullname__icontains=term))
    teams = teams.distinct()
    # }}}

    # {{{ Redirect if only one hit
    if   players.count() == 1 and teams.count() == 0 and events.count() == 0:
        return redirect('/players/%i-%s/' % (players.first().id, urlfilter(players.first().tag)))
    elif players.count() == 0 and teams.count() == 1 and events.count() == 0:
        return redirect('/teams/%i-%s/' % (teams.first().id, urlfilter(teams.first().name)))
    elif players.count() == 0 and teams.count() == 0 and events.count() == 1:
        return redirect('/results/events/%i-%s/' % (events.first().id, urlfilter(events.first().fullname)))
    # }}}

    base.update({
        'players':  players,
        'teams':    teams,
        'events':   events,
        'query':    query,
    })

    base.update({"title": "Search results"})

    return render_to_response('search.html', base)
# }}}

# {{{ Login, logout and change password
def login_view(request):
    base = base_ctx(request=request)
    login_message(base)

    base.update({"title": "Login"})
    return render_to_response('login.html', base)

def logout_view(request):
    logout(request)
    return redirect('/login/')

def changepwd(request):
    if not request.user.is_authenticated():
        return redirect('/login/')

    base = base_ctx(request=request)
    login_message(base)

    if not ('old' in request.POST and 'new' in request.POST and 'newre' in request.POST):
        return render_to_response('changepwd.html', base)

    if not request.user.check_password(request.POST['old']):
        base['messages'].append(
            Message("The old password didn't match. Your password was not changed.", type=Message.ERROR)
        )
        return render_to_response('changepwd.html', base)

    if request.POST['new'] != request.POST['newre']:
        base['messages'].append(
            Message("The new passwords didn't match. Your password was not changed.", type=Message.ERROR)
        )
        return render_to_response('changepwd.html', base)

    request.user.set_password(request.POST['new'])
    request.user.save()
    base['messages'].append(
        Message('The password for %s was successfully changed.' % request.user.username, type=Message.SUCCESS)
    )

    base.update({"title": "Change password"})

    return render_to_response('changepwd.html', base)
# }}}

# {{{ Error handlers
@cache_page
def h404(request):
    base = base_ctx(request=request)
    base.update({"title": "404: Not found"})
    return HttpResponseNotFound(render_to_string('404.html', base))

@cache_page
def h500(request):
    base = base_ctx(request=request)
    base.update({"title": "500: Internal Server Error"})
    return HttpResponseNotFound(render_to_string('500.html', base))
# }}}
