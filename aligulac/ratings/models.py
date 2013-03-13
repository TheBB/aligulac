from django.contrib.auth.models import User
from django.db import models
from django.db.models import Max, F, Q
from django.db.models.signals import pre_delete
from countries import transformations, data

from math import sqrt
import datetime

class Period(models.Model):
    start = models.DateField('Start date')
    end = models.DateField('End date')
    computed = models.BooleanField(default=False)
    needs_recompute = models.BooleanField(default=False)
    num_retplayers = models.IntegerField('Returning players')
    num_newplayers = models.IntegerField('New players', default=0)
    num_games = models.IntegerField(default=0)
    dom_p = models.FloatField()
    dom_t = models.FloatField()
    dom_z = models.FloatField()

    def __unicode__(self):
        return 'Period #' + str(self.id) + ': ' + str(self.start) + ' to ' + str(self.end)

    def is_preview(self):
        return self.end >= datetime.date.today()

class Event(models.Model):
    name = models.CharField(max_length=100)
    parent = models.ForeignKey('Event', null=True, blank=True)
    lft = models.IntegerField('Left')
    rgt = models.IntegerField('Right')
    closed = models.BooleanField(default=False)
    big = models.BooleanField(default=False)
    noprint = models.BooleanField(default=False)
    fullname = models.CharField(max_length=500, default='')
    homepage = models.CharField('Homepage', blank=True, null=True, max_length=200)
    lp_name = models.CharField('Liquipedia title', blank=True, null=True, max_length=200)

    INDIVIDUAL = 'individual'
    TEAM = 'team'
    FREQUENT = 'frequent'
    CATEGORIES = [(INDIVIDUAL, 'Individual'), (TEAM, 'Team'), (FREQUENT, 'Frequent')]
    category = models.CharField(max_length=50, null=True, blank=True, choices=CATEGORIES)
    
    CATEGORY = 'category'
    EVENT = 'event'
    ROUND = 'round'
    TYPE = [(CATEGORY, 'Category'), (EVENT, 'Event'), (ROUND, 'Round')]
    type = models.CharField(max_length=50, null=True, blank=True, choices=TYPE)

    def __unicode__(self):
        return self.fullname

    def update_name(self):
        ancestors = Event.objects.filter(lft__lt=self.lft, rgt__gt=self.rgt, noprint=False).order_by('lft')
        q = ' '.join([e.name for e in ancestors])
        if q != '':
            q += ' '
        q += self.name
        self.fullname = q
        self.save()

    def get_path(self):
        return Event.objects.filter(lft__lte=self.lft, rgt__gte=self.rgt, noprint=False).order_by('lft')

    def get_event_fullname(self):
        return Event.objects.filter(lft__lte=self.lft, rgt__gte=self.rgt, type__in=['category','event'])\
                            .order_by('-lft')[0].fullname

    def get_event_path(self):
        return Event.objects.filter(lft__lte=self.lft, rgt__gte=self.rgt, noprint=False,
                                    type__in=['category','event']).order_by('lft')
    
    def get_parent(self, levels=1):
        try:
            return Event.objects.filter(lft__lt=self.lft, rgt__gt=self.rgt).order_by('-lft')[levels-1]
        except:
            return self
    
    def get_children(self):
        return Event.objects.filter(lft__gt=self.lft, rgt__lt=self.rgt).order_by('lft')
    
    def get_homepage(self):
        if self.homepage:
            return self.homepage
        else:
            try:
                return Event.objects.filter(lft__lt=self.lft, rgt__gt=self.rgt, homepage__isnull=False)\
                            .order_by('-lft').values('homepage')[0]['homepage']
            except:
                return None

    def get_lp_name(self):
        if self.lp_name:
            return self.lp_name
        else:
            try:
                return Event.objects.filter(lft__lt=self.lft, rgt__gt=self.rgt, lp_name__isnull=False)\
                            .order_by('-lft').values('lp_name')[0]['lp_name']
            except:
                return None
    
    def get_earliest(self):
        from django.db import connection
        cursor = connection.cursor()
        try:
            cursor.execute('select date, id from ratings_match where eventobj_id in\
                                        (select id from ratings_event where\
                                        lft >= ' + str(event.event.lft) + ' and\
                                        rgt <= ' + str(event.event.rgt) +
                                        ') order by date asc limit 1;')
            return cursor.fetchone()[0]
        except:
            return None

    def get_latest(self):
        from django.db import connection
        cursor = connection.cursor()
        try:
            cursor.execute('select date, id from ratings_match where eventobj_id in\
                                        (select id from ratings_event where\
                                        lft >= ' + str(event.event.lft) + ' and\
                                        rgt <= ' + str(event.event.rgt) +
                                        ') order by date desc limit 1;')
            return cursor.fetchone()[0]
        except:
            return None
    
    def change_type(self, type):
        self.type = type
        if type == 'event' or type == 'round':
            Event.objects.filter(lft__gte=self.lft, lft__lt=self.rgt).update(type='round')
        if type == 'event' or type == 'category':
            Event.objects.filter(lft__lt=self.lft, rgt__gt=self.rgt).update(type='category')
        self.save()
    
    def set_parent(self, parent):
        self.parent = parent
        self.save()
    
    def set_homepage(self, homepage):
        self.homepage = homepage
        self.save()
    
    def set_lp_name(self, lp_name):
        self.lp_name = lp_name
        self.save()

    def add_child(self, name, type, noprint = False, closed = False):
        new = Event(name=name, parent=self)
        if Event.objects.filter(parent=self).exists():
            new.lft = Event.objects.filter(parent=self).aggregate(Max('rgt'))['rgt__max'] + 1
        else:
            new.lft = self.lft + 1
        new.rgt = new.lft + 1
        new.noprint = noprint
        Event.objects.filter(lft__gt=new.rgt-2).update(lft=F('lft')+2)
        Event.objects.filter(rgt__gt=new.rgt-2).update(rgt=F('rgt')+2)
        new.update_name()
        if closed:
            new.close()
        new.save()
        new.change_type(type)
        return new

    @staticmethod
    def add_root(name, type, big = False, noprint = False):
        new = Event(name=name)

        try:
            new.lft = Event.objects.aggregate(Max('rgt'))['rgt__max'] + 1
        except:
            new.lft = 0

        new.rgt = new.lft + 1
        new.big = big
        new.noprint = noprint
        new.update_name()
        new.save()
        new.change_type(type)
        return new

    def close(self):
        self.closed = True
        self.save()
        Event.objects.filter(lft__gt=self.lft, lft__lt=self.rgt).update(closed=True)

    def slide(self, shift):
        self.lft += shift
        self.rgt += shift
        self.save()
        for e in Event.objects.filter(parent=self):
            e.slide(shift)

    def reorganize(self, newleft):
        self.lft = newleft

        children = list(Event.objects.filter(parent=self).order_by('lft'))
        nextleft = newleft + 1
        for c in children:
            nextleft = c.reorganize(nextleft) + 1

        self.rgt = nextleft
        self.save()

        return self.rgt

class Player(models.Model):
    class Meta:
        ordering = ['tag']

    tag = models.CharField('In-game name', max_length=30)
    name = models.CharField('Full name', max_length=100, blank=True, null=True)

    countries = []
    for code in data.ccn_to_cca2.values():
        countries.append((code, transformations.cc_to_cn(code)))
    countries.sort(key=lambda a: a[1])
    country = models.CharField('Country', max_length=2, choices=countries, blank=True, null=False, default='')

    birthday = models.DateField(blank=True, null=True)

    P = 'P'
    T = 'T'
    Z = 'Z'
    R = 'R'
    S = 'S'
    RACES = [(P, 'Protoss'), (T, 'Terran'), (Z, 'Zerg'), (R, 'Random'), (S, 'Switcher')]
    race = models.CharField(max_length=1, choices=RACES)

    tlpd_kr_id = models.IntegerField('TLPD Korean ID', blank=True, null=True)
    tlpd_in_id = models.IntegerField('TLPD International ID', blank=True, null=True)
    lp_name = models.CharField('Liquipedia title', blank=True, null=True, max_length=200)
    sc2c_id = models.IntegerField('SC2Charts.net ID', blank=True, null=True)
    sc2e_id = models.IntegerField('SC2Earnings.com ID', blank=True, null=True)

    dom_val = models.FloatField(blank=True, null=True)
    dom_start = models.ForeignKey(Period, blank=True, null=True, related_name='player_dom_start')
    dom_end = models.ForeignKey(Period, blank=True, null=True, related_name='player_dom_end')

    goodynum = models.IntegerField(blank=True, null=True, default=None)

    def __unicode__(self):
        if self.country != None and self.country != '':
            return self.tag + ' (' + self.race + ', ' + self.country + ')'
        else:
            return self.tag + ' (' + self.race + ')'
    
    def update_external_links(self, sc2c_id, tlpd_kr_id, tlpd_in_id, sc2e_id, lp_name):
        self.sc2c_id = sc2c_id
        self.tlpd_kr_id = tlpd_kr_id
        self.tlpd_in_id = tlpd_in_id
        self.sc2e_id = sc2e_id
        self.lp_name = lp_name
        self.save()
        
    def set_tag(self, tag):
        self.tag = tag
        self.save()
    
    def set_country(self, country):
        self.country = country
        self.save()
    
    def set_name(self, name):
        self.name = name
        self.save()
    
    def set_birthday(self, birthday):
        self.birthday = birthday
        self.save()
    
    #set alias. Takes an array of arguments, which are compared to existing
    #aliases. New aliases from "aliases" are added, aliases from "oldaliases"
    #that are not in "aliases" are removed.
    def set_aliases(self, aliases):
        if aliases:
            oldaliases = []
            for alias in Alias.objects.filter(player=self):
                oldaliases.append(alias.name)
            newaliases = [x for x in aliases if x not in oldaliases]
            removealiases = [x for x in oldaliases if x not in aliases]
            for alias in newaliases:
                Alias.add_player_alias(self, alias)
            for alias in removealiases:
                Alias.objects.filter(player=self, name=alias).delete()
        #aliases is None, so delete all aliases
        else:
            Alias.objects.filter(player=self).delete()

class Team(models.Model):
    name = models.CharField(max_length=100)
    shortname = models.CharField(max_length=25, null=True, blank=True)
    members = models.ManyToManyField(Player, through='TeamMembership')
    scoreak = models.FloatField(default=0.0)
    scorepl = models.FloatField(default=0.0)
    founded = models.DateField(null=True, blank=True)
    disbanded = models.DateField(null=True, blank=True)
    active = models.BooleanField(default=True)
    homepage = models.CharField('Homepage', blank=True, null=True, max_length=200)
    lp_name = models.CharField('Liquipedia title', blank=True, null=True, max_length=200) 

    def __unicode__(self):
        return self.name

    def set_name(self, name):
        self.name = name
        self.save()
    
    def set_shortname(self, shortname):
        self.shortname = shortname
        self.save()
    
    #set alias. Takes an array of arguments, which are compared to existing
    #aliases. New aliases from "aliases" are added, aliases from "oldaliases"
    #that are not in "aliases" are removed.
    def set_aliases(self, aliases):
        if aliases:
            oldaliases = []
            for alias in Alias.objects.filter(team=self):
                oldaliases.append(alias.name)
            newaliases = [x for x in aliases if x not in oldaliases]
            removealiases = [x for x in oldaliases if x not in aliases]
            for alias in newaliases:
                Alias.add_team_alias(self, alias)
            for alias in removealiases:
                Alias.objects.filter(team=self, name=alias).delete()
        #aliases is None, so delete all aliases
        else:
            Alias.objects.filter(team=self).delete()
    
    def set_homepage(self, homepage):
        self.homepage = homepage
        self.save()
    
    def set_lp_name(self, lp_name):
        self.lp_name = lp_name
        self.save()    

class TeamMembership(models.Model):
    player = models.ForeignKey(Player)
    team = models.ForeignKey(Team)
    start = models.DateField('Date joined', blank=True, null=True)
    end = models.DateField('Date left', blank=True, null=True)
    current = models.BooleanField(default=True, null=False)
    playing = models.BooleanField(default=True, null=False)
	
    def __unicode__(self):
        return 'Player: ' + self.player.tag + ' Team: ' + self.team.name + ' (' + str(self.start) + ' - ' + str(self.end) + ')'

class Alias(models.Model):
    name = models.CharField(max_length=100)
    player = models.ForeignKey(Player, null=True)
    team = models.ForeignKey(Team, null=True)

    class Meta:
        verbose_name_plural = 'aliases'

    def __unicode__(self):
        return self.name
    
    @staticmethod
    def add_player_alias(player, name):
        new = Alias(player=player, name=name)
        new.save()

    @staticmethod
    def add_team_alias(team, name):
        new = Alias(team=team, name=name)
        new.save()

class Match(models.Model):
    period = models.ForeignKey(Period)
    date = models.DateField()
    pla = models.ForeignKey(Player, related_name='match_pla', verbose_name='Player A')
    plb = models.ForeignKey(Player, related_name='match_plb', verbose_name='Player B')
    sca = models.SmallIntegerField('Score for player A')
    scb = models.SmallIntegerField('Score for player B')

    P = 'P'
    T = 'T'
    Z = 'Z'
    R = 'R'
    RACES = [(P, 'Protoss'), (T, 'Terran'), (Z, 'Zerg'), (R, 'Random')]
    rca = models.CharField(max_length=1, choices=RACES, null=True, blank=True, verbose_name='Race A')
    rcb = models.CharField(max_length=1, choices=RACES, null=True, blank=True, verbose_name='Race B')

    treated = models.BooleanField(default=False)
    event = models.CharField(max_length=200, default='', blank=True)
    eventobj = models.ForeignKey(Event, null=True, blank=True)
    submitter = models.ForeignKey(User, null=True, blank=True)

    WOL = 'WoL'
    HOTS = 'HotS'
    GAMES = [(WOL, 'Wings of Liberty'), (HOTS, 'Heart of the Swarm')]
    game = models.CharField(max_length=10, default='WoL', blank=False, null=False, choices=GAMES)
    offline = models.BooleanField(default=False, null=False)

    class Meta:
        verbose_name_plural = 'matches'

    def populate_orig(self):
        try:
            self.orig_pla = self.pla
            self.orig_plb = self.plb
            self.orig_rca = self.rca
            self.orig_rcb = self.rcb
            self.orig_sca = self.sca
            self.orig_scb = self.scb
            self.orig_date = self.date
            self.orig_period = self.period
        except:
            self.orig_pla = None
            self.orig_plb = None
            self.orig_rca = None
            self.orig_rcb = None
            self.orig_sca = None
            self.orig_scb = None
            self.orig_date = None
            self.orig_period = None

    def changed_effect(self):
        return self.orig_pla != self.pla or self.orig_plb != self.plb or\
               self.orig_rca != self.rca or self.orig_rcb != self.rcb or\
               self.orig_sca != self.sca or self.orig_scb != self.scb

    def changed_date(self):
        return self.orig_date != self.date

    def changed_period(self):
        return self.orig_period != self.period

    def __init__(self, *args, **kwargs):
        super(Match, self).__init__(*args, **kwargs)
        self.populate_orig()

    def save(self, force_insert=False, force_update=False, *args, **kwargs):
        if self.changed_date():
            self.set_period()

        if self.changed_period() or self.changed_effect():
            try:
                self.orig_period.needs_recompute = True
                self.orig_period.save()
            except:
                pass

            try:
                self.period.needs_recompute = True
                self.period.save()
            except:
                pass
            
            self.treated = False

        super(Match, self).save(force_insert, force_update, *args, **kwargs)
        self.populate_orig()

    def set_period(self):
        pers = Period.objects.filter(start__lte=self.date).filter(end__gte=self.date)
        self.period = pers[0]

    def __unicode__(self):
        return str(self.date) + ' ' + self.pla.tag + ' ' + str(self.sca) +\
                '-' + str(self.scb) + ' ' + self.plb.tag

    def get_winner(self):
        if self.sca > self.scb:
            return self.pla
        elif self.scb > self.sca:
            return self.plb
        else:
            return None

    def get_winner_score(self):
        return max(self.sca, self.scb)
    
    def get_loser_score(self):
        return min(self.sca, self.scb)

    def event_check_fullpath(self):
        return self.event if self.eventobj is None else self.eventobj.fullname

    def event_check_partpath(self):
        return self.event if self.eventobj is None else self.eventobj.get_event_fullname()

#"Earnings" or "Earning"?
class Earnings(models.Model):
    event = models.ForeignKey(Event)
    player = models.ForeignKey(Player)
    earnings = models.IntegerField()
    placement = models.IntegerField()
    
    @staticmethod
    def set_earnings(event, players, earnings, placements):
        #probably should be more subtle and not delete everything on change
        if Earnings.objects.filter(event=event).exists():
            Earnings.objects.filter(event=event).delete()
        if not len(players) == len(earnings):
            return None
        else:
            for i in range(0,len(players)):
                new = Earnings(event=event, player=players[i], placement=placements[i]+1, earnings=earnings[i])
                new.save()
        return new
    
    def __unicode__(self):
        return '#' + str(self.placement) + ' at ' + self.event.fullname + ': ' + self.player.tag + ' Earnings: $' + str(self.earnings)
    
def mark_period(sender, **kwargs):
    obj = kwargs['instance']
    try:
        obj.period.needs_recompute = True
        obj.period.save()
    except:
        pass
pre_delete.connect(mark_period, sender=Match)

class PreMatchGroup(models.Model):
    date = models.DateField()
    event = models.CharField(max_length=200, default='', null=False, blank=True)
    source = models.CharField(max_length=500, default='', null=True, blank=True)
    contact = models.CharField(max_length=200, default='', null=True, blank=True)
    notes = models.TextField(default='', null=True, blank=True)

    WOL = 'WoL'
    HOTS = 'HotS'
    GAMES = [(WOL, 'Wings of Liberty'), (HOTS, 'Heart of the Swarm')]
    game = models.CharField(max_length=10, default='wol', blank=False, null=False, choices=GAMES)
    offline = models.BooleanField(default=False, null=False)

    def __unicode__(self):
        return str(self.date) + ' ' + self.event

class PreMatch(models.Model):
    group = models.ForeignKey(PreMatchGroup, null=False, blank=False)

    pla = models.ForeignKey(Player, related_name='prematch_pla', verbose_name='Player A', null=True, blank=True)
    plb = models.ForeignKey(Player, related_name='prematch_plb', verbose_name='Player B', null=True, blank=True)
    sca = models.SmallIntegerField('Score for player A')
    scb = models.SmallIntegerField('Score for player B')
    date = models.DateField()

    P = 'P'
    T = 'T'
    Z = 'Z'
    R = 'R'
    RACES = [(P, 'Protoss'), (T, 'Terran'), (Z, 'Zerg'), (R, 'Random')]
    rca = models.CharField(max_length=1, choices=RACES, null=False, blank=False, verbose_name='Race A')
    rcb = models.CharField(max_length=1, choices=RACES, null=False, blank=False, verbose_name='Race B')

    pla_string = models.CharField(max_length=200, default='', null=True, blank=True)
    plb_string = models.CharField(max_length=200, default='', null=True, blank=True)

    class Meta:
        verbose_name_plural = 'prematches'

    def __unicode__(self):
        ret = '(' + self.group.event + ') '
        ret += self.pla.tag if self.pla else self.pla_string
        ret += ' ' + str(self.sca) + '-' + str(self.scb) + ' '
        ret += self.plb.tag if self.plb else self.plb_string
        return ret

    def event_check_fullpath(self):
        return self.group.event

    def event_check_partpath(self):
        return self.group.event

class Rating(models.Model):
    period = models.ForeignKey(Period)
    player = models.ForeignKey(Player)

    # Standard rating numbers
    rating = models.FloatField()
    rating_vp = models.FloatField()
    rating_vt = models.FloatField()
    rating_vz = models.FloatField()

    # Standard rating deviations
    dev = models.FloatField()
    dev_vp = models.FloatField()
    dev_vt = models.FloatField()
    dev_vz = models.FloatField()

    # Computed performance ratings
    comp_rat = models.FloatField(null=True, blank=True)
    comp_rat_vp = models.FloatField(null=True, blank=True)
    comp_rat_vt = models.FloatField(null=True, blank=True)
    comp_rat_vz = models.FloatField(null=True, blank=True)

    # Computed performance rating deviations
    comp_dev = models.FloatField(null=True, blank=True)
    comp_dev_vp = models.FloatField(null=True, blank=True)
    comp_dev_vt = models.FloatField(null=True, blank=True)
    comp_dev_vz = models.FloatField(null=True, blank=True)

    # Backwards filtered rating numbers
    bf_rating = models.FloatField(default=0)
    bf_rating_vp = models.FloatField(default=0)
    bf_rating_vt = models.FloatField(default=0)
    bf_rating_vz = models.FloatField(default=0)

    # Backwards filtered rating deviations
    bf_dev = models.FloatField(null=True, blank=True, default=1)
    bf_dev_vp = models.FloatField(null=True, blank=True, default=1)
    bf_dev_vt = models.FloatField(null=True, blank=True, default=1)
    bf_dev_vz = models.FloatField(null=True, blank=True, default=1)

    # Ranks among all players (if player is active)
    position = models.IntegerField()
    position_vp = models.IntegerField()
    position_vt = models.IntegerField()
    position_vz = models.IntegerField()

    decay = models.IntegerField(default=0)
    domination = models.FloatField(null=True, blank=True)

    def get_prev(self):
        try:
            if self.prev:
                return self.prev
        except:
            pass

        try:
            self.prev = Rating.objects.get(period__id=self.period.id-1, player=self.player)
            return self.prev
        except:
            pass
        
        return None

    def get_next(self):
        try:
            return Rating.objects.get(period__id=self.period.id+1, player=self.player)
        except:
            return None

    def ratings(self):
        return [self.rating, self.rating_vp, self.rating_vt, self.rating_vz]

    def devs(self):
        return [self.dev, self.dev_vp, self.dev_vt, self.dev_vz]

    def __unicode__(self):
        return self.player.tag + ' P' + str(self.period.id)

    def get_rating(self, race=None):
        if race == 'P':
            return self.rating_vp
        elif race == 'T':
            return self.rating_vt
        elif race == 'Z':
            return self.rating_vz
        return self.rating

    def get_dev(self, race=None):
        if race == 'P':
            return self.dev_vp
        elif race == 'T':
            return self.dev_vt
        elif race == 'Z':
            return self.dev_vz
        return self.dev

    def get_totalrating(self, race):
        if race in ['P','T','Z']:
            return self.rating + self.get_rating(race)
        else:
            return self.rating

    def get_totaldev(self, race):
        if race in ['P','T','Z']:
            return sqrt(self.get_dev(None)**2 + self.get_dev(race)**2)
        else:
            d = self.get_dev(None)**2
            for r in ['P','T','Z']:
                d += self.get_dev(r)**2/9
            return sqrt(d)

    def set_rating(self, d, write_bf=False):
        self.rating = d['M']
        self.rating_vp = d['P']
        self.rating_vt = d['T']
        self.rating_vz = d['Z']

        if write_bf:
            self.bf_rating = self.rating
            self.bf_rating_vp = self.rating_vp
            self.bf_rating_vt = self.rating_vt
            self.bf_rating_vz = self.rating_vz

    def set_dev(self, d, write_bf=False):
        self.dev = d['M']
        self.dev_vp = d['P']
        self.dev_vt = d['T']
        self.dev_vz = d['Z']

        if write_bf:
            self.bf_dev = self.dev
            self.bf_dev_vp = self.dev_vp
            self.bf_dev_vt = self.dev_vt
            self.bf_dev_vz = self.dev_vz
    
    def set_comp_rating(self, d):
        self.comp_rat = d['M']
        self.comp_rat_vp = d['P']
        self.comp_rat_vt = d['T']
        self.comp_rat_vz = d['Z']

    def set_comp_dev(self, d):
        self.comp_dev = d['M']
        self.comp_dev_vp = d['P']
        self.comp_dev_vt = d['T']
        self.comp_dev_vz = d['Z']
