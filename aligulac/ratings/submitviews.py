import os, pickle
import urllib, urllib2
from pyparsing import nestedExpr

from aligulac.views import base_ctx
from aligulac.settings import M_WARNINGS, M_APPROVED
from ratings.tools import find_player, find_duplicates, display_matches

from django.shortcuts import render_to_response, get_object_or_404
from django.http import HttpResponse
from django.db.models import Q, Sum, F
from models import Period, Rating, Player, Match, Team, TeamMembership, Event, PreMatchGroup, PreMatch
from django.contrib.auth import authenticate, login
from django.core.context_processors import csrf

from countries import transformations, data

class Integrity:
    pass

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
    # This view is the default redirect for login requests
    if 'username' in request.POST and 'password' in request.POST:
        user = authenticate(username=request.POST['username'], password=request.POST['password'])
        if user != None and user.is_active:
            login(request, user)

    base = base_ctx('Submit', 'Matches', request)

    # If the user is logged in, the template needs a username and a list of event objects
    if base['adm']:
        base['user'] = request.user.username
        base['events'] = Event.objects.filter(closed=False, rgt=F('lft')+1).order_by('lft')

    if 'matches' in request.POST:
        # Collect various information from the form
        event = request.POST['event'].strip()
        date = request.POST['date']
        matches = request.POST['matches'].splitlines()
        offline = not (request.POST['type'] != 'offline')
        game = request.POST['game']
        if game not in ['WoL', 'HotS']:
            game = 'WoL'

        base['game'] = game
        base['type'] = 'offline' if offline else 'online'
        base['matches'] = '\n'.join(matches)
        base['date'] = date
        base['event'] = event

        # Get event object. If not admin, an exception will be thrown and eventobj = None.
        try:
            eventobj = Event.objects.get(id=int(request.POST['eobj']))
            if eventobj.id == 2:
                eventobj = None
        except:
            eventobj = None

        if eventobj != None:
            base['eobj'] = eventobj.id

        # Get extra data needed if not admin.
        try:
            source = request.POST['source']
            contact = request.POST['contact']
            notes = request.POST['notes']
            base['source'] = source
            base['contact'] = contact
            base['notes'] = notes
        except:
            pass

        # Check various requirements for non-admins
        if not base['adm'] and len(matches) > 100:
            base.update({'messages': True, 'success': [],\
                    'failure': [(None, 'Please do not submit more than 100 results at a time')]})
            base.update(csrf(request))
            return render_to_response('add.html', base)
        if not base['adm'] and source.strip() == '':
            base.update({'messages': True, 'success': [],\
                    'failure': [(None, 'Please include a source')]})
            base.update(csrf(request))
            return render_to_response('add.html', base)

        # If not admin, make a PreMatchGroup.
        if not base['adm']:
            pmgroup = PreMatchGroup(date=date, event=event, source=source, contact=contact, notes=notes,\
                    game=game, offline=offline)
            pmgroup.save()

        # Lists of successes and failures
        success = []
        failure = []

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

                # Check for !DUP and !MAKE switches if user is logged in
                dup_switch = False
                make_switch = False
                while collect[2][-1][0] == '!':
                    if collect[2][-1] == '!MAKE':
                        make_switch = True
                    elif collect[2][-1] == '!DUP':
                        dup_switch = True
                    collect[2] = collect[2][:-1]

                if not base['adm']:
                    make_switch = False

                # Check for race overrides
                def get_race(lst):
                    if lst[-1][:2].upper() == 'R:':
                        r = lst[-1][2:].upper() if lst[-1][2:].upper() in 'PTZR' else None
                        return r, lst[:-1]
                    else:
                        return None, lst
                rca, pla = get_race(pla)
                rcb, plb = get_race(plb)

                # Find players
                def get_player(lst, failure, make, adm):
                    try:
                        pls = find_player(lst, make=make)
                    except Exception as e:
                        failure.append((s, 'Could not parse: ' + e.message))
                        return None
                    if not pls.exists() and adm:
                        # Player not found, and user logged in. Add failure message and return None.
                        failure.append((s, 'Could not find player \'%s\', add !MAKE switch to create'\
                                % ' '.join(lst)))
                        return None
                    if pls.count() > 1 and adm:
                        # Too many players found, and used logged in. Add failure message and return None.
                        failure.append((s, 'Player \'%s\' not unique, provide more information'\
                                % ' '.join(lst)))
                        return None
                    if not pls.exists() or pls.count() > 1:
                        # Too many or too few players found, and user not logged in. Just return None.
                        return None
                    return pls[0]

                # If the user is logged in and some players were not found, abort.
                pla_obj = get_player(pla, failure, make_switch, base['adm'])
                if pla_obj == None and base['adm']:
                    continue

                plb_obj = get_player(plb, failure, make_switch, base['adm'])
                if plb_obj == None and base['adm']:
                    continue

                # If both players are known, check for duplicates
                if pla_obj and plb_obj:
                    n = find_duplicates(pla_obj, plb_obj, sca, scb, date)
                    if n > 0 and not dup_switch:
                        failure.append((s, '%i possible duplicates found, add !DUP switch to force' % n))
                        continue

                # If the user is not logged in, we now have enough information to create a prematch.
                if not base['adm']:
                    pm = PreMatch(group=pmgroup, sca=sca, scb=scb, pla=pla_obj, plb=plb_obj,\
                            pla_string=' '.join(pla), plb_string=' '.join(plb), date=pmgroup.date)
                    if rca:
                        pm.rca = rca
                    elif pla_obj:
                        pm.rca = pla_obj.race
                    else:
                        pm.rca = None

                    if rcb:
                        pm.rcb = rcb
                    elif plb_obj:
                        pm.rcb = plb_obj.race
                    else:
                        pm.rcb = None

                    pm.save()
                    success.append(pm)
                    continue

                # Abort if race information is incorrect
                if pla_obj.race == 'S' and rca == None:
                    failure.append((s, '%s is Random or Switcher, need race information' % pla_obj.tag))
                    continue

                if plb_obj.race == 'S' and rcb == None:
                    failure.append((s, '%s is Random or Switcher, need race information' % plb_obj.tag))
                    continue

                # Add match
                m = Match()
                m.pla = pla_obj
                m.plb = plb_obj
                m.sca = sca
                m.scb = scb
                m.rca = pla_obj.race if rca == None else rca
                m.rcb = plb_obj.race if rcb == None else rcb
                m.date = date
                m.event = event
                m.submitter = request.user
                m.set_period()
                m.eventobj = eventobj
                m.offline = offline
                m.game = game
                m.save()

                success.append(m)

            except ValueError as e:
                failure.append((s, 'Could not parse: ' + e.message))
                continue

        success = display_matches(success, fullpath=True)

        base.update({'messages': True, 'matches': '\n'.join([f[0] for f in failure]),\
                'success': success, 'failure': failure})

    base.update(csrf(request))
    return render_to_response('add.html', base)

def review_treat_players(pm, messages):
    def get_make_switch(lst):
        make_switch = False
        while lst[-1][0] == '!':
            if lst[-1] == '!MAKE':
                make_switch = True
                lst = lst[:-1]
        return lst, make_switch

    def get_race_info(lst):
        race = None
        while lst[-1][0:2].upper() == 'R:':
            race = lst[-1][2:].upper()
            lst = lst[:-1]
        return lst, race

    rca, rcb = None, None

    if not pm.pla:
        lst = list(pm.pla_string.split(' '))
        lst, make_switch_a = get_make_switch(lst)
        lst, rca = get_race_info(lst)
        pla = find_player(lst, make=make_switch_a)
        if pla.count() > 1:
            messages.append('Player not unique: \'%s\'. Add more information.' % ' '.join(lst))
        elif pla.count() == 0:
            messages.append('Player does not exist: \'%s\'. Add !MAKE switch to create.' % ' '.join(lst))
        else:
            pm.pla = pla[0]

    if rca:
        pm.rca = rca
    elif not pm.rca and pm.pla and pm.pla.race != 'S':
        pm.rca = pm.pla.race
    elif pm.pla and not pm.rca:
        messages.append('No race information for %s.' % str(pm.pla))

    if not pm.plb:
        lst = list(pm.plb_string.split(' '))
        lst, make_switch_b = get_make_switch(lst)
        lst, rcb = get_race_info(lst)
        plb = find_player(lst, make=make_switch_b)
        if plb.count() > 1:
            messages.append('Player not unique: \'%s\'. Add more information.' % ' '.join(lst))
        elif plb.count() == 0:
            messages.append('Player does not exist: \'%s\'. Add !MAKE switch to create.' % ' '.join(lst))
        else:
            pm.plb = plb[0]

    if rcb:
        pm.rcb = rcb
    elif not pm.rcb and pm.plb and pm.plb.race != 'S':
        pm.rcb = pm.plb.race
    elif pm.plb and not pm.rcb:
        messages.append('No race information for %s.' % str(pm.plb))

def review(request):
    base = base_ctx('Submit', 'Review', request)

    if not base['adm']:
        base.update(csrf(request))
        return render_to_response('login.html', base)

    base['user'] = request.user.username
    base['events'] = Event.objects.filter(closed=False, rgt=F('lft')+1).order_by('lft')

    if 'act' in request.POST and base['adm'] == True:
        if int(request.POST['eobj']) != 2:
            eobj = Event.objects.get(id=int(request.POST['eobj']))
        else:
            eobj = None

        etext = request.POST['event']

        delete = True if request.POST['act'] == 'reject' else False

        messages = []
        success = []

        for key in sorted(request.POST.keys()):
            if request.POST[key] != 'y':
                continue
            if key[0:6] == 'match-':
                pm = PreMatch.objects.get(id=int(key.split('-')[-1]))

                if delete:
                    group = pm.group
                    pm.delete()
                    if not group.prematch_set.all().exists():
                        group.delete()
                    continue
                
                if pm.pla == None:
                    pm.pla_string = request.POST['match-%i-pla' % pm.id]
                if pm.plb == None:
                    pm.plb_string = request.POST['match-%i-plb' % pm.id]

                if pm.pla == None or pm.plb == None:
                    review_treat_players(pm, messages)

                if pm.pla and not pm.rca:
                    pm.pla = None
                if pm.plb and not pm.rcb:
                    pm.plb = None

                pm.save()

                if pm.pla and pm.plb and pm.rca and pm.rcb:
                    m = Match()
                    m.pla = pm.pla
                    m.plb = pm.plb
                    m.sca = pm.sca
                    m.scb = pm.scb
                    m.rca = pm.rca
                    m.rcb = pm.rcb
                    if request.POST['date'].strip() == '':
                        m.date = pm.group.date
                    else:
                        m.date = request.POST['date']
                    m.event = etext if etext.strip() != '' else pm.group.event
                    m.eventobj = eobj
                    m.submitter = request.user
                    m.set_period()
                    m.offline = pm.group.offline
                    m.game = pm.group.game
                    m.save()
                    
                    success.append(m)

                    group = pm.group
                    pm.delete()
                    if not group.prematch_set.all().exists():
                        group.delete()

        base['messages'] = messages

        base['success'] = display_matches(success, fullpath=True)

    groups = PreMatchGroup.objects.filter(prematch__isnull=False)\
            .select_related('prematch').order_by('id', 'event').distinct()
    for g in groups:
        g.prematches = display_matches(g.prematch_set.all(), event_headers=False)
    base['groups'] = groups

    base.update(csrf(request))
    return render_to_response('review.html', base)

def manage_events(request):
    base = base_ctx('Submit', 'Events', request)

    if not base['adm']:
        base.update(csrf(request))
        return render_to_response('login.html', base)

    base['user'] = request.user.username

    if 'parent' in request.POST:
        if request.POST['op'] == 'Add':
            if 'big' in request.POST.keys():
                big = True
            else:
                big = False
            if 'noprint' in request.POST.keys():
                noprint = True
            else:
                noprint = False
                
            try:
                parent = Event.objects.get(id=int(request.POST['parent']))
                for q in request.POST['name'].strip().split(','):
                    type = request.POST['type']
                    parent.add_child(q.strip(), type, big, noprint)
            except:
                for q in request.POST['name'].strip().split(','):
                    if q.strip() == '':
                        continue
                    type = request.POST['type']
                    Event.add_root(q.strip(), type, big, noprint)

        elif request.POST['op'] == 'Close':
            try:
                parent = Event.objects.get(id=int(request.POST['parent']))
                parent.close()
            except:
                pass

    from django.db import connection
    cur = connection.cursor()
    cur.execute('''SELECT e.id, e.name, (COUNT(p.id)-1), e.parent_id, e.fullname AS depth, e.type 
                   FROM ratings_event AS e, ratings_event AS p
                   WHERE e.lft BETWEEN p.lft AND p.rgt AND e.id != 2 AND e.closed=0 
                   GROUP BY e.id ORDER BY e.lft''')
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
        foldnodes.append((nodes[i][0], nodes[i][1], nodes[i][2], fold, nodes[i][3], nodes[i][4], nodes[i][5]))
        totfold += fold

    base['nodes'] = foldnodes

    base.update(csrf(request))
    return render_to_response('eventmgr.html', base)

def manage(request):
    base = base_ctx('Submit', 'Misc', request)

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

    if 'op' in request.POST and request.POST['op'] == 'namerestore':
        for event in Event.objects.all():
            event.update_name()
        base['namerestore_succ'] = 'The names have been updated.'
        return render_to_response('manage.html', base)

    return render_to_response('manage.html', base)

def integrity(request):
    base = base_ctx('Submit', 'Integrity', request)

    if not base['adm']:
        base.update(csrf(request))
        return render_to_response('login.html', base)

    base['user'] = request.user.username
    base.update(csrf(request))

    with open(M_WARNINGS, 'r') as f:
        warnings = pickle.load(f)
    with open(M_APPROVED, 'r') as f:
        approved = pickle.load(f)

    if 'del' in request.POST or 'del_ok' in request.POST:
        for key in request.POST:
            if request.POST[key] != 'y':
                continue
            if key[0:6] == 'match-':
                try:
                    Match.objects.get(id=int(key.split('-')[-1])).delete()
                except:
                    pass

    if 'del_ok' in request.POST or 'false' in request.POST:
        warning = tuple([int(f) for f in request.POST['warning'].split(',')])
        warnings.remove(warning)
        approved.add(warning)

        with open(M_WARNINGS, 'w') as f:
            pickle.dump(warnings, f)
        with open(M_APPROVED, 'w') as f:
            pickle.dump(approved, f)

    matches = []
    for w in warnings:
        block = []
        for id in w:
            try:
                block.append(Match.objects.get(id=id))
            except:
                pass
        matches.append((','.join(str(k) for k in list(w)), display_matches(block, event_headers=False)))

        if len(matches) == 50:
            break
    base['matches'] = matches
    base['num'] = len(warnings)

    return render_to_response('integrity.html', base)
