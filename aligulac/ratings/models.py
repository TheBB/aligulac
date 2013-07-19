from django.contrib.auth.models import User
from django.db import models
from django.db.models import Max, F, Q
from django.db.models.signals import pre_delete
from countries import transformations, data

from math import sqrt
import datetime
import currency as curex

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
    
    tlpd_id = models.IntegerField('TLPD ID', blank=True, null=True)
    #tlpd_db contains information in binary form on which TLPD databases to use:
    #1 for korean, 10 for international, 100 for HotS, 1000 for Hots beta, 10000 for WoL beta
    tlpd_db = models.IntegerField('TLPD Databases', blank=True, null=True)
    tl_thread = models.IntegerField('Teamliquid.net thread ID', blank=True, null=True)

    prizepool = models.NullBooleanField(blank=True, null=True)

    earliest = models.DateField(blank=True, null=True)
    latest = models.DateField(blank=True, null=True)

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

    def get_path_print(self):
        return Event.objects.filter(lft__lte=self.lft, rgt__gte=self.rgt).order_by('lft')

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

    def get_parents(self, id=False):
        try:
            if not id:
                return Event.objects.filter(lft__lt=self.lft, rgt__gt=self.rgt).order_by('-lft')
            else:
                return Event.objects.filter(lft__lte=self.lft, rgt__gte=self.rgt).order_by('-lft')
        except:
            return self
    
    def get_children(self, type=['category', 'event', 'round'], id=False):
        if not id:
            return Event.objects.filter(lft__gt=self.lft, rgt__lt=self.rgt,type__in=type).order_by('lft')
        else:
            return Event.objects.filter(lft__gte=self.lft, rgt__lte=self.rgt,type__in=type).order_by('lft')

    def has_children(self):
        return self.rgt > self.lft + 1
    
    def get_root(self):
        return Event.objects.filter(lft__lte=self.lft, rgt__gte=self.rgt).order_by('lft')[0]
    
    def get_homepage(self):
        id = Event.objects.filter(lft__lte=self.lft, rgt__gte=self.rgt, homepage__isnull=False).order_by('-lft')
        
        if id:
            return id[0].homepage
        else:
            return None

    def get_lp_name(self):
        id = Event.objects.filter(lft__lte=self.lft, rgt__gte=self.rgt, lp_name__isnull=False).order_by('-lft')
        
        if id:
            return id[0].lp_name
        else:
            return None

    #returns a dictionary of TLPD IDs, or None if player has no TLPD link.
    #Dictionary keys: IN, KR, HotS, HotSbeta. Values are either None or the TLPD ID.   
    def get_tlpd_id(self):
        id = Event.objects.filter(lft__lte=self.lft, rgt__gte=self.rgt, tlpd_id__isnull=False).order_by('-lft')
        if id:
            tlpd_ids = {}
            if (self.tlpd_db % 2) == 1:
                tlpd_ids["KR"] = id[0].tlpd_id
            if (self.tlpd_db / 0b10 % 2) == 1:
                tlpd_ids["IN"] = id[0].tlpd_id
            if (self.tlpd_db / 0b100 % 2) == 1:
                tlpd_ids["HotS"] = id[0].tlpd_id
            if (self.tlpd_db / 0b1000 % 2) == 1:
                tlpd_ids["HotSbeta"] = id[0].tlpd_id
            if (self.tlpd_db / 0b10000 % 2) == 1:
                tlpd_ids["WoLbeta"] = id[0].tlpd_id
            return tlpd_ids
        else:
            return None

    def get_tl_thread(self):
        id = Event.objects.filter(lft__lte=self.lft, rgt__gte=self.rgt, tl_thread__isnull=False).order_by('-lft')
        
        if id:
            return id[0].tl_thread
        else:
            return None

    def get_prizepool(self):
        return self.prizepool
    
    def get_earliest(self):
        return self.earliest
    def get_latest(self):
        return self.latest

    #raw SQL query is much faster and/or I don't know how to get the same SQL query as a django query 
    def update_dates(self):
        from django.db import connection
        cursor = connection.cursor()
        try:
            cursor.execute('select date, id from ratings_match where eventobj_id in\
                                        (select id from ratings_event where\
                                        lft >= ' + str(self.lft) + ' and\
                                        rgt <= ' + str(self.rgt) +
                                        ') order by date desc limit 1;')
            self.latest = cursor.fetchone()[0]
            cursor.execute('select date, id from ratings_match where eventobj_id in\
                                        (select id from ratings_event where\
                                        lft >= ' + str(self.lft) + ' and\
                                        rgt <= ' + str(self.rgt) +
                                        ') order by date asc limit 1;')
            self.earliest = cursor.fetchone()[0]
            self.save()
        except:
            self.latest = None
            self.earliest = None
            self.save()
    
    def change_type(self, type):
        self.type = type
        # Set childevents as "round" if type is "event" or "round". 
        if type == 'event' or type == 'round':
            Event.objects.filter(lft__gte=self.lft, lft__lt=self.rgt).update(type='round')
        # Set parent events as "category" if type is "event" or "category". 
        if type == 'event' or type == 'category':
            Event.objects.filter(lft__lt=self.lft, rgt__gt=self.rgt).update(type='category')
        self.save()
    
    def set_prizepool(self, prizepool):
        self.prizepool = prizepool
        self.save()
    
    def set_parent(self, parent):
        self.parent = parent
        self.save()
    
    def set_homepage(self, homepage):
        if homepage == '':
            self.homepage = None
        else:
            self.homepage = homepage
        self.save()
    
    def set_lp_name(self, lp_name):
        if lp_name == '':
            self.lp_name = None
        else:
            self.lp_name = lp_name
        self.save()

    def set_tlpd_id(self, tlpd_id, tlpd_db):
        if tlpd_id == '' or tlpd_db == 0:
            self.tlpd_id = None
            self.tlpd_db = None
        else:
            self.tlpd_id = tlpd_id
            self.tlpd_db = tlpd_db
        self.save()
        
    def set_tl_thread(self, tl_thread):
        if tl_thread == '':
            self.tl_thread = None
        else:
            self.tl_thread = tl_thread
        self.save()
    
    def set_earliest(self, date):
        self.earliest = date
        self.save()

    def set_latest(self, date):
        self.latest = date
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
    
    def delete_earnings(self, ranked=True):
        if ranked:
            Earnings.objects.filter(event=self).exclude(placement__exact=0).delete()
        else:
            Earnings.objects.filter(event=self, placement__exact=0).delete()

    def move_earnings(self, newevent):
        Earnings.objects.filter(event=self).update(event=newevent)
        event.set_prizepool(None)
        newevent.set_prizepool(True)
        newevent.change_type('event')

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

    tlpd_id = models.IntegerField('TLPD ID', blank=True, null=True)
    #tlpd_db contains information in binary form on which TLPD databases to use:
    #1 for korean, 10 for international, 100 for HotS, 1000 for Hots beta, 10000 for WoL beta
    #So a value of 5 (00101 in binary) would correspond to a link to the korean and HotS TLPD.  
    tlpd_db = models.IntegerField('TLPD Databases', blank=True, null=True)
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
    
    def set_tag(self, tag):
        self.tag = tag
        self.save()
    
    def set_country(self, country):
        self.country = country
        self.save()
    
    def set_name(self, name):
        if name == '':
            self.name = None
        else:
            self.name = name
        self.save()
    
    def set_birthday(self, birthday):
        if birthday == '':
            self.birthday = None
        else:
            self.birthday = birthday
        self.save()

    def set_sc2c_id(self, sc2c_id):
        if sc2c_id == '':
            self.sc2c_id = None
        else:
            self.sc2c_id = sc2c_id
        self.save()

    def set_tlpd_id(self, tlpd_id, tlpd_db):
        if tlpd_id == '' or tlpd_db == 0:
            self.tlpd_id = None
            self.tlpd_db = None
        else:
            self.tlpd_id = tlpd_id
            self.tlpd_db = tlpd_db
        self.save()

    def set_sc2e_id(self, sc2e_id):
        if sc2e_id == '':
            self.sc2e_id = None
        else:
            self.sc2e_id = sc2e_id
        self.save()

    def set_lp_name(self, lp_name):
        if lp_name == '':
            self.lp_name = None
        else:
            self.lp_name = lp_name
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

    #returns a dictionary of TLPD IDs, or None if player has no TLPD link.
    #Dictionary keys: IN, KR, HotS, HotSbeta. Values are either None or the TLPD ID.   
    def get_tlpd_id(self):
        if self.tlpd_id is None:
            return None
        else:
            tlpd_ids = {}
            if (self.tlpd_db % 2) == 1:
                tlpd_ids["KR"] = self.tlpd_id
            if (self.tlpd_db / 0b10 % 2) == 1:
                tlpd_ids["IN"] = self.tlpd_id
            if (self.tlpd_db / 0b100 % 2) == 1:
                tlpd_ids["HotS"] = self.tlpd_id
            if (self.tlpd_db / 0b1000 % 2) == 1:
                tlpd_ids["HotSbeta"] = self.tlpd_id
            if (self.tlpd_db / 0b10000 % 2) == 1:
                tlpd_ids["WoLbeta"] = self.tlpd_id
            return tlpd_ids

class Story(models.Model):
    player = models.ForeignKey(Player, null=False)
    text = models.CharField(max_length=200, null=False)
    date = models.DateField(null=False)
    event = models.ForeignKey(Event, null=True)

    class Meta:
        verbose_name_plural = 'stories'

    def __unicode__(self):
        return self.player.tag + ' - ' + self.text + ' on ' + str(self.date)

class Group(models.Model):
    name = models.CharField(max_length=100)
    shortname = models.CharField(max_length=25, null=True, blank=True)
    members = models.ManyToManyField(Player, through='GroupMembership')
    scoreak = models.FloatField(default=0.0)
    scorepl = models.FloatField(default=0.0)
    founded = models.DateField(null=True, blank=True)
    disbanded = models.DateField(null=True, blank=True)
    active = models.BooleanField(default=True)
    homepage = models.CharField('Homepage', blank=True, null=True, max_length=200)
    lp_name = models.CharField('Liquipedia title', blank=True, null=True, max_length=200) 

    is_team = models.BooleanField(default=True)
    is_manual = models.BooleanField(default=True)

    def __unicode__(self):
        return self.name

    def set_name(self, name):
        self.name = name
        self.save()
    
    def set_shortname(self, shortname):
        if shortname == '':
            self.shortname = None
        else:
            self.shortname = shortname
        self.save()
    
    #set alias. Takes an array of arguments, which are compared to existing
    #aliases. New aliases from "aliases" are added, aliases from "oldaliases"
    #that are not in "aliases" are removed.
    def set_aliases(self, aliases):
        if aliases:
            oldaliases = []
            for alias in Alias.objects.filter(group=self):
                oldaliases.append(alias.name)
            newaliases = [x for x in aliases if x not in oldaliases]
            removealiases = [x for x in oldaliases if x not in aliases]
            for alias in newaliases:
                Alias.add_team_alias(self, alias)
            for alias in removealiases:
                Alias.objects.filter(group=self, name=alias).delete()
        #aliases is None, so delete all aliases
        else:
            Alias.objects.filter(group=self).delete()
    
    def set_homepage(self, homepage):
        if homepage == '':
            self.homepage = None
        else:
            self.homepage = homepage
        self.save()
    
    def set_lp_name(self, lp_name):
        if lp_name == '':
            self.lp_name = None
        else:
            self.lp_name = lp_name
        self.save()    

class GroupMembership(models.Model):
    player = models.ForeignKey(Player)
    group = models.ForeignKey(Group)
    start = models.DateField('Date joined', blank=True, null=True)
    end = models.DateField('Date left', blank=True, null=True)
    current = models.BooleanField(default=True, null=False)
    playing = models.BooleanField(default=True, null=False)
	
    def __unicode__(self):
        return 'Player: ' + self.player.tag + ' Group: ' + self.group.name + ' (' + str(self.start) + ' - ' + str(self.end) + ')'

class Alias(models.Model):
    name = models.CharField(max_length=100)
    player = models.ForeignKey(Player, null=True)
    group = models.ForeignKey(Group, null=True)

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
            self.orig_pla = self.pla_id
            self.orig_plb = self.plb_id
            self.orig_rca = self.rca
            self.orig_rcb = self.rcb
            self.orig_sca = self.sca
            self.orig_scb = self.scb
            self.orig_date = self.date
            self.orig_period = self.period_id
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
        return self.orig_pla != self.pla_id or self.orig_plb != self.plb_id or\
               self.orig_rca != self.rca or self.orig_rcb != self.rcb or\
               self.orig_sca != self.sca or self.orig_scb != self.scb

    def changed_date(self):
        return self.orig_date != self.date

    def changed_period(self):
        return self.orig_period != self.period_id

    def __init__(self, *args, **kwargs):
        super(Match, self).__init__(*args, **kwargs)
        self.populate_orig()

    def save(self, force_insert=False, force_update=False, *args, **kwargs):
        update_dates = False
        if self.changed_date():
            self.set_period()
            
            if self.eventobj:
                update_dates = True

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
        
        if update_dates:
            # This is very slow if used for many matches, but that should rarely happen.
            for event in self.eventobj.get_parents(id=True):
                event.update_dates()
    
    def delete(self,  *args, **kwargs):
        eventobj = self.eventobj
        super(Match, self).delete(*args, **kwargs)
        
        if eventobj:
            for event in self.eventobj.get_parents(id=True):
                # This is very slow if used for many matches, but that should rarely happen. 
                event.update_dates()

    def set_period(self):
        pers = Period.objects.filter(start__lte=self.date).filter(end__gte=self.date)
        self.period = pers[0]
    
    def set_date(self, date):
        self.date = date
        self.save()
    
    # Update dates for both old and new event, then set new event object.
    def set_event(self, event):
        oldevent = None
        if self.eventobj:
            oldevent = self.eventobj
        self.eventobj = event
        self.save()
        # This is very slow if used for many matches, but that should rarely happen.
        for event in event.get_parents(id=True):
            event.update_dates()
        if oldevent:
            for event in oldevent.get_parents(id=True):
                event.update_dates()
        
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

class Message(models.Model):
    INFO = 'info'
    WARNING = 'warning'
    ERROR = 'error'
    SUCCESS = 'success'
    TYPES = [(INFO, 'info'), (WARNING, 'warning'), (ERROR, 'error'), (SUCCESS, 'success')]
    type = models.CharField(max_length=10, choices=TYPES)

    title = models.CharField(max_length=100, null=True)
    text = models.TextField()

    player = models.ForeignKey(Player, null=True)
    event = models.ForeignKey(Event, null=True)
    group = models.ForeignKey(Group, null=True)
    match = models.ForeignKey(Match, null=True)

class Earnings(models.Model):
    event = models.ForeignKey(Event)
    player = models.ForeignKey(Player)
    earnings = models.IntegerField(null=True, blank=True)
    origearnings = models.IntegerField()
    currency = models.CharField(max_length=30)
    placement = models.IntegerField()
    
    @staticmethod
    def set_earnings(event, players, origearnings, currency, placements):
        #probably should be more subtle and not delete everything on change
        if Earnings.objects.filter(event=event).exists():
            if placements[0] == -1:
                Earnings.objects.filter(event=event, placement__exact=0).delete()
            else:
                Earnings.objects.filter(event=event).exclude(placement__exact=0).delete()
        if not len(players) == len(origearnings):
            return None
        else:
            for i in range(0,len(players)):
                new = Earnings(event=event, player=players[i], placement=placements[i]+1, origearnings=origearnings[i], currency=currency)
                new.save()
            new.convert_earnings()
        event.set_prizepool(True)
        return new
            
    def convert_earnings(self):
        currency = self.currency
        earningobj = Earnings.objects.filter(event=self.event)
        
        if currency == 'USD':
            for earning in earningobj:
                earning.earnings = earning.origearnings
                earning.save()
        else:
            date = self.event.get_latest()
            exchangerates = curex.ExchangeRates(date)

            if exchangerates:
                for earning in earningobj:        
                    earning.earnings = round(exchangerates.convert(earning.origearnings, currency))
                    earning.save()
   
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

    @property
    def rating_diff(self):
        if self.get_prev() is not None:
            return self.rating - self.get_prev().rating

    @property
    def rating_diff_vp(self):
        if self.get_prev() is not None:
            return self.rating + self.rating_vp - \
                (self.get_prev().rating + self.get_prev().rating_vp)

    @property
    def rating_diff_vt(self):
        if self.get_prev() is not None:
            return self.rating + self.rating_vt - \
                (self.get_prev().rating + self.get_prev().rating_vt)

    @property
    def rating_diff_vz(self):
        if self.get_prev() is not None:
            return self.rating + self.rating_vz - \
                (self.get_prev().rating + self.get_prev().rating_vz)


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

class BalanceEntry(models.Model):
    date = models.DateField()
    pvt_wins = models.IntegerField()
    pvt_losses = models.IntegerField()
    pvz_wins = models.IntegerField()
    pvz_losses = models.IntegerField()
    tvz_wins = models.IntegerField()
    tvz_losses = models.IntegerField()
    p_gains = models.FloatField()
    t_gains = models.FloatField()
    z_gains = models.FloatField()
