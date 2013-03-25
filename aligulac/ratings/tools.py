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
            if m.eventobj:
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

def add_earnings_regularcup():
    eventid = 9860    
    event = Event.objects.get(id=eventid)
    winners = {'#23':['DIMAGA'], '#22':['Kas'], '#21':['Brat_OK'], '#20':['Happy', 95], '#19':['fraer'], '#18':['Noname'], '#17':['fraer'], '#15':['HappyZerg'], '#14':['Noname'], '#13':['Kas'], '#12':['fraer'], '#11':['Bly'], '#10':['Happy', 95], '#9':['Happy', 95], '#8':['fraer'], '#7':['Happy', 95], '#6':['sLivko'], '#5':['Happy', 95], '#4':['fraer'], '#3':['Happy', 95], '#2':['Verdi'], '#1':['Bly']}
    prize = 100
    currency = "USD"
    
    for ievent in event.get_children(type=["event"]):
        player = Player.objects.filter(tag=winners[ievent.name][0])
        if len(player) != 1:
            player = Player.objects.filter(tag=winners[ievent.name][0], id=winners[ievent.name][1])
        player = player[0]
        
        players = [player]
        earnings = [prize]
        placements = [0]
        
        Earnings.set_earnings(ievent, players, earnings, currency, placements)
        print "yay!"

def add_earnings_zotacNA():
    eventid = 3083    
    event = Event.objects.get(id=eventid)
    winners = {'#83':['Sage'], '#82':['Arthur'], '#81':['MaSa'], '#80':['Vasilisk'], '#79':['MaSsan'], '#78':['Dreamertt'], '#77':['HyuN'], '#76':['HyuN'], '#75':['Crane'], '#74':['StarDust'], '#73':['Tree'], '#72':['Revival'], '#71':['dde'], '#70':['Tree'], '#69':['inori'], '#68':['inori'], '#67':['aLive'], '#66':['Crane'], '#65':['dde'], '#64':['Min'], '#63':['Symbol'], '#62':['HyuN'], '#61':['HyuN'], '#60':['Revival'], '#59':['HyuN'], '#58':['HyuN'], '#57':['ByuN'], '#56':['Polt'], '#55':['Daisy'], '#54':['HyuN'], '#53':['HyuN'], '#52':['HyuN'], '#51':['Revival'], '#50':['HyuN'], '#49':['dreamertt'], '#48':['Mentalist'], '#47':['ByuN'], '#46':['inori'], '#45':['Revival'], '#44':['ByuN'], '#43':['Crane'], '#42':['Sleep'], '#41':['Revival'], '#40':['Crane'], '#39':['Sleep'], '#38':['Shine', 62], '#37':['Crane'], '#36':['Golden'], '#35':['Lucky'], '#34':['horror', 277], '#33':['KiLLeR', 169], '#32':['Tree'], '#31':['Lucky'], '#30':['ReaL'], '#29':['Sleep'], '#28':['ByuN'], '#27':['Sleep'], '#26':['Sleep'], '#25':['Monster', 30], '#24':['AnNyeong'], '#23':['CrazymoviNG'], '#22':['Skit'], '#21':['Terius'], '#20':['Galaxy', 205], '#19':['Deezer'], '#18':['dde'], '#17':['Gatored'], '#16':['PeGaSuS'], '#15':['Revival'], '#14':['HwangSin'], '#13':['sC'], '#12':['sC'], '#11':['MajOr'], '#10':['Check'], '#9':['HwangSin'], '#8':['LastShadow'], '#7':['Fenix'], '#6':['Gatored'], '#5':['Gatored'], '#4':['GoOdy'], '#3':['GoOdy'], '#2':['LastShadow'], '#1':['Drewbie']}
    prize = 100
    currency = "USD"
    
    for ievent in event.get_children(type=["event"]):
        try:
            player = Player.objects.filter(tag=winners[ievent.name][0])
        except:
            break
        if len(player) != 1:
            try:
                player = Player.objects.filter(tag=winners[ievent.name][0], id=winners[ievent.name][1])
            except:
                print player
                print winners[ievent.name][0]
                print ievent
        player = player[0]
        
        players = [player]
        earnings = [prize]
        placements = [0]
        print players
        print earnings
        print ievent
        
        Earnings.set_earnings(ievent, players, earnings, currency, placements)
        print "yay!"
        
def add_earnings_zotacEU():
    eventid = 596    
    event = Event.objects.get(id=eventid)
    winners = {'#138':['LiveZerg'],'#137':['fraer'],'#136':['Welmu'],'#135':['LiveZerg'],'#134':['ReaL'],'#133':['roof'],'#132':['Bly'],'#131':['Nerchio'],'#130':['Acro'],'#129':['MilkEA'],'#128':['Happy', 95],'#127':['LoWeLy'],'#126':['LoWeLy'],'#125':['fraer'],'#124':['Welmu'],'#123':['sLivko'],'#122':['Revival'],'#121':['Nerchio'],'#120':['LiveZerg'],'#119':['ReaL'],'#118':['roof'],'#117':['VortiX'],'#116':['Nerchio'],'#115':['TitaN', 60],'#114':['Kas'],'#113':['elfi'],'#112':['Bly'],'#111':['Revival'],'#110':['Revival'],'#109':['elfi'],'#108':['Bly'],'#107':['Nerchio'],'#106':['fraer'],'#105':['Bly'],'#104':['Welmu'],'#103':['Sleep'],'#102':['VortiX'],'#101':['LiveZerg'],'#100':['LiveZerg'],'#99':['Nerchio'],'#98':['fraer'],'#97':['Bly'],'#96':['Bly'],'#95':['fraer'],'#94':['sLivko'],'#93':['Happy', 95],'#92':['Happy', 95],'#91':['monchi'],'#90':['Krr'],'#89':['NoXOuT'],'#88':['Bly'],'#87':['GoOdy'],'#86':['sLivko'],'#85':['Beastyqt'],'#84':['roof'],'#83':['GoOdy'],'#82':['TAiLS', 112],'#81':['CoolTea'],'#80':['Nerchio'],'#79':['GoOdy'],'#78':['SLiDeR'],'#77':['Deezer'],'#76':['Nerchio'],'#75':['GoOdy'],'#74':['DarKFoRcE'],'#73':['roof'],'#72':['Nerchio'],'#71':['GoOdy'],'#70':['Satiini'],'#69':['LucifroN'],'#68':['Satiini'],'#67':['Tarson'],'#66':['Satiini'],'#65':['roof'],'#64':['Beastyqt'],'#63':['Nerchio'],'#62':['Nerchio'],'#61':['Nerchio'],'#60':['GoOdy'],'#59':['Nerchio'],'#58':['Nerchio'],'#57':['Strelok'],'#56':['DIMAGA'],'#55':['elfi'],'#54':['elfi'],'#53':['LoWeLy'],'#52':['Satiini'],'#51':['GoOdy'],'#50':['Tarson'],'#49':['Jimpo'],'#48':['GoOdy'],'#47':['Strelok'],'#46':['VortiX'],'#45':['elfi'],'#44':['Strelok'],'#43':['GoOdy'],'#42':['Tefel'],'#41':['elfi'],'#40':['AureS'],'#39':['elfi'],'#38':['Nerchio'],'#37':['Strelok'],'#36':['NaNiwa'],'#35':['Strelok'],'#34':['Strelok'],'#33':['Satiini'],'#32':['NaNiwa'],'#31':['Control'],'#30':['GoOdy'],'#29':['Kas'],'#28':['Kas'],'#27':['DIMAGA'],'#26':['LucifroN'],'#25':['DIMAGA'],'#24':['PredY'],'#23':['LucifroN'],'#22':['Strelok'],'#21':['SeleCT'],'#20':['Kas'],'#19':['SjoW'],'#18':['MorroW'],'#17':['SjoW']}
    prize = 100
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
                print player
                print winners[ievent.name][0]
                print ievent
        player = player[0]
        
        players = [player]
        earnings = [prize]
        placements = [0]
        print players
        print earnings
        print ievent
        
        Earnings.set_earnings(ievent, players, earnings, currency, placements)
        print "yay!"

def add_earnings_tlopen():
    eventid = 10912    
    event = Event.objects.get(id=eventid)
    prizes = [100, 50, 25, 25]
    currency = "USD"
    first, second, third, fourth = '', '', '', ''
    
    for ievent in event.get_children(type=["event"]):
        if ievent.name != "#1":
            for childievent in ievent.get_children():
                if childievent.name == "Final":
                    matches = Match.objects.filter(eventobj=childievent)
                    final = matches[0]
                    if final.sca > final.scb:
                        first = final.pla
                        second = final.plb
                    else:
                        first = final.plb
                        second = final.pla
                if childievent.name == "Ro4":
                    matches = Match.objects.filter(eventobj=childievent)
                    sfinal1 = matches[0]
                    sfinal2 = matches[1]
                    if sfinal1.sca > sfinal1.scb:
                        third = sfinal1.plb
                    else:
                        third = sfinal1.pla
                    if sfinal2.sca > sfinal2.scb:
                        fourth = sfinal2.plb
                    else:
                        fourth = sfinal2.pla
        
            players = [first, second, third, fourth]
            placements = [0, 1, 2, 3]
            print ievent
            print players
            print prizes
        
            Earnings.set_earnings(ievent, players, prizes, currency, placements)
            print "yay!"

def add_earnings_craftcupUS():
    eventid = 7149    
    event = Event.objects.get(id=eventid)
    winners = {'#1':['qxc'],'#2':['Fenix'],'#3':['MurDeR'],'#4':['Ryze'],'#5':['Socke'],'#6':['DdoRo'],'#7':['Greatman'],'#8':['mihai'],'#9':['Levin'],'#10':['Fan'],'#11':['Killer', 169],'#12':['Skillet'],'#13':['DdoRo'],'#14':['OpTiKzErO'],'#15':['Spades'],'#16':['Rigid'],'#17':['mkengyn'],'#18':['BigBadBeaver'],'#19':['OpTiKzErO'],'#20':['ThisIsJimmy'],'#21':['PhiliBiRD'],'#22':['OpTiKzErO'],'#23':['Attero'],'#24':['GoOdy'],'#25':['NGry'],'#26':['GoOdy'],'#27':['Grubby'],'#28':['owmygroin'],'#29':['Bio'],'#30':['DarkDreaMs'],'#31':['SungpA'],'#32':['MarinekngXPn'],'#33':['MeYera'],'#34':['Blast'],'#35':['KWest'],'#36':['sYz'],'#37':['RaNgeD'],'#38':['OnlyToss'],'#39':['nukestrike'],'#40':['Forbs'],'#41':['gun'],'#42':['gun'],'#43':['gun'],'#44':['Glon'],'#45':['Gun'],'#46':['Seiplo'],'#47':['Seiplo'],'#48':['dde'],'#49':['dde'],'#50':['TriMaster'],'#51':['dde']}
    prize = 20
    currency = "USD"
    
    for ievent in event.get_children(type=["event"]):
        try:
            player = Player.objects.filter(tag=winners[ievent.name][0])
        except:
            break
        if len(player) != 1:
            try:
                player = Player.objects.filter(tag=winners[ievent.name][0], id=winners[ievent.name][1])
            except:
                print player
                print winners[ievent.name][0]
                print ievent
        player = player[0]
        
        players = [player]
        earnings = [prize]
        placements = [0]
        print ievent
        print players
        print earnings
        
        Earnings.set_earnings(ievent, players, earnings, currency, placements)
        print "yay!"


def add_earnings_competocup():
    eventid = 10188    
    event = Event.objects.get(id=eventid)
    winners = {'#47':['Orly'],'#46':['sYz'],'#45':['Beastyqt'],'#44':['elfi'],'#43':['elfi'],'#42':['Rikytan'],'#41':['Naama'],'#40':['GoOdy'],'#39':['Beastyqt'],'#38':['Beastyqt'],'#37':['Happy', 40],'#36':['DeathAngel'],'#35':['Happy', 40],'#34':['Tarson'],'#33':['Bly'],'#32':['Seiplo'],'#31':['Beastyqt'],'#30':['Elfi'],'#29':['Elfi'],'#28':['SKy', 584],'#27':['MorroW'],'#26':['Kas'],'#25':['GoOdy'],'#24':['iNSoLeNCE'],'#23':['Elfi'],'#22':['Kas'],'#21':['DieStar'],'#20':['GoOdy'],'#19':['Kas'],'#18':['iNSoLeNCE'],'#17':['Jimpo'],'#16':['eNvious'],'#15':['eNvious'],'#14':['Damnosaurus'],'#13':['Naama'],'#12':['Kas'],'#11':['Tefel'],'#10':['Bly'],'#9':['NightEnD'],'#7':['SeleCT'],'#6':['MorroW'],'#5':['Kas'],'#4':['ClouD', 227],'#3':['Sein'],'#2':['SjoW'],'#1':['GoOdy']}
    prize = 50
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
                print player
                print winners[ievent.name][0]
                print ievent
        player = player[0]
        
        players = [player]
        earnings = [prize]
        placements = [0]
        print ievent
        print players
        print earnings
        
        Earnings.set_earnings(ievent, players, earnings, currency, placements)
        print "yay!"

def add_earnings_go4sc2_1():
    eventid = 11351
    event = Event.objects.get(id=eventid)
    winners = {'#3':['Mardow'],'#5':['White-Ra'],'#7':['TLO'],'#9':['DeMusliM'],'#11':['TLO'],'#13':['Brat_OK'],'#15':['HuK'],'#19':['MorroW'],'#21':['Tarson'],'#23':['Strelok']}
    prize = 100
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
                print player
                print winners[ievent.name][0]
                print ievent
        player = player[0]
        
        players = [player]
        earnings = [prize]
        placements = [0]
        print ievent
        print players
        print earnings
        
        Earnings.set_earnings(ievent, players, earnings, currency, placements)
        print "yay!"

def add_earnings_go4sc2_2():
    eventid = 11351
    event = Event.objects.get(id=eventid)
    winners = {'#25':['NaNiwa'],'#27':['White-Ra'],'#29':['DIMAGA'],'#31':['Naama'],'#33':['NaNiwa'],'#35':['MaNa'],'#37':['MaNa'],'#39':['Tarson'],'#41':['Socke'],'#43':['Naama'],'#45':['Brat_OK'],'#47':['GoOdy'],'#49':['DarKFoRcE'],'#51':['SjoW'],'#53':['cloud',227],'#55':['Tarson'],'#57':['SjoW'],'#59':['Brat_OK'],'#60':['Kas'],'#62':['Krolu'],'#64':['Control'],'#66':['Adelscott'],'#68':['NaNiwa'],'#69':['Satiini'],'#71':['Strelok'],'#73':['GoOdy'],'#75':['DIMAGA'],'#77':['SjoW'],'#79':['MorroW'],'#81':['cloud',227],'#83':['DIMAGA'],'#85':['Kas'],'#88':['GoOdy'],'#90':['Kas'],'#92':['Stephano'],'#94':['DarKFoRcE'],'#96':['Stephano'],'#98':['Stephano'],'#100':['Happy',95],'#103':['LaLuSh'],'#105':['Strelok'],'#107':['LoWeLy'],'#109':['DeathAngel'],'#112':['Adelscott'],'#114':['sLivko'],'#116':['Happy',95],'#121':['Stephano'],'#123':['GoOdy'],'#125':['LaLuSh'],'#129':['DarKFoRcE'],'#132':['MaNa'],'#134':['MaNa'],'#136':['Eeel'],'#138':['VortiX'],'#140':['Beastyqt'],'#142':['ReaL'],'#144':['Kas'],'#146':['Beastyqt'],'#148':['Nerchio'],'#150':['DarkHydra'],'#152':['Beastyqt'],'#154':['Aristeo'],'#157':['Tefel'],'#159':['MaNa'],'#163':['Aristeo'],'#165':['SjoW'],'#167':['Beastyqt'],'#169':['DBS'],'#171':['LoWeLy'],'#173':['titan',60],'#176':['Nerchio'],'#178':['Nerchio'],'#180':['LiveZerg'],'#182':['titan',60],'#184':['LiveZerg'],'#186':['Nerchio'],'#189':['Tefel'],'#191':['BsK'],'#194':['HyuN'],'#196':['DIMAGA'],'#198':['titan',60],'#203':['sYz'],'#205':['HyuN'],'#207':['Nerchio'],'#211':['HyuN'],'#213':['MaNa'],'#215':['Bly'],'#217':['Revival'],'#219':['LiveZerg'],'#222':['HyuN'],'#224':['HyuN'],'#226':['Nerchio'],'#228':['HyuN'],'#230':['Nerchio'],'#232':['Nerchio'],'#234':['HyuN'],'#236':['Nerchio'],'#238':['ShoWTimE',2170],'#240':['Romson'],'#241':['Snute'],'#243':['Nerchio'],'#246':['Turuk'],'#248':['Nimitz'],'#250':['titan',60],'#252':['Snute'],'#254':['Delphi'],'#255':['Bly'],'#257':['Harstem'],'#259':['Giantt'],'#261':['Zazu']}
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
                print player
                print winners[ievent.name][0]
                print ievent
        player = player[0]
        
        players = [player]
        earnings = [prize]
        placements = [0]
        print ievent
        print players
        print earnings
        
        Earnings.set_earnings(ievent, players, earnings, currency, placements)
        print "yay!"