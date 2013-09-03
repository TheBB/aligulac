from math import sqrt
from collections import namedtuple
from datetime import date

import aligulac.views
from ratings.models import Player, Match, PreMatch, Event, Earnings
from countries import data
from countries.transformations import cca3_to_ccn, ccn_to_cca2, cn_to_ccn

from django.db.models import Q, F, Sum, Max
from aligulac.parameters import RATINGS_INIT_DEV, KR_INIT
from numpy import tanh, arctanh, pi
from math import sqrt, exp

PATCHES = [(date(year=2010, month=10, day=14), '1.1.2'),
           (date(year=2011, month=3,  day=22), '1.3.0'),
           (date(year=2011, month=9,  day=20), '1.4.0'),
           (date(year=2012, month=2,  day=21), '1.4.3'),
           (date(year=2013, month=3,  day=12), 'HotS'),
           (date(year=2013, month=7,  day=11), '2.0.9 BU')]

def start_rating(country, period):
    if country == 'KR':
        return KR_INIT
    else:
        return 0.0

def prob_of_winning(rating_a=None, rating_b=None):
    if rating_a and rating_b:
        rtg_a = rating_a.get_totalrating(rating_b.player.race)
        dev_a = rating_a.get_totaldev(rating_b.player.race)
    elif rating_a:
        rtg_a = rating_a.get_totalrating('R')
        dev_a = rating_a.get_totaldev('R')
    else:
        rtg_a = 0
        dev_a = sqrt(2) * RATINGS_INIT_DEV

    if rating_b and rating_a:
        rtg_b = rating_b.get_totalrating(rating_a.player.race)
        dev_b = rating_b.get_totaldev(rating_a.player.race)
    elif rating_b:
        rtg_b = rating_b.get_totalrating('R')
        dev_b = rating_b.get_totaldev('R')
    else:
        rtg_b = 0
        dev_b = sqrt(2) * RATINGS_INIT_DEV

    return cdf(rtg_a-rtg_b, scale=sqrt(1.0+dev_a**2+dev_b**2))

def pdf(x, loc=0.0, scale=1.0):
    return pi/4/sqrt(3)/scale * (1 - tanh(pi/2/sqrt(3)*(x-loc)/scale)**2)

def cdf(x, loc=0.0, scale=1.0):
    return 0.5 + 0.5*tanh(pi/2/sqrt(3)*(x-loc)/scale)

def icdf(c, loc=0.0, scale=1.0):
    return loc + scale * 2*sqrt(3)/pi * arctanh(2*c - 1)

def filter_active_ratings(queryset):
    #return queryset.filter(decay__lt=4, dev__lt=0.2)
    return queryset.filter(decay__lt=4)

def filter_inactive_ratings(queryset):
    #return queryset.exclude(decay__lt=4, dev__lt=0.2)
    return queryset.exclude(decay__lt=4)

def add_ratings(matches):
    for match in matches:
        try:
            match.rta = match.pla.rating_set.get(period__id=match.period.id-1).get_totalrating(match.rcb)
        except:
            match.rta = ''
        try:
            match.rtb = match.plb.rating_set.get(period__id=match.period.id-1).get_totalrating(match.rca)
        except:
            match.rtb = ''
    
    return matches

def order_player(matches, player):
    for match in matches:
        if player == match.plb:
            temppl = match.pla
            tempsc = match.sca
            temprc = match.rca

            match.pla = match.plb
            match.sca = match.scb
            match.rca = match.rcb

            match.plb = temppl
            match.scb = tempsc
            match.rcb = temprc
            
            try:
                temprt = match.rta
                match.rta = match.rtb
                match.rtb = temprt
            except:
                pass
            
    return matches

def find_duplicates(pla, plb, sca, scb, date, incl_prematches=True):
    n = Match.objects.filter(pla=pla, plb=plb, sca=sca, scb=scb).extra(
            where=['abs(datediff(date,\'%s\')) < 2' % date]).count()
    n += Match.objects.filter(pla=plb, plb=pla, sca=scb, scb=sca).extra(
            where=['abs(datediff(date,\'%s\')) < 2' % date]).count()
    if incl_prematches:
        n += PreMatch.objects.filter(pla=pla, plb=plb, sca=sca, scb=scb).extra(
                where=['abs(datediff(date,\'%s\')) < 2' % date]).count()
        n += PreMatch.objects.filter(pla=plb, plb=pla, sca=scb, scb=sca).extra(
                where=['abs(datediff(date,\'%s\')) < 2' % date]).count()
    return n

def find_player(lst, make=False, soft=False):
    qset = Player.objects.all()

    for s in [s.strip() for s in lst if s.strip() != '']:
        # If numeric, assume it's a restriction on ID and nothing else
        if s.isdigit():
            qset = qset.filter(id=int(s))
            continue

        # Always search by player tag, team and aliases
        if soft:
            q = Q(tag__icontains=s) | Q(alias__name__icontains=s) |\
                Q(groupmembership__current=True, 
                  groupmembership__group__name__icontains=s,
                  groupmembership__group__is_team=True) |\
                Q(groupmembership__current=True, 
                  groupmembership__group__alias__name__icontains=s,
                  groupmembership__group__is_team=True)
        else:
            q = Q(tag__iexact=s) | Q(alias__name__iexact=s) |\
                Q(groupmembership__current=True, 
                  groupmembership__group__name__iexact=s,
                  groupmembership__group__is_team=True) |\
                Q(groupmembership__current=True, 
                  groupmembership__group__alias__name__iexact=s,
                  groupmembership__group__is_team=True)

        # Race query
        if len(s) == 1 and s.upper() in 'PTZSR':
            q |= Q(race=s.upper())

        # Country codes
        if len(s) == 2 and s.upper() in data.cca2_to_ccn:
            q |= Q(country=s.upper())
        if len(s) == 3 and s.upper() in data.cca3_to_ccn:
            q |= Q(country=ccn_to_cca2(cca3_to_ccn(s.upper())))
        renorm = s[0].upper() + s[1:].lower()
        if renorm in data.cn_to_ccn:
            q |= Q(country=ccn_to_cca2(cn_to_ccn(renorm)))

        qset = qset.filter(q)

    # Make player if needed and allowed
    if not qset.exists() and make:
        tag, country, race = None, None, None

        for s in [s.strip() for s in lst if s.strip() != '']:
            if s.isdigit():
                continue

            if len(s) == 1 and s.upper() in 'PTZSR':
                race = s.upper()
                continue

            if len(s) == 2 and s.upper() in data.cca2_to_ccn:
                country = s.upper()
                continue
            if len(s) == 3 and s.upper() in data.cca3_to_ccn:
                country = ccn_to_cca2(cca3_to_ccn(s.upper()))
                continue
            renorm = s[0].upper() + s[1:].lower()
            if renorm in data.cn_to_ccn:
                country = ccn_to_cca2(cn_to_ccn(renorm))
                continue

            tag = s

        if tag == None:
            raise Exception('Player \'' + ' '.join(lst) + '\' was not found and could not be made'\
                    + ' (missing player tag)')

        if race == None:
            raise Exception('Player \'' + ' '.join(lst) + '\' was not found and could not be made'\
                    + ' (missing race)')

        p = Player()
        p.tag = tag
        p.country = country
        p.race = race
        p.save()

        return Player.objects.filter(id=p.id)

    return qset.distinct()

def display_matches(matches, date=True, fix_left=None, ratings=False, messages=True):
    class M:
        pass
    ret = []

    prev_check = -1
    group_id = 0

    for idx, m in enumerate(matches):
        r = M()
        r.match = m
        r.match_id = m.id

        if type(m) == Match:
            r.game = m.game
            r.offline = m.offline
        else:
            r.game = m.group.game
            r.offline = m.group.offline

        r.treated = m.treated if type(m) == Match else False

        if date and type(m) == Match:
            r.date = m.date

        r.pla_id = m.pla_id
        r.plb_id = m.plb_id
        r.pla_tag = m.pla.tag if m.pla else m.pla_string
        r.plb_tag = m.plb.tag if m.plb else m.plb_string
        r.pla_race = m.rca
        r.plb_race = m.rcb
        r.pla_country = m.pla.country if m.pla else ''
        r.plb_country = m.plb.country if m.plb else ''
        r.pla_score = m.sca
        r.plb_score = m.scb

        if messages:
            r.messages = []
            for msg in m.message_set.all():
                r.messages.append(aligulac.views.Message(msg.text, msg.title, msg.type + '-small'))

        if ratings:
            try:
                rta = m.pla.rating_set.get(period__id=m.period_id-1)
                r.pla_rating = rta.get_totalrating(m.rcb)
                r.pla_dev = rta.get_totaldev(m.rcb)
            except:
                r.pla_rating = start_rating(r.pla_country, m.period_id)
                r.pla_dev = sqrt(2)*RATINGS_INIT_DEV

            try:
                rtb = m.plb.rating_set.get(period__id=m.period_id-1)
                r.plb_rating = rtb.get_totalrating(m.rca)
                r.plb_dev = rtb.get_totaldev(m.rca)
            except:
                r.plb_rating = start_rating(r.plb_country, m.period_id)
                r.plb_dev = sqrt(2)*RATINGS_INIT_DEV

        if fix_left is not None and fix_left.id == r.plb_id:
            r.pla_id,       r.plb_id      = r.plb_id,       r.pla_id
            r.pla_tag,      r.plb_tag     = r.plb_tag,      r.pla_tag
            r.pla_race,     r.plb_race    = r.plb_race,     r.pla_race
            r.pla_country,  r.plb_country = r.plb_country,  r.pla_country
            r.pla_score,    r.plb_score   = r.plb_score,    r.pla_score
            if ratings:
                r.pla_rating,  r.plb_rating = r.plb_rating,  r.pla_rating
                r.pla_dev,     r.plb_dev    = r.plb_dev,     r.pla_dev

        if type(m) == Match:
            if m.eventobj_id is not None:
                r.eventtext = m.eventobj.fullname
            elif m.event:
                r.eventtext = m.event 
        ret.append(r)

    return ret

def event_shift(event, diff):
    subtree = list(event.get_children()) + [event]
    width = event.rgt - event.lft + 1

    if diff > 0:
        Event.objects.filter(lft__gt=event.rgt, lft__lte=event.rgt+diff).update(lft=F('lft')-width)
        Event.objects.filter(rgt__gt=event.rgt, rgt__lte=event.rgt+diff).update(rgt=F('rgt')-width)
    elif diff < 0:
        Event.objects.filter(lft__gte=event.lft+diff, lft__lt=event.lft).update(lft=F('lft')+width)
        Event.objects.filter(rgt__gte=event.lft+diff, rgt__lt=event.lft).update(rgt=F('rgt')+width)

    for e in subtree:
        e.lft += diff
        e.rgt += diff
        e.save()

def get_placements(event):
    earningdict = {}
    for earning in Earnings.objects.filter(event=event).order_by('placement'):
        try:
            earningdict[earning.earnings].append(earning.placement)
        except:
            earningdict[earning.earnings] = [earning.placement]
    return earningdict

def add_earliest_latest():
    for event in Event.objects.all():
        print event
        event.update_dates()
