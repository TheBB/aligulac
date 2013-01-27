import os
from pyparsing import nestedExpr

from aligulac.views import base_ctx
from ratings.tools import find_player

from django.shortcuts import render_to_response, get_object_or_404
from django.http import HttpResponse
from django.db.models import Q, Sum, F
from models import Period, Rating, Player, Match, Team, TeamMembership, Event
from django.contrib.auth import authenticate, login
from django.core.context_processors import csrf

from countries import transformations, data

def submitmenu(base):
    base['submenu'] = [('Misc', '/add/misc/'),\
                       ('Matches', '/add/'),\
                       ('Events', '/add/events/')]
    base['curpage'] = 'Admin'

def parse_match(s):
    res = nestedExpr('(',')').parseString('('+s.encode()+')').asList()[0]
    elements = []
    collect = []

    first = True
    for r in res:
        if type(r) == str:
            splits = r.split('-')
            if len(splits) > 1 and first:
                elements.append(splits[0].strip())
                collect.append(elements)
                elements = []
                elements += [r.strip() for r in splits[1:] if r.strip() != '']
                first = False
            elif len(splits) > 1 and not first:
                collect.append(elements)
                elements = []
                elements += [r.strip() for r in splits if r.strip() != '']
            else:
                elements.append(splits[0].strip())

        else:
            elements += r

    collect.append(elements)
    collect = [[f for f in col if f != ''] for col in collect]
    return collect

def add_matches(request):
    if 'username' in request.POST and 'password' in request.POST:
        user = authenticate(username=request.POST['username'], password=request.POST['password'])
        if user != None and user.is_active:
            login(request, user)

    base = base_ctx('Admin', 'Matches', request)

    if not base['adm']:
        base.update(csrf(request))
        return render_to_response('login.html', base)

    base.update({'user': request.user.username})

    base['events'] = Event.objects.filter(closed=False, rgt=F('lft')+1).order_by('lft')

    if 'event' in request.POST and 'date' in request.POST and 'matches' in request.POST:
        event = request.POST['event'].strip()
        date = request.POST['date']
        matches = request.POST['matches'].splitlines()

        success = []
        failure = []

        try:
            eventobj = Event.objects.get(id=int(request.POST['eobj']))
            if eventobj.id == 2:
                eventobj = None
        except:
            eventobj = None

        if eventobj != None:
            base['eobj'] = eventobj.id

        # Loop through match entries
        for s in matches:
            if s.strip() == '':
                continue

            try:
                # Parse and collect the components
                collect = parse_match(s.strip())
                pla = collect[0]
                plb = collect[1]
                sca = int(collect[2][0])
                scb = int(collect[2][1])

                # Check for !DUP and !MAKE switches
                dup_switch = False
                make_switch = False
                while collect[2][-1][0] == '!':
                    if collect[2][-1] == '!MAKE':
                        make_switch = True
                    elif collect[2][-1] == '!DUP':
                        dup_switch = True
                    collect[2] = collect[2][:-1]

                # Check for race overrides
                def get_race(lst):
                    if lst[-1][:2].upper() == 'R:':
                        r = lst[-1][2:].upper()
                        return r, lst[:-1]
                    else:
                        return None, lst
                rca, pla = get_race(pla)
                rcb, plb = get_race(plb)

                # Find players
                def get_player(lst, failure, make):
                    try:
                        pls = find_player(lst, make=make)
                    except Exception as e:
                        failure.append((s, e.message))
                        return None
                    if not pls.exists():
                        failure.append((s, 'Could not find player \'%s\', add !MAKE switch to create'\
                                % ' '.join(lst)))
                        return None
                    if pls.count() > 1:
                        failure.append((s, 'Player \'%s\' not unique, provide more information'\
                                % ' '.join(lst)))
                        return None
                    return pls[0]

                pla = get_player(pla, failure, make_switch)
                if pla == None:
                    continue

                plb = get_player(plb, failure, make_switch)
                if plb == None:
                    continue

                n1 = Match.objects.filter(pla=pla, plb=plb, sca=sca, scb=scb)\
                        .extra(where=['abs(datediff(date,\'%s\')) < 2' % date])
                n2 = Match.objects.filter(pla=plb, plb=pla, sca=scb, scb=sca)\
                        .extra(where=['abs(datediff(date,\'%s\')) < 2' % date])
                n1 = n1.exists()
                n2 = n2.exists()

                if (n1 or n2) and not dup_switch:
                    failure.append((s, '%i duplicate(s) found, add !DUP switch to force: %s'\
                            % ((n1+n2), s)))
                    continue

                if pla.race in ['R', 'S'] and rca == None:
                    failure.append((s, '%s is Random or Switcher, need race information' % pla.tag))
                    continue

                if plb.race in ['R', 'S'] and rcb == None:
                    failure.append((s, '%s is Random or Switcher, need race information' % plb.tag))
                    continue

                m = Match()
                m.pla = pla
                m.plb = plb
                m.sca = sca
                m.scb = scb
                m.rca = pla.race if rca == None else rca
                m.rcb = plb.race if rcb == None else rcb
                m.date = date
                m.event = event
                m.submitter = request.user
                m.set_period()
                m.eventobj = eventobj
                m.save()

                success.append(m)

            except Exception as e:
                failure.append((s, e))
                continue

        base.update({'event': event, 'date': date, 'messages': True,\
                'matches': '\n'.join([f[0] for f in failure]), 'success': success, 'failure': failure})

    base.update(csrf(request))
    return render_to_response('add.html', base)

def manage_events(request):
    if 'username' in request.POST and 'password' in request.POST:
        user = authenticate(username=request.POST['username'], password=request.POST['password'])
        if user != None and user.is_active:
            login(request, user)

    base = base_ctx('Admin', 'Events', request)

    if not base['adm']:
        base.update(csrf(request))
        return render_to_response('login.html', base)

    base['user'] = request.user.username

    if 'parent' in request.POST:
        if request.POST['op'] == 'Add':
            try:
                parent = Event.objects.get(id=int(request.POST['parent']))
                for q in request.POST['name'].strip().split(','):
                    parent.add_child(q.strip())
            except:
                for q in request.POST['name'].strip().split(','):
                    if q.strip() == '':
                        continue
                    Event.add_root(q.strip())
        elif request.POST['op'] == 'Close':
            try:
                parent = Event.objects.get(id=int(request.POST['parent']))
                parent.close()
            except:
                pass

    from django.db import connection
    cur = connection.cursor()
    cur.execute('''SELECT e.id, e.name, (COUNT(p.id)-1), e.parent_id AS depth FROM ratings_event AS e, ratings_event AS p
                   WHERE e.lft BETWEEN p.lft AND p.rgt AND e.id != 2 AND e.closed=0 GROUP BY e.id ORDER BY e.lft''')
    nodes = cur.fetchall()
    foldnodes = []
    totfold = 0
    for i in range(0,len(nodes)):
        fold = 0
        try:
            fold = nodes[i+1][2]-nodes[i][2]
        except:
            pass
        if i == len(nodes) - 1:
            fold = -totfold
        foldnodes.append((nodes[i][0], nodes[i][1], nodes[i][2], fold, nodes[i][3]))
        totfold += fold

    base['nodes'] = foldnodes

    base.update(csrf(request))
    return render_to_response('eventmgr.html', base)

def manage(request):
    if 'username' in request.POST and 'password' in request.POST:
        user = authenticate(username=request.POST['username'], password=request.POST['password'])
        if user != None and user.is_active:
            login(request, user)

    base = base_ctx('Admin', 'Misc', request)

    if not base['adm']:
        base.update(csrf(request))
        return render_to_response('login.html', base)

    base['user'] = request.user.username
    base.update(csrf(request))

    if 'op' in request.POST and request.POST['op'] == 'merge':
        try:
            base['player_source'] = request.POST['player_source']
            base['player_target'] = request.POST['player_target']
            source = Player.objects.get(id=int(request.POST['player_source']))
            target = Player.objects.get(id=int(request.POST['player_target']))
        except:
            base['merge_err'] = 'Failed to find players. One or more incorrect IDs.'
            return render_to_response('manage.html', base)

        if 'conf' in request.POST and request.POST['conf'] == 'yes':
            Match.objects.filter(pla=source).update(pla=target, treated=False)
            Match.objects.filter(plb=source).update(plb=target, treated=False)
            Rating.objects.filter(player=source).delete()
            TeamMembership.objects.filter(player=source).delete()
            source.delete()

            base['merge_succ'] = 'Merging complete.'
            base['player_source'] = ''
            base['player_target'] = ''
        else:
            base['merge_conf'] = True
            base['source'] = source
            base['target'] = target
        return render_to_response('manage.html', base)

    if 'op' in request.POST and request.POST['op'] == 'treerestore':
        roots = list(Event.objects.filter(parent__isnull=True).order_by('lft'))
        nextleft = 0
        for r in roots:
            nextleft = r.reorganize(nextleft) + 1 
        base['treerestore_succ'] = 'The NSM has been restored.'
        return render_to_response('manage.html', base)

    return render_to_response('manage.html', base)
