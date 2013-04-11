from math import sqrt
from collections import namedtuple
from datetime import date

from ratings.models import Player, Match, PreMatch, Event, Earnings
from countries import data
from countries.transformations import cca3_to_ccn, ccn_to_cca2, cn_to_ccn

from django.db.models import Q, F, Sum, Max
from aligulac.parameters import RATINGS_INIT_DEV
from numpy import tanh, pi
from math import sqrt, exp

PATCHES = [(date(year=2010, month=10, day=14), '1.1.2'),
           (date(year=2011, month=3,  day=22), '1.3.0'),
           (date(year=2011, month=9,  day=20), '1.4.0'),
           (date(year=2012, month=2,  day=21), '1.4.3'),
           (date(year=2013, month=3,  day=12), 'HotS')]

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
    return queryset.filter(decay__lt=4, dev__lt=0.2)

def filter_inactive_ratings(queryset):
    return queryset.exclude(decay__lt=4, dev__lt=0.2)

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

def display_matches(matches, date=True, fix_left=None, ratings=False):
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

        if ratings:
            try:
                rta = m.pla.rating_set.get(period__id=m.period_id-1)
                r.pla_rating = rta.get_totalrating(m.rcb)
                r.pla_dev = rta.get_totaldev(m.rcb)
            except:
                r.pla_rating = 0
                r.pla_dev = sqrt(2)*RATINGS_INIT_DEV

            try:
                rtb = m.plb.rating_set.get(period__id=m.period_id-1)
                r.plb_rating = rtb.get_totalrating(m.rca)
                r.plb_dev = rtb.get_totaldev(m.rca)
            except:
                r.plb_rating = 0
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

def add_earnings_craftcupLite():
    eventid = 7148
    event = Event.objects.get(id=eventid)
    winners = {'Light #1':['Rigid'],'Light #2':['Jimpo'],'Light #3':['FuRy'],'Light #4':['cHoBo', 447],'Light #5':['PuReBall'],'Light #6':['inNirvana'],'Light #7':['FuRy', 347],'Light #8':['dske'],'Light #9':['Jimpo'],'Light #10':['Fenix'],'Light #11':['Snake'],'Light #12':['MoMaN'],'Light #13':['LESTER'],'Light #14':['ToHio'],'Light #15':['Kas'],'Light #16':['ZeeRaX'],'Light #17':['Splendour'],'Light #18':['Ciara'],'Light #19':['FuRy', 347],'Light #20':['Rikytan'],'Light #21':['slyCAT'],'Light #22':['SLiDeR'],'Light #23':['KiLLeR', 169],'Light #24':['inNirvana'],'Light #25':['Nerchio'],'Light #26':['KiLLeR', 169],'Light #27':['EffkA'],'Light #28':['Gomas'],'Light #29':['MoMaN'],'Light #30':['Beastyqt'],'Light #31':['Underdark'],'Light #32':['DeathAngel'],'Light #33':['mOoNan'],'Light #34':['StarEagle'],'Light #36':['Pomi'],'Light #37':['Beastyqt'],'Light #38':['Gomas'],'Light #39':['DDoRo'],'Light #40':['Seiplo'],'Light #42':['Beastyqt'],'Light #43':['LaLuSh'],'Light #44':['CuteZerg'],'Light #45':['sLivko'],'Light #46':['unix'],'Light #47':['Beastyqt'],'Light #48':['Beastyqt'],'Light #50':['Nerchio'],'Light #51':['biGs'],'Light #52':['Underdark'],'Light #53':['UkraineStar'],'Light #54':['Chelovek'],'Light #55':['LoWeLy'],'Light #56':['Kalin'],'Light #57':['Unix'],'Light #58':['DBS'],'Light #59':['Kalin'],'Light #60':['MeYera'],'Light #61':['DieStar'],'Light #62':['Tefel'],'Light #63':['RelaX'],'Light #64':['elfi'],'Light #65':['Unix'],'Light #66':['Tefel'],'Light #67':['Slider'],'Light #68':['roof'],'Light #69':['DeathAngel'],'Light #70':['RineTS'],'Light #71':['BlinG'],'Light #72':['LoZ'],'Light #73':['Onva'],'Light #74':['monchi'],'Light #75':['ninkum'],'Light #76':['MoMaN'],'Light #77':['sYz'],'Light #78':['RaNgeD'],'Light #79':['PoYo'],'Light #80':['sYz'],'Light #81':['UkraineStar'],'Light #82':['OutSide'],'Light #83':['Indy'],'Light #84':['Boroda'],'Light #85':['Steve'],'Light #86':['monchi'],'Light #87':['Ninkum'],'Light #88':['GoOdy'],'Light #89':['BlinG'],'Light #90':['Orly'],'Light #91':['Cosmos'],'Light #92':['BabyKnight'],'Light #93':['BlinG'],'Light #94':['Jaden'],'Light #95':['Kimo'],'Light #96':['ELVIS'],'Light #97':['Fargo'],'Light #98':['Ninkum'],'Light #99':['Elbegast'],'Light #100':['Tefel'],'Light #101':['AnNyeong'],'Light #102':['AnNyeong'],'Light #103':['Romson'],'Light #104':['Turuk'],'Light #105':['Kamikaze'],'Light #106':['Pomi'],'Light #107':['Pomi'],'Light #108':['RainMan'],'Light #109':['sYz'],'Light #110':['Tigr'],'Light #111':['Harstem'],'Light #112':['Ninkum'],'Light #113':['Druzdil'],'Light #114':['Affect'],'Light #115':['TheMista'],'Light #116':['KingCobra'],'Light #117':['Helios'],'Light #118':['Helios']}
    prize = 20
    currency = "USD"
    
    for ievent in event.get_children(type=["event"]):
        try:
            player = Player.objects.filter(tag=winners[ievent.name][0])
        except:
            continue
        if len(player) != 1:
            try:
                player = Player.objects.filter(tag=winners[ievent.name][0], id=winners[ievent.name][1])
            except:
                print ievent
                print winners[ievent.name][0]
                print player
        player = player[0]
        
        players = [player]
        earnings = [prize]
        placements = [0]
        print ievent
        print players
        print earnings
        
        Earnings.set_earnings(ievent, players, earnings, currency, placements)
        print "yay!"

def add_earnings_craftcup():
    eventid = 7148
    event = Event.objects.get(id=eventid)
    winners = {'#1':['Strelok'],'#2':['Strelok'],'#3':['Socke'],'#4':['NightEnD'],'#5':['NightEnd'],'#6':['SjoW'],'#7':['merz'],'#8':['Socke'],'#9':['SjoW'],'#10':['SjoW'],'#11':['SjoW'],'#12':['Tarson'],'#13':['Naugrim'],'#14':['DeathAngel'],'#15':['Brat_OK'],'#16':['Tarson'],'#17':['GoOdy'],'#18':['SjoW'],'#19':['Strelok'],'#20':['DeathAngel'],'#21':['Beastyqt'],'#22':['SjoW'],'#23':['GoOdy'],'#24':['GoOdy'],'#25':['NaNiwa'],'#26':['Strelok'],'#27':['Pomi'],'#28':['iNSoLeNCE'],'#29':['sYz'],'#30':['DIMAGA'],'#31':['Seiplo'],'#32':['GoOdy'],'#33':['Brat_OK'],'#34':['Kas'],'#35':['DIMAGA'],'#36':['Nerchio'],'#37':['Granath'],'#38':['Kas'],'#39':['Happy'],'#40':['Kalin'],'#41':['Osho'],'#42':['Clavie'],'#43':['Turuk'],'#44':['Bly'],'#45':['elfi'],'#46':['monchi'],'#47':['LaZ'],'#48':['sLivko'],'#49':['Tefel'],'#50':['HyuN'],'#51':['Nerchio'],'#52':['HyuN'],'#53':['Nerchio'],'#54':['Bly']}
    prize = 100
    currency = "USD"
    
    for ievent in event.get_children(type=["event"]):
        try:
            player = Player.objects.filter(tag=winners[ievent.name][0])
        except:
            continue
        if len(player) != 1:
            try:
                player = Player.objects.filter(tag=winners[ievent.name][0], id=winners[ievent.name][1])
            except:
                print ievent
                print winners[ievent.name][0]
                print player
        player = player[0]
        
        players = [player]
        earnings = [prize]
        placements = [0]
        print ievent
        print players
        print earnings
        
        Earnings.set_earnings(ievent, players, earnings, currency, placements)
        print "yay!"

def add_earnings_craftcuplite2():
    eventid = 7150
    event = Event.objects.get(id=eventid)
    winners = {'#1':['Rigid'],'#2':['Jimpo'],'#3':['FuRy'],'#4':['cHoBo', 447],'#5':['PuReBall'],'#6':['inNirvana'],'#7':['FuRy', 347],'#8':['dske'],'#9':['Jimpo'],'#10':['Fenix'],'#11':['Snake'],'#12':['MoMaN'],'#13':['LESTER'],'#14':['ToHio'],'#15':['Kas'],'#16':['ZeeRaX'],'#17':['Splendour'],'#18':['Ciara'],'#19':['FuRy', 347],'#20':['Rikytan'],'#21':['slyCAT'],'#22':['SLiDeR'],'#23':['KiLLeR', 169],'#24':['inNirvana'],'#25':['Nerchio'],'#26':['KiLLeR', 169],'#27':['EffkA'],'#28':['Gomas'],'#29':['MoMaN'],'#30':['Beastyqt'],'#31':['Underdark'],'#32':['DeathAngel'],'#33':['mOoNan'],'#34':['StarEagle'],'#36':['Pomi'],'#37':['Beastyqt'],'#38':['Gomas'],'#39':['DDoRo'],'#40':['Seiplo'],'#42':['Beastyqt'],'#43':['LaLuSh'],'#44':['CuteZerg'],'#45':['sLivko'],'#46':['unix'],'#47':['Beastyqt'],'#48':['Beastyqt'],'#50':['Nerchio'],'#51':['biGs'],'#52':['Underdark'],'#53':['UkraineStar'],'#54':['Chelovek'],'#55':['LoWeLy'],'#56':['Kalin'],'#57':['Unix'],'#58':['DBS'],'#59':['Kalin'],'#60':['MeYera'],'#61':['DieStar'],'#62':['Tefel'],'#63':['RelaX'],'#64':['elfi'],'#65':['Unix'],'#66':['Tefel'],'#67':['Slider'],'#68':['roof'],'#69':['DeathAngel'],'#70':['RineTS'],'#71':['BlinG'],'#72':['LoZ'],'#73':['Onva'],'#74':['monchi'],'#75':['ninkum'],'#76':['MoMaN'],'#77':['sYz'],'#78':['RaNgeD'],'#79':['PoYo'],'#80':['sYz'],'#81':['UkraineStar'],'#82':['OutSide'],'#83':['Indy', 362],'#84':['Boroda'],'#85':['Steve'],'#86':['monchi'],'#87':['Ninkum'],'#88':['GoOdy'],'#89':['BlinG'],'#90':['Orly'],'#91':['Cosmos'],'#92':['BabyKnight'],'#93':['BlinG'],'#94':['Jaden'],'#95':['Kimo'],'#96':['ELVIS'],'#97':['Fargo'],'#98':['Ninkum'],'#99':['Elbegast'],'#100':['Tefel'],'#101':['AnNyeong'],'#102':['AnNyeong'],'#103':['Romson'],'#104':['Turuk'],'#105':['Kamikaze'],'#106':['Pomi'],'#107':['Pomi'],'#108':['RainMan'],'#109':['sYz'],'#110':['Tigr'],'#111':['Harstem'],'#112':['Ninkum'],'#113':['Druzdil'],'#114':['Affect'],'#115':['TheMista'],'#116':['KingCobra'],'#117':['Helios'],'#118':['Helios']}
    prize = 20
    currency = "USD"
    
    for ievent in event.get_children(type=["event"]):
        try:
            player = Player.objects.filter(tag=winners[ievent.name][0])
        except:
            continue
        if len(player) != 1:
            try:
                player = Player.objects.filter(tag=winners[ievent.name][0], id=winners[ievent.name][1])
            except:
                print ievent
                print winners[ievent.name][0]
                print player
        player = player[0]
        
        players = [player]
        earnings = [prize]
        placements = [0]
        print ievent
        print players
        print earnings
        
        Earnings.set_earnings(ievent, players, earnings, currency, placements)
        print "yay!"
        
def add_earnings_craftcupcombined():
    eventid = 7151
    event = Event.objects.get(id=eventid)
    winners = {'#1':['Strelok'],'#2':['Strelok'],'#3':['Socke'],'#4':['NightEnD'],'#5':['NightEnd'],'#6':['SjoW'],'#7':['merz'],'#8':['Socke'],'#9':['SjoW'],'#10':['SjoW'],'#11':['SjoW'],'#12':['Tarson'],'#13':['Naugrim'],'#14':['DeathAngel'],'#15':['Brat_OK'],'#16':['Tarson'],'#17':['GoOdy'],'#18':['SjoW'],'#19':['Strelok'],'#20':['DeathAngel'],'#21':['Beastyqt'],'#22':['SjoW'],'#23':['GoOdy'],'#24':['GoOdy'],'#25':['NaNiwa'],'#26':['Strelok'],'#27':['Pomi'],'#28':['iNSoLeNCE'],'#29':['sYz'],'#30':['DIMAGA'],'#31':['Seiplo'],'#32':['GoOdy'],'#33':['Brat_OK'],'#34':['Kas'],'#35':['DIMAGA'],'#36':['Nerchio'],'#37':['Granath'],'#38':['Kas'],'#39':['Happy'],'#40':['Kalin'],'#41':['Osho'],'#42':['Clavie'],'#43':['Turuk'],'#44':['Bly'],'#45':['elfi'],'#46':['monchi'],'#47':['LaZ'],'#48':['sLivko'],'#49':['Tefel'],'#50':['HyuN'],'#51':['Nerchio'],'#52':['HyuN'],'#53':['Nerchio'],'#54':['Bly']}
    prize = 100
    currency = "USD"
    
    for ievent in event.get_children(type=["event"]):
        try:
            player = Player.objects.filter(tag=winners[ievent.name][0])
        except:
            continue
        if len(player) != 1:
            try:
                player = Player.objects.filter(tag=winners[ievent.name][0], id=winners[ievent.name][1])
            except:
                print ievent
                print winners[ievent.name][0]
                print player
        player = player[0]
        
        players = [player]
        earnings = [prize]
        placements = [0]
        print ievent
        print players
        print earnings
        
        Earnings.set_earnings(ievent, players, earnings, currency, placements)
        print "yay!"

def add_earnings_cyborgcup():
    eventid = 11774
    event = Event.objects.get(id=eventid)
    winners = {'#1':['Socke'],'#2':['GoOdy'],'#3':['DIMAGA'],'#4':['SjoW'],'#5':['DIMAGA'],'#6':['NightEnD'],'#7':['DIMAGA'],'#8':['DIMAGA'],'#9':['Satiini'],'#10':['INSoLeNCE'],'#11':['TLO'],'#12':['MaNa'],'#13':['Happy', 95],'#14':['Happy', 95],'#15':['MaNa'],'#16':['Kas'],'#17':['DIMAGA'],'#18':['Welmu'],'#19':['Bly'],'#20':['Happy', 95],'#21':['DIMAGA'],'#22':['HyuN']}
    prize = 200
    currency = "EUR"
    
    for ievent in event.get_children(type=["event"]):
        try:
            player = Player.objects.filter(tag=winners[ievent.name][0])
        except:
            continue
        if len(player) != 1:
            try:
                player = Player.objects.filter(tag=winners[ievent.name][0], id=winners[ievent.name][1])
            except:
                print ievent
                print winners[ievent.name][0]
                print player
        player = player[0]
        
        players = [player]
        earnings = [prize]
        placements = [0]
        print ievent
        print players
        print earnings
        
        Earnings.set_earnings(ievent, players, earnings, currency, placements)
        print "yay!"

def add_earnings_closecombat2010():
    eventid = 10387
    event = Event.objects.get(id=eventid)
    winners = {'1':[['DasDuelon'],['Delphi']],'2':[['GoOdy'],['DasDuelon']],'3':[['Rine'],['Lefy']],'4':[['cHoBo'],['nukular00']],'5':[['Delphi'],['inuh']],'6':[['HasuObs'],['Risk']],'7':[['Socke'],['iLuvatar']],'8':[['Socke'],['Rine']],'9':[['GoOdy'],['JuNe']],'10':[['GoOdy'],['Wilko']],'11':[['HasuObs'],['Druzdil']],'12':[['GoOdy'],['Delphi']],'13':[['ClouD', 227],['Bly']],'14':[['GoOdy'],['cHoBo', 447]],'15':[['Brat_OK'],['GoOdy']],'16':[['OutSide'],['HasuObs']],'17':[['Brat_OK'],['GoOdy']],'18':[['mOoNan'],['Tarson']],'19 ESET':[['Brat_OK'],['inuh']],'20':[['GoOdy'],['HasuObs']],'21':[['merz'],['SjoW']],'22':[['DarKFoRcE'],['Seiplo']],'23':[['Kas'],['Tarson']],'24':[['NightEnD'],['HasuObs']],'25':[['Miou'],['LoCo']],'26':[['GoOdy'],['NightEnD']],'27':[['Tefel'],['DarKFoRcE']],'28':[['DieStar'],['Rikytan']]}
    prize = [125, 50, 25]
    currency = "EUR"
    
    for ievent in event.get_children(type=["event"]):
        players = []
        for j in range(0,2):
            try:
                player = Player.objects.filter(tag=winners[ievent.name][j][0])
            except:
                continue
            if len(player) != 1:
                try:
                    player = Player.objects.filter(tag=winners[ievent.name][j][0], id=winners[ievent.name][j][1])
                except:
                    print ievent
                    print winners[ievent.name][j][0]
                    print player
                    print prize[j]
            player = player[0]
            players.append(player)
        
        matches = Match.objects.filter(eventobj=ievent)
        matches = matches.exclude(Q(pla=players[0]) | Q(plb=players[0]))
        matches = matches.exclude(Q(pla=players[1]) | Q(plb=players[1]))
        
        if len(matches) != 1:
            continue

        try:
            if matches[0].sca > matches[0].scb:
                third = matches[0].pla
            else:
                third = matches[0].plb
            players.append(third)
        except:
            continue
        
        earnings = prize
        placements = [0, 1, 2]
        print ievent
        print players
        print earnings
        
        Earnings.set_earnings(ievent, players, earnings, currency, placements)
        print "yay!"

def add_earnings_closecombat2011():
    eventid = 10388
    event = Event.objects.get(id=eventid)
    winners = {'1':[['Socke'],['sYz']],'2 ESET':[['Beastyqt'],['Nerchio']],'3':[['DarKFoRcE'],['Bly']],'5':[['Insolence'],['LoCo']],'7':[['DieStar'],['SjoW']],'9':[['HasuObs'],['Nerchio']],'11':[['SjoW'],['DieStar']],'12':[['Nerchio'],['GoOdy']],'14':[['SeleCT'],['Underdark']],'15':[['Nerchio'],['Insolence']],'17':[['SLiDeR'],['LaLuSh']],'18':[['HasuObs'],['Nerchio']],'20':[['DieStar'],['Wilko']],'21':[['DieStar'],['Pomi']],'25':[['DarKFoRcE'],['HasuObs']],'27':[['Nerchio'],['GoOdy']],'29':[['DeathAngel'],['Nerchio']],'31':[['sYz'],['LaLuSh']],'33':[['StarEagle'],['Underdark']],'35':[['DieStar'],['AcRo']],'37':[['Happy', 95],['ActionJesuz']],'39':[['Masterok'],['ALF']],'41':[['Bly'],['Seiplo']],'43':[['Nerchio'],['sYz']],'45':[['Delphi'],['Roll']],'47':[['Happy', 95],['DIMAGA']],'49':[['Beastyqt'],['Snute']],'51':[['Happy', 95],['DBS']],'53':[['Kas'],['rine']],'55':[['Nerchio'],['Goody']],'57':[['SjoW'],['SLiDeR']],'59':[['SjoW'],['Delphi']],'61':[['GoOdy'],['Lalush']],'63':[['GoOdy'],['Bly']],'65':[['GoOdy'],['HasuObs']],'67':[['DarKFoRcE'],['DIMAGA']],'69':[['monchi'],['mEtRo']],'70':[['DIMAGA'],['Beastyqt']],'71':[['sYz'],['OutSide']],'72':[['sYz'],['HobbyPlayer']],'73':[['monchi'],['White']],'74':[['biGs'],['Happy']],'75':[['BabyKnight'],['Feast']],'76':[['Happy'],['Outside']],'77':[['HappyZerg'],['ALF']],'78':[['Fuzer'],['BabyKnight']],'79':[['Fenix'],['LaLuSh']],'80':[['Happy'],['Nerchio']],'81':[['LoWeLy'],['inNirvana']],'83':[['Bly'],['sYz']]}
    prize = [125, 50, 25]
    currency = "EUR"
    
    for ievent in event.get_children(type=["event"]):
        players = []
        for j in range(0,2):
            try:
                player = Player.objects.filter(tag=winners[ievent.name][j][0])
            except:
                continue
            if len(player) != 1:
                try:
                    player = Player.objects.filter(tag=winners[ievent.name][j][0], id=winners[ievent.name][j][1])
                except:
                    print ievent
                    print winners[ievent.name][j][0]
                    print player
                    print prize[j]
            player = player[0]
            players.append(player)
        
        try:
            matches = Match.objects.filter(eventobj=ievent)
            matches = matches.exclude(Q(pla=players[0]) | Q(plb=players[0]))
            matches = matches.exclude(Q(pla=players[1]) | Q(plb=players[1]))
        except:
            continue
        
        if len(matches) != 1:
            continue
        
        try:
            if matches[0].sca > matches[0].scb:
                third = matches[0].pla
            else:
                third = matches[0].plb
            players.append(third)
        except:
            continue
        
        earnings = prize
        placements = [0, 1, 2]
        print ievent
        print players
        print earnings
        
        Earnings.set_earnings(ievent, players, earnings, currency, placements)
        print "yay!"


def add_earnings_go4sc2_NA():
    eventid = 11635
    event = Event.objects.get(id=eventid)
    prize = 50
    currency = "USD"
    
    for ievent in event.get_children(type=["event"]):
        
        weekday = ievent.get_earliest().weekday()
        #Only Sunday cups have prize pool, so filter out those
        #Also grab games on Monday due to time zone errors
        if weekday == 6 or weekday == 0:
            winnercount = {}
            winners = []
            losers = []
            for match in Match.objects.filter(eventobj=ievent):
                #Throw all winners and losers into a separate array
                #Also count number of wins per player in a dictionary
                if match.sca > match.scb:
                    if match.pla not in winners:
                        winners.append(match.pla)
                    if match.plb not in losers:
                        losers.append(match.plb)
                    if match.pla not in winnercount:
                        winnercount[match.pla] = 1
                    else:
                        winnercount[match.pla] += 1
                else:
                    if match.plb not in winners:
                        winners.append(match.plb)
                    if match.pla not in losers:
                        losers.append(match.pla)
                    if match.plb not in winnercount:
                        winnercount[match.plb] = 1
                    else:
                        winnercount[match.plb] += 1
            #Substract losers list from winners list, leaving only playeres that haven't lost 
            winnerlist = [x for x in winners if x not in losers]
            #Remove all players that have lost a game from the winnercount dictionary
            for k,v in winnercount.items():
                if k not in winnerlist:
                    del winnercount[k]
            #Determine the winner: The player who never lost a game and won the most games
            winner = max(winnercount, key=winnercount.get)
        
            earnings = [prize]
            players = [winner]
            placements = [0]
            print ievent
            print players
            print earnings
        
            Earnings.set_earnings(ievent, players, earnings, currency, placements)
            print "yay!"