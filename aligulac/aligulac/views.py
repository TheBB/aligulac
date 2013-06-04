import os
import string
import random
import shlex
from datetime import datetime

from django.contrib.auth import logout
from django.shortcuts import render_to_response, redirect
from django.template.loader import render_to_string
from django.http import HttpResponse, HttpResponseNotFound
from django.core.context_processors import csrf
from django.db.models import Sum, Q
from django.contrib.auth.models import User

from aligulac.settings import DEBUG, PATH_TO_DIR
from ratings.models import Rating, Period, Player, Group, Match, Event, Earnings
import ratings.tools
from ratings.templatetags.ratings_extras import urlfilter

from blog.models import Post

import simplejson

from countries import transformations


# This class encodes error/success/warning messages sent to the templates.
# A list of these should be in base['messages']
class Message:

    WARNING = 'warning'
    ERROR = 'error'
    INFO = 'info'
    SUCCESS = 'success'

    def __init__(self, text, title='', type='info'):
        self.title = title
        self.text = text
        self.type = type
        self.id = ''.join([random.choice(string.letters+string.digits) for _ in xrange(10)])


class NotUniquePlayerMessage(Message):

    def __init__(self, search, players, update=None, updateline=None, type='error'):
        id = ''.join([random.choice(string.letters+string.digits) for _ in xrange(10)])

        lst = []
        for p in players:
            s = ''
            if p.country is not None and p.country != '':
                s += '<img src="http://static.aligulac.com/flags/%s.png" /> ' % p.country.lower()
            s += '<img src="http://static.aligulac.com/%s.png" /> ' % p.race

            if update is None:
                s += '<a href="/players/%i-%s/">%s</a>' % (p.id, p.tag, p.tag)
            elif updateline is None:
                s += ('<a href="#" onclick="set_textbox(\'%s\',\'%s %i\');' +\
                                         ' togvis(\'%s\',\'none\'); return false;">%s</a>')\
                     % (update, p.tag, p.id, id, p.tag)
            else:
                s += ('<a href="#" onclick="set_textarea_line(\'%s\',\'%s %i\',%i);' +\
                                         ' togvis(\'%s\',\'none\'); return false;">%s</a>')\
                     % (update, p.tag, p.id, updateline, id, p.tag)

            lst.append(s)

        num = 5
        if len(lst) < num:
            s = 'Possible matches: ' + ', '.join(lst[:-1]) + ' and ' + lst[-1] + '.'
        else:
            rand = ''.join(random.choice(string.ascii_lowercase) for _ in xrange(10))
            s = 'Possible matches: <span id="%s-a">' % rand + ', '.join(lst[:num-1])\
              + ' and <a href="#" onclick="togvis(\'%s-a\',\'none\'); ' % rand\
              + 'togvis(\'%s-b\',\'inline\'); return false;">' % rand\
              + '%i more</a></span>' % (len(lst) - num + 1)\
              + '<span id="%s-b" style="display: none;">%s</span>'\
                % (rand, ', '.join(lst[:-1]) + ' and ' + lst[-1])\
              + '.'

        Message.__init__(self, s, '\'%s\' not unique' % search, type)
        self.id = id


def generate_messages(obj):
    ret = []
    for m in obj.message_set.all():
        ret.append(Message(m.text, m.title, m.type))
    return ret

def base_ctx(section=None, subpage=None, request=None, context=None):
    curp = Period.objects.filter(computed=True).order_by('-start')[0]
    menu = [('Ranking', '/periods/%i' % curp.id),\
            ('Teams', '/teams/'),\
            ('Records', '/records/'),\
            ('Results', '/results/'),\
            ('Reports', '/reports/'),\
            ('Predict', '/predict/'),\
            ('About', '/faq/'),\
            ('Submit', '/add/')]

    base = {'curp': curp, 'menu': menu, 'debug': DEBUG, 'cur_path': request.get_full_path()}
    base.update(csrf(request))

    if request != None:
        base['adm'] = request.user.is_authenticated()
        base['user'] = request.user.username

    if section == 'Records':
        base['submenu'] = [('HoF', '/records/?race=hof'),\
                           ('All', '/records/?race=all'),\
                           ('Protoss', '/records/?race=P'),\
                           ('Terran', '/records/?race=T'),\
                           ('Zerg', '/records/?race=Z')]
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

    if section != None:
        base['curpage'] = section

    if subpage != None:
        base['cursubpage'] = subpage

    if context != None:
        if type(context) == Player:
            rating = Rating.objects.filter(player=context, comp_rat__isnull=False).order_by('-period')
            earnings = Earnings.objects.filter(player=context)

            base_url = '/players/%i-%s/' % (context.id, urlfilter(context.tag))

            base['submenu'] += [None, ('%s:' % context.tag, base_url)]

            if rating.exists():
                base['submenu'].append(('Rating history', base_url + 'historical/'))

            base['submenu'].append(('Match history', base_url + 'results/'))
            
            if earnings.exists():
                base['submenu'].append(('Earnings', base_url + 'earnings/'))

            if rating.exists():
                base['submenu'].append(('Adjustments', base_url + 'period/%i' % rating[0].period.id))

    base['messages'] = []

    return base

def db(request):
    base = base_ctx('About', 'Database', request)

    ngames = Match.objects.all().aggregate(Sum('sca'))['sca__sum'] + Match.objects.all().aggregate(Sum('scb'))['scb__sum']
    nmatches = Match.objects.all().count()
    nuntreated = Match.objects.filter(treated=False).count()

    nwol = Match.objects.filter(game='WoL').count()
    nhots = Match.objects.filter(game='HotS').count()

    nwolgames = Match.objects.filter(game='WoL').aggregate(Sum('sca'))['sca__sum'] + Match.objects.filter(game='WoL').aggregate(Sum('scb'))['scb__sum']
    nhotsgames = Match.objects.filter(game='HotS').aggregate(Sum('sca'))['sca__sum'] + Match.objects.filter(game='HotS').aggregate(Sum('scb'))['scb__sum']
	
    nonline = Match.objects.filter(offline = False).count()
    noffline = Match.objects.filter(offline = True).count()
	
    nonlinegames = Match.objects.filter(offline = False).aggregate(Sum('sca'))['sca__sum'] + Match.objects.filter(offline= False).aggregate(Sum('scb'))['scb__sum']
    nofflinegames = Match.objects.filter(offline = True).aggregate(Sum('sca'))['sca__sum'] + Match.objects.filter(offline= True).aggregate(Sum('scb'))['scb__sum']

    npartial = Match.objects.exclude(eventobj__isnull=True, event='').count()
    nfull = Match.objects.filter(eventobj__isnull=False).count()
    nuncatalogued = Match.objects.filter(eventobj__isnull=True).count()

    nplayers = Player.objects.all().count()
    nkoreans = Player.objects.filter(country='KR').count()
    nteams = Group.objects.filter(team=True).count()
    nactive = Group.objects.filter(active=True, team=True).count()
    ninactive = Group.objects.filter(active=False, team=True).count()

    base.update({'ngames': ngames, 'nmatches': nmatches, 'nuntreated': nuntreated,\
                 'nwol': nwol, 'nhots': nhots, 'nonline': nonline, 'noffline': noffline,\
                 'npartial': npartial, 'nfull': nfull, 'nuncatalogued': nuncatalogued,\
                 'nplayers': nplayers, 'nkoreans': nkoreans,\
                 'nteams': nteams, 'nactive': nactive, 'ninactive': ninactive,\
		 'nwolgames': nwolgames, 'nhotsgames': nhotsgames, 'nonlinegames': nonlinegames, 'nofflinegames':nofflinegames})

    submitters = []
    for u in User.objects.all():
        n = Match.objects.filter(submitter=u).count()
        if n > 0:
            submitters.append((u, n))
    submitters.sort(key=lambda t: t[1], reverse=True)
    base['submitters'] = submitters

    dumpfile = '/usr/local/www/media/al/aligulac.sql'
    base['dump'] = os.path.exists(dumpfile)
    if base['dump']:
        stat = os.stat(dumpfile)
        base['megabytes'] = float(stat.st_size)/1048576
        base['modified'] = datetime.fromtimestamp(stat.st_mtime)

    base['updated'] = datetime.fromtimestamp(os.stat(PATH_TO_DIR + 'update').st_mtime)

    return render_to_response('db.html', base)

def staff(request):
    base = base_ctx('About', 'Staff', request)

    return render_to_response('staff.html', base)

def home(request):
    base = base_ctx(request=request)

    period = Period.objects.filter(computed=True).order_by('-start')[0]
    entries = ratings.tools.filter_active_ratings(Rating.objects.filter(period=period).order_by('-rating'))
    entries = entries.select_related('group', 'groupmembership')[0:10]
    for entry in entries:
        teams = entry.player.groupmembership_set.filter(current=True, group__team=True)
        if teams.exists():
            entry.team = teams[0].group.shortname
            entry.teamfull = teams[0].group.name
            entry.teamid = teams[0].group.id

    blogs = Post.objects.order_by('-date')[0:3]

    base.update({'entries': entries, 'blogposts': blogs})
    
    return render_to_response('index.html', base)

def search(request, q=''):
    base = base_ctx(request=request)

    if q == '':
        q = request.GET['q']

    terms = shlex.split(q.encode())

    players = ratings.tools.find_player(terms, make=False, soft=True)

    teams = Group.objects.filter(team=True)
    for qpart in terms:
        if qpart.strip() == '':
            continue
        query = Q(name__icontains=qpart) | Q(alias__name__icontains=q)
        teams = teams.filter(query)
    teams = teams.distinct()

    events = Event.objects.filter(type__in=['category','event'])
    for qpart in terms:
        if qpart.strip() == '':
            continue
        events = events.filter(Q(fullname__icontains=qpart))
    events = events.order_by('lft')

    if players.count() == 1 and teams.count() == 0 and events.count() == 0:
        return redirect('/players/%i-%s/' % (players[0].id, urlfilter(players[0].tag)))
    elif players.count() == 0 and teams.count() == 1 and events.count() == 0:
        return redirect('/teams/%i-%s/' % (teams[0].id, urlfilter(teams[0].name)))
    elif players.count() == 0 and teams.count() == 0 and events.count() == 1:
        return redirect('/results/events/%i-%s/' % (events[0].id, urlfilter(events[0].fullname)))

    base.update({'players': players, 'query': repr(terms), 'teams': teams, 'events': events})

    return render_to_response('search.html', base)

def api_search(request, q=''):
    if q == '':
        q = request.GET['q']

    players = Player.objects.filter(tag__icontains=q)
    d = []
    for p in players:
        dp = {'tag': p.tag, 'race': p.race}
        if p.country != None and p.country != '':
            dp['country'] = transformations.cc_to_cn(p.country)

        try:
            r = Rating.objects.filter(player=p).order_by('-period__id')[0]
            dp['rating'] = r.rating
            dp['rating_vp'] = r.rating_vp
            dp['rating_vt'] = r.rating_vt
            dp['rating_vz'] = r.rating_vz
            dp['dev'] = r.dev
            dp['dev_vp'] = r.dev_vp
            dp['dev_vt'] = r.dev_vt
            dp['dev_vz'] = r.dev_vz
        except:
            dp['rating'] = 0
            dp['rating_vp'] = 0
            dp['rating_vt'] = 0
            dp['rating_vz'] = 0
            dp['dev'] = 0.6
            dp['dev_vp'] = 0.6
            dp['dev_vt'] = 0.6
            dp['dev_vz'] = 0.6

        d.append(dp)

    return HttpResponse(simplejson.dumps(d), mimetype='application/json')

def logoutv(request):
    logout(request)
    return redirect('/add/')

def loginv(request):
    base = base_ctx(request=request)
    base.update(csrf(request))
    return render_to_response('login.html', base)

def changepwd(request):
    base = base_ctx(request=request)

    if not request.user.is_authenticated():
        base.update(csrf(request))
        return render_to_response('login.html', base)

    base.update({'user': request.user.username})

    if not ('old' in request.POST and 'new' in request.POST and 'newre' in request.POST):
        base.update(csrf(request))
        return render_to_response('changepwd.html', base)

    if not request.user.check_password(request.POST['old']):
        base['messages'].append(Message('The old password didn\'t match. Your password was not changed.',
                                        type=Message.ERROR))
        base.update(csrf(request))
        return render_to_response('changepwd.html', base)
    
    if request.POST['new'] != request.POST['newre']:
        base['messages'].append(Message('The new passwords didn\'t match. Your password was not changed.',
                                        type=Message.ERROR))
        base.update(csrf(request))
        return render_to_response('changepwd.html', base)

    request.user.set_password(request.POST['new'])
    base['messages'].append(Message(
        'The password for ' + request.user.username + ' was successfully changed.', type=Message.SUCCESS))
    request.user.save()

    return render_to_response('changepwd.html', base)

def h404(request):
    base = base_ctx(request=request)

    return HttpResponseNotFound(render_to_string('404.html', base))

def h500(request):
    base = base_ctx(request=request)

    return HttpResponseNotFound(render_to_string('500.html', base))
