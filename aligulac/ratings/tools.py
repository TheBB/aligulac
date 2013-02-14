from math import sqrt

from ratings.models import Player, Match, PreMatch
from countries import data
from countries.transformations import cca3_to_ccn, ccn_to_cca2, cn_to_ccn

from django.db.models import Q, F, Sum, Max
from aligulac.settings import RATINGS_INIT_DEV
from numpy import tanh, pi
from math import sqrt, exp

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

def filter_active_ratings(queryset):
    return queryset.filter(decay__lt=5, dev__lt=0.2)

def sort_matches(matches, player, add_ratings=False):
    sc_my, sc_op = 0, 0

    for m in matches:
        if m.pla == player:
            m.sc_my, m.sc_op = m.sca, m.scb
            m.rc_my, m.rc_op = m.rca, m.rcb
            m.me, m.opp = m.pla, m.plb
        else:
            m.sc_my, m.sc_op = m.scb, m.sca
            m.rc_my, m.rc_op = m.rcb, m.rca
            m.me, m.opp = m.plb, m.pla

        sc_my += m.sc_my
        sc_op += m.sc_op

        if add_ratings:
            try:
                temp = m.opp.rating_set.get(period__id=m.period.id-1)
                m.rt_op = temp.get_totalrating(player.race)
                m.dev_op = temp.get_totaldev(player.race)
            except:
                m.rt_op = 0
                m.dev_op = sqrt(2)*RATINGS_INIT_DEV

            try:
                temp = m.me.rating_set.get(period__id=m.period.id-1)
                m.rt_my = temp.get_totalrating(m.rc_op)
                m.dev_my = temp.get_totaldev(m.rc_op)
            except:
                m.rt_my = 0
                m.dev_my = sqrt(2)*RATINGS_INIT_DEV

    return sc_my, sc_op

def group_by_events(matches):
    ret = []

    events = []
    for e in [m.eventobj for m in matches if m.eventobj != None]:
        if e not in events:
            events.append(e)

    for e in events:
        ret.append([m for m in matches if m.eventobj == e])

    events = []
    for e in [m.event for m in matches if m.eventobj == None]:
        if e not in events:
            events.append(e)

    for e in events:
        ret.append([m for m in matches if m.eventobj == None and m.event == e])

    ret = sorted(ret, key=lambda l: l[0].date, reverse=True)

    return ret

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
                    Q(teammembership__current=True, teammembership__team__name__icontains=s) |\
                    Q(teammembership__current=True, teammembership__team__alias__name__icontains=s)
        else:
            q = Q(tag__iexact=s) | Q(alias__name__iexact=s) |\
                    Q(teammembership__current=True, teammembership__team__name__iexact=s) |\
                    Q(teammembership__current=True, teammembership__team__alias__name__iexact=s)

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
