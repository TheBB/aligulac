import os, pickle
import urllib, urllib2
from pyparsing import nestedExpr

from aligulac.views import base_ctx, Message, NotUniquePlayerMessage
from aligulac.settings import M_WARNINGS, M_APPROVED
from ratings.tools import find_player, find_duplicates, display_matches

from django.shortcuts import render_to_response, get_object_or_404
from django.http import HttpResponse
from django.db.models import Q, Sum, F
from models import Period, Rating, Player, Match, Team, TeamMembership, Event, Earnings, PreMatchGroup, PreMatch
from django.contrib.auth import authenticate, login
from django.core.context_processors import csrf

from countries import transformations, data

class Integrity:
    pass

def add_login_message(base, extra=''):
    if not base['adm']:
        text = 'You are not logged in.' + (' ' if extra != '' else '') + extra\
             + ' (<a href="/login/">login</a>)'
        base['messages'].append(Message(text, type=Message.INFO))
    else:
        text = 'You are logged in as ' + base['user']\
             + ' (<a href="/logout/">logout</a>, <a href="/changepwd/">change password</a>)'
        base['messages'].append(Message(text, type=Message.INFO))

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
    add_login_message(base, extra='Submitted results will be pending review before inclusion.')

    # If the user is logged in, the template needs a username and a list of event objects
    if base['adm']:
        base['events'] = Event.objects.filter(closed=False, rgt=F('lft')+1).order_by('lft')

    if 'matches' in request.POST:
        # Collect various information from the form
        try:
            event = request.POST['event'].strip()
        except:
            event = None

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
            base['messages'].append(Message('Please do not submit more than 100 results at a time.',
                                         'Too many entries', Message.ERROR))
            base.update(csrf(request))
            return render_to_response('add.html', base)
        if not base['adm'] and source.strip() == '':
            base['messages'].append(Message('Please include a source.', 'Source missing', Message.ERROR))
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
                def get_player(lst, failure, base, make, adm):
                    try:
                        pls = find_player(lst, make=make)
                    except Exception as e:
                        failure.append(s)
                        base['messages'].append(Message('Could not parse: ' + e.message,
                                                        s, Message.ERROR))
                        return None
                    if not pls.exists() and adm:
                        # Player not found, and user logged in. Add failure message and return None.
                        failure.append(s)
                        base['messages'].append(Message(
                            'Could not find player \'%s\', add !MAKE switch to create.' % ' '.join(lst),
                            s, Message.ERROR))
                        return None
                    if pls.count() > 1 and adm:
                        # Too many players found, and used logged in. Add failure message and return None.
                        failure.append(s)
                        base['messages'].append(NotUniquePlayerMessage(' '.join(lst), pls))
                        return None
                    if not pls.exists() or pls.count() > 1:
                        # Too many or too few players found, and user not logged in. Just return None.
                        return None
                    return pls[0]

                # If the user is logged in and some players were not found, abort.
                pla_obj = get_player(pla, failure, base, make_switch, base['adm'])
                if pla_obj == None and base['adm']:
                    continue

                plb_obj = get_player(plb, failure, base, make_switch, base['adm'])
                if plb_obj == None and base['adm']:
                    continue

                # If both players are known, check for duplicates
                if pla_obj and plb_obj:
                    n = find_duplicates(pla_obj, plb_obj, sca, scb, date)
                    if n > 0 and not dup_switch:
                        failure.append(s)
                        base['messages'].append(Message(
                            '%i possible duplicate(s) found, add !DUP switch to force.' % n,
                            s, Message.ERROR))
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
                    failure.append(s)
                    base['messages'].append(Message(
                        '%s is Random or Switcher, need race information.' % pla_obj.tag),
                        s, Message.ERROR)
                    continue

                if plb_obj.race == 'S' and rcb == None:
                    failure.append(s)
                    base['messages'].append(Message(
                        '%s is Random or Switcher, need race information.' % plb_obj.tag),
                        s, Message.ERROR)
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
                m.submitter = request.user
                m.set_period()
                m.eventobj = eventobj
                m.offline = offline
                m.game = game
                m.save()

                success.append(m)

            except Exception as e:
                failure.append(s)
                base['messages'].append(Message('Could not parse: ' + e.message, s, Message.ERROR))
                continue

        success = display_matches(success, messages=False)
        if len(success) > 0:
            base['messages'].append(Message('Added %i match(es).' % len(success), type=Message.SUCCESS))

        base.update({'matches': '\n'.join(failure), 'success': success})

    base.update(csrf(request))
    return render_to_response('add.html', base)

def review_treat_players(pm, base):
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
            base['messages'].append(NotUniquePlayerMessage(' '.join(lst), pla))
        elif pla.count() == 0:
            base['messages'].append(Message('Player does not exist. Add !MAKE switch to create.',
                                            ' '.join(lst), type=Message.ERROR))
        else:
            pm.pla = pla[0]

    if rca:
        pm.rca = rca
    elif not pm.rca and pm.pla and pm.pla.race != 'S':
        pm.rca = pm.pla.race
    elif pm.pla and not pm.rca:
        base['messages'].append(Message('No race information for %s.' % str(pm.pla),
                                        'Race information missing', type=Message.ERROR))

    if not pm.plb:
        lst = list(pm.plb_string.split(' '))
        lst, make_switch_b = get_make_switch(lst)
        lst, rcb = get_race_info(lst)
        plb = find_player(lst, make=make_switch_b)
        if plb.count() > 1:
            base['messages'].append(NotUniquePlayerMessage(' '.join(lst), plb))
        elif plb.count() == 0:
            base['messages'].append(Message('Player does not exist. Add !MAKE switch to create.',
                                            ' '.join(lst), type=Message.ERROR))
        else:
            pm.plb = plb[0]

    if rcb:
        pm.rcb = rcb
    elif not pm.rcb and pm.plb and pm.plb.race != 'S':
        pm.rcb = pm.plb.race
    elif pm.plb and not pm.rcb:
        base['messages'].append(Message('No race information for %s.' % str(pm.plb),
                                        'Race information missing', type=Message.ERROR))

def review(request):
    base = base_ctx('Submit', 'Review', request)

    if not base['adm']:
        base.update(csrf(request))
        return render_to_response('login.html', base)

    add_login_message(base)
    base['events'] = Event.objects.filter(closed=False, rgt=F('lft')+1).order_by('lft')

    if 'act' in request.POST and base['adm'] == True:
        if int(request.POST['eobj']) != 2:
            eobj = Event.objects.get(id=int(request.POST['eobj']))
            base['eobj'] = eobj.id

        delete = True if request.POST['act'] == 'reject' else False

        success = []
        ndel = 0

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
                    ndel += 1
                    continue
                
                if pm.pla == None:
                    pm.pla_string = request.POST['match-%i-pla' % pm.id]
                if pm.plb == None:
                    pm.plb_string = request.POST['match-%i-plb' % pm.id]

                if pm.pla == None or pm.plb == None:
                    review_treat_players(pm, base)

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
                    m.event = pm.group.event
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

        base['success'] = display_matches(success, messages=False)
        if len(success) > 0:
            base['messages'].append(Message('Approved %i match(es).' % len(success), type=Message.SUCCESS))
        
        if ndel > 0:
            base['messages'].append(Message('Rejected %i match(es).' % ndel, type=Message.SUCCESS))

    groups = PreMatchGroup.objects.filter(prematch__isnull=False)\
            .select_related('prematch').order_by('id', 'event').distinct()
    for g in groups:
        g.prematches = display_matches(g.prematch_set.all(), messages=False)
    base['groups'] = groups

    base.update(csrf(request))
    return render_to_response('review.html', base)

def manage_events(request):
    base = base_ctx('Submit', 'Events', request)

    if not base['adm']:
        base.update(csrf(request))
        return render_to_response('login.html', base)

    add_login_message(base)

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
                
            nadd = 0
            try:
                parent = Event.objects.get(id=int(request.POST['parent']))
                for q in request.POST['name'].strip().split(','):
                    type = request.POST['type']
                    parent.add_child(q.strip(), type, noprint)
                    nadd += 1
                base['messages'].append(Message('Created %i children of \'%s\'.' % (nadd, parent.fullname),
                                                type=Message.SUCCESS))
            except:
                # No parent => create roots
                for q in request.POST['name'].strip().split(','):
                    if q.strip() == '':
                        continue
                    type = request.POST['type']
                    Event.add_root(q.strip(), type, big, noprint)
                    nadd += 1
                base['messages'].append(Message('Created %i new roots.' % nadd, type=Message.SUCCESS))

        elif request.POST['op'] == 'Close':
            try:
                parent = Event.objects.get(id=int(request.POST['parent']))
                parent.close()
                base['messages'].append(Message(
                    'Successfully closed \'%s\' and all its children.' % parent.fullname,
                    type=Message.SUCCESS))
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

def open_events(request):
    base = base_ctx('Submit', 'Open events', request)

    if not base['adm']:
        base.update(csrf(request))
        return render_to_response('login.html', base)

    add_login_message(base)
    base.update(csrf(request))

    if base['adm'] == True:
        if 'openevents' in request.POST:
            nclose = 0
            for event in request.POST.getlist('openevent'):
                Event.objects.get(id=event).close()
                nclose += 1
            base['messages'].append(Message('Closed %i events and their children.' % nclose,
                                            type=Message.SUCCESS))
        if 'prizepools' in request.POST:
            nmarked = 0
            for event in request.POST.getlist('prizepool'):
                Event.objects.get(id=event).set_prizepool(False)
                nmarked += 1
            base['messages'].append(Message('Marked %i events as having no prize pool.' % nmarked,
                                            type=Message.SUCCESS))

    openevents = []
    emptyopenevents = []
    noprizepoolevents = []
    events = Event.objects.filter(type="event", closed=False)
    ppevents = Event.objects.filter(prizepool__isnull=True, type="event", closed=True)
    
    for event in events:
        # If any of the subevents is not empty, add it to openevents.
        # Else it has no matches and so is added to emptyopenevents
        if Event.objects.filter(lft__gte=event.lft, rgt__lte=event.rgt, 
                                match__eventobj__isnull=False).exists():
            openevents.append(event)
        else:
            emptyopenevents.append(event)
            
    #exclude team events and empty events from no prize pool list 
    for event in ppevents:
        if event.get_root().category != "team" and Event.objects.filter(lft__gte=event.lft, rgt__lte=event.rgt, match__eventobj__isnull=False).exists():
            noprizepoolevents.append(event)

    #remove "unknown events"
    emptyopenevents = emptyopenevents[1:]
    noprizepoolevents = noprizepoolevents[1:]

    base['openevents'] = openevents
    base['emptyopenevents'] = emptyopenevents
    base['noprizepoolevents'] = noprizepoolevents

    return render_to_response('events_open.html', base)

def manage(request):
    base = base_ctx('Submit', 'Misc', request)

    if not base['adm']:
        base.update(csrf(request))
        return render_to_response('login.html', base)

    add_login_message(base)
    base.update(csrf(request))

    if 'op' in request.POST and request.POST['op'] == 'merge':
        try:
            base['player_source'] = request.POST['player_source']
            base['player_target'] = request.POST['player_target']
            source = Player.objects.get(id=int(request.POST['player_source']))
            target = Player.objects.get(id=int(request.POST['player_target']))
        except:
            base['messages'].append(Message('Failed to find players. One or more incorrect IDs.',
                                            title='Merge error', type=Message.ERROR))
            return render_to_response('manage.html', base)

        if 'conf' in request.POST and request.POST['conf'] == 'yes':
            Match.objects.filter(pla=source).update(pla=target, treated=False)
            Match.objects.filter(plb=source).update(plb=target, treated=False)
            Earnings.objects.filter(player=source).update(player=target)
            Rating.objects.filter(player=source).delete()
            TeamMembership.objects.filter(player=source).delete()
            sourcename = source.tag
            source.delete()

            base['messages'].append(Message('%s was successfully merged into %s.' % (sourcename, target.tag),
                                            title='Merging complete', type=Message.SUCCESS))
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
        base['messages'].append(Message('The NSM has been successfully restored.', 
                                        title='NSM restoration', type=Message.SUCCESS))
        return render_to_response('manage.html', base)

    if 'op' in request.POST and request.POST['op'] == 'namerestore':
        for event in Event.objects.all():
            event.update_name()
        base['messages'].append(Message('The event names have been successfully updated.', 
                                        title='Event name update', type=Message.SUCCESS))
        return render_to_response('manage.html', base)

    return render_to_response('manage.html', base)

def integrity(request):
    base = base_ctx('Submit', 'Integrity', request)

    if not base['adm']:
        base.update(csrf(request))
        return render_to_response('login.html', base)

    add_login_message(base)
    base.update(csrf(request))

    with open(M_WARNINGS, 'r') as f:
        warnings = pickle.load(f)
    with open(M_APPROVED, 'r') as f:
        approved = pickle.load(f)

    if 'del' in request.POST or 'del_ok' in request.POST:
        ndel = 0
        for key in request.POST:
            if request.POST[key] != 'y':
                continue
            if key[0:6] == 'match-':
                try:
                    Match.objects.get(id=int(key.split('-')[-1])).delete()
                    ndel += 1
                except:
                    pass
        base['messages'].append(Message('Deleted %i match(es).' % ndel, type=Message.SUCCESS))

    if 'del_ok' in request.POST or 'false' in request.POST:
        warning = tuple([int(f) for f in request.POST['warning'].split(',')])
        warnings.remove(warning)
        approved.add(warning)

        with open(M_WARNINGS, 'w') as f:
            pickle.dump(warnings, f)
        with open(M_APPROVED, 'w') as f:
            pickle.dump(approved, f)
        base['messages'].append(Message('Resolved one integrity warning.', type=Message.SUCCESS))

    matches = []
    for w in warnings:
        block = []
        for id in w:
            try:
                block.append(Match.objects.get(id=id))
            except:
                pass
        matches.append((','.join(str(k) for k in list(w)), display_matches(block, messages=False)))

        if len(matches) == 50:
            break

    base['matches'] = matches
    if len(matches) == 0:
        base['messages'].append(Message('There are currently no warnings pending resolution.', 
                                        type=Message.INFO))
    base['num'] = len(warnings)

    return render_to_response('integrity.html', base)
