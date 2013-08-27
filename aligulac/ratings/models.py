from django.db import models
from countries import transformations, data

# List of countries
# This is used in a couple of models, although it adds a bit of overhead, it would be better to do this
# statically in the country module.
countries = [(code, transformations.cc_to_cn(code)) for code in data.ccn_to_cca2.values()]
countries.sort(key=lambda a: a[1])


# {{{ Periods
class Period(models.Model):
    class Meta:
        db_table = 'period'

    start = models.DateField('Start date', null=False)
    end = models.DateField('End date', null=False)
    computed = models.BooleanField('Computed', null=False, default=False)
    needs_recompute = models.BooleanField('Requires recomputation', null=False, default=False)
    num_retplayers = models.IntegerField('# returning players', default=0)
    num_newplayers = models.IntegerField('# new players', default=0)
    num_games = models.IntegerField('# games', default=0)
    dom_p = models.FloatField('Protoss OP value')
    dom_t = models.FloatField('Terran OP value')
    dom_z = models.FloatField('Zerg OP value')

    # {{{ String representation
    def __unicode__(self):
        return 'Period #' + str(self.id) + ': ' + str(self.start) + ' to ' + str(self.end)
    # }}}

    # {{{ is_preview: Checks whether this period is still a preview
    def is_preview(self):
        return self.end >= datetime.date.today()
    # }}}
# }}}


# {{{ Events
class Event(models.Model):
    class Meta:
        db_table = 'event'

    name = models.CharField('Name', max_length=100)
    parent = models.ForeignKey('Event', null=True, blank=True)
    lft = models.IntegerField('Left')
    rgt = models.IntegerField('Right')
    closed = models.BooleanField('Closed', default=False)
    big = models.BooleanField('Big', default=False)
    noprint = models.BooleanField('No print', default=False)
    fullname = models.CharField('Full name', max_length=500, default='')
    homepage = models.CharField('Homepage', blank=True, null=True, max_length=200)
    lp_name = models.CharField('Liquipedia title', blank=True, null=True, max_length=200)
    
    # tlpd_db contains information in binary form on which TLPD databases to use:
    # 1 for Korean, 10 for International, 100 for HotS, 1000 for Hots beta, 10000 for WoL beta
    # So a value of 5 (00101 in binary) would correspond to a link to the Korean and HotS TLPD.  
    # Use bitwise AND (&) with the flags to check.
    TLPD_DB_KOREAN, TLPD_DB_INTERNATIONAL, TLPD_DB_HOTS, TLPD_DB_HOTSBETA, TLPD_DB_WOLBETA = [1,2,4,8,16]
    tlpd_id = models.IntegerField('TLPD ID', blank=True, null=True)
    tlpd_db = models.IntegerField('TLPD Databases', blank=True, null=True)
    tl_thread = models.IntegerField('Teamliquid.net thread ID', blank=True, null=True)

    prizepool = models.NullBooleanField('Has prize pool', blank=True, null=True)

    earliest = models.DateField('Earliest match', blank=True, null=True)
    latest = models.DateField('Latest match', blank=True, null=True)

    INDIVIDUAL, TEAM, FREQUENT = 'individual', 'team', 'frequent'
    CATEGORIES = [(INDIVIDUAL, 'Individual'), (TEAM, 'Team'), (FREQUENT, 'Frequent')]
    category = models.CharField('Category', max_length=50, null=True, blank=True, choices=CATEGORIES)
    
    CATEGORY, EVENT, ROUND = 'category', 'event', 'round'
    TYPES = [(CATEGORY, 'Category'), (EVENT, 'Event'), (ROUND, 'Round')]
    type = models.CharField(max_length=50, null=True, blank=True, choices=TYPES)

    # {{{ String representation
    def __unicode__(self):
        return self.fullname
    # }}}

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

    def get_event_event(self):
        return Event.objects.filter(lft__lte=self.lft, rgt__gte=self.rgt, type__in=['category','event'], noprint=False)\
                            .order_by('-lft')[0]

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
# }}}


# {{{ Players
class Player(models.Model):
    class Meta:
        ordering = ['tag']
        db_table = 'player'

    tag = models.CharField('In-game name', max_length=30, null=False)
    name = models.CharField('Full name', max_length=100, blank=True, null=True)
    birthday = models.DateField('Birthday', blank=True, null=True)
    mcnum = models.IntegerField('MC number', blank=True, null=True, default=None)

    # tlpd_db contains information in binary form on which TLPD databases to use:
    # 1 for Korean, 10 for International, 100 for HotS, 1000 for Hots beta, 10000 for WoL beta
    # So a value of 5 (00101 in binary) would correspond to a link to the Korean and HotS TLPD.  
    # Use bitwise AND (&) with the flags to check.
    [TLPD_DB_KOREAN, TLPD_DB_INTERNATIONAL, TLPD_DB_HOTS, TLPD_DB_HOTSBETA, TLPD_DB_WOLBETA] = [1,2,4,8,16]
    tlpd_id = models.IntegerField('TLPD ID', blank=True, null=True)
    tlpd_db = models.IntegerField('TLPD Databases', blank=True, null=True)

    lp_name = models.CharField('Liquipedia title', blank=True, null=True, max_length=200)
    sc2c_id = models.IntegerField('SC2Charts.net ID', blank=True, null=True)
    sc2e_id = models.IntegerField('SC2Earnings.com ID', blank=True, null=True)

    country = models.CharField('Country', max_length=2, choices=countries, blank=True, null=True)

    P, T, Z, R, S = "PTZRS"
    RACES = [(P, 'Protoss'), (T, 'Terran'), (Z, 'Zerg'), (R, 'Random'), (S, 'Switcher')]
    race = models.CharField('Race', max_length=1, choices=RACES, null=False)

    # Domination fields (for use in the hall of fame)
    dom_val = models.FloatField('Domination', blank=True, null=True)
    dom_start = models.ForeignKey(Period, blank=True, null=True, related_name='player_dom_start')
    dom_end   = models.ForeignKey(Period, blank=True, null=True, related_name='player_dom_end')

    # {{{ String representation
    def __unicode__(self):
        if self.country != None and self.country != '':
            return self.tag + ' (' + self.race + ', ' + self.country + ')'
        else:
            return self.tag + ' (' + self.race + ')'
    # }}}
    
    # {{{ Standard setters
    def set_tag(self, tag):
        self.tag = tag
        self.save()
    
    def set_country(self, country):
        self.country = country
        self.save()
    
    def set_name(self, name):
        self.name = None if name == '' else name
        self.save()
    
    def set_birthday(self, birthday):
        self.birthday = None if birthday == '' else birthday
        self.save()

    def set_sc2c_id(self, sc2c_id):
        self.sc2c_id = None if sc2c_id == '' else sc2c_id
        self.save()

    def set_tlpd_id(self, tlpd_id, tlpd_db):
        self.tlpd_id = tlpd_id
        self.save()

    def set_sc2e_id(self, sc2e_id):
        self.sc2e_id = None if sc2e_id == '' else sc2e_id
        self.save()

    def set_lp_name(self, lp_name):
        self.lp_name = None if lp_name == '' else lp_name
        self.save()
    # }}}

    # {{{ Adding and removing TLPD databases
    def add_tlpd_db(self, tlpd_db):
        self.tlpd_db |= tlpd_db
        self.save()

    def remove_tlpd_db(self, tlpd_db):
        self.tlpd_db -= self.tlpd_db & tlpd_db
        self.save()
    # }}}
    
    # {{{ set_aliases: Set aliases
    # Input: An array of string aliases, which are compared to existing aliases.
    # New ones are added, existing superfluous ones are removed.
    def set_aliases(self, aliases):
        if aliases:
            old = []

            for alias in Alias.objects.filter(player=self):
                if alias.name not in aliases:
                    alias.delete()
                else:
                    old.append(alias.name)

            new = [x for x in aliases if x not in old]

            for alias in new:
                Alias.add_player_alias(self, alias)

        else:
            Alias.objects.filter(player=self).delete()
    # }}}

    # {{{ get_tlpd_id: Gets TLPD databases
    # Returns a dictionary of database : id key-value pairs, where the keys are
    # strings (IN, KR, HotS, HotSbeta, WoLbeta), and the values are TLPD IDs.
    def get_tlpd_id(self):
        if self.tlpd_id is None:
            return None

        names = [(self.TLPD_DB_KOREAN,          "KR"),
                 (self.TLPD_DB_INTERNATIONAL,   "IN"),
                 (self.TLPD_DB_HOTS,            "HotS"),
                 (self.TLPD_DB_HOTSBETA,        "HotSbeta"),
                 (self.TLPD_DB_WOLBETA,         "WoLbeta")]

        return dict.fromkeys([n[1] for n in names if self.tlpd_db & n[0]], self.tlpd_id)
    # }}}
# }}}


# {{{ Stories
class Story(models.Model):
    class Meta:
        db_table = 'story'
        verbose_name_plural = 'stories'

    player = models.ForeignKey(Player, null=False)
    text = models.CharField('Text', max_length=200, null=False)
    date = models.DateField('Date', null=False)
    event = models.ForeignKey(Event, null=True)

    # {{{ String representation
    def __unicode__(self):
        return '%s - %s on %s' % (self.player.tag, self.text, str(self.date))
    # }}}
# }}}


# {{{ Groups
class Group(models.Model):
    class Meta:
        db_table = 'group'

    name = models.CharField('Name', max_length=100, null=False)
    shortname = models.CharField('Short name', max_length=25, null=True, blank=True)
    members = models.ManyToManyField(Player, through='GroupMembership')
    scoreak = models.FloatField('AK score', null=False, default=0.0)
    scorepl = models.FloatField('PL score', null=False, default=0.0)
    founded = models.DateField('Date founded', null=True, blank=True)
    disbanded = models.DateField('Date disbanded', null=True, blank=True)
    active = models.BooleanField('Active', null=False, default=True)
    homepage = models.CharField('Homepage', null=True, blank=True, max_length=200)
    lp_name = models.CharField('Liquipedia title', null=True, blank=True, max_length=200) 

    is_team = models.BooleanField('Team', null=False, default=True)
    is_manual = models.BooleanField('Manual entry', null=False, default=True)

    # {{{ String representation
    def __unicode__(self):
        return self.name
    # }}}

    # {{{ Standard setters
    def set_name(self, name):
        self.name = name
        self.save()
    
    def set_shortname(self, shortname):
        self.shortname = None if shortname == '' else shortname
        self.save()

    def set_homepage(self, homepage):
        self.homepage = None if homepage == '' else homepage
        self.save()
    
    def set_lp_name(self, lp_name):
        self.lp_name = None if lp_name == '' else lp_name
        self.save()    
    # }}}
    
    # {{{ set_aliases: Set aliases
    # Input: An array of string aliases, which are compared to existing aliases.
    # New ones are added, existing superfluous ones are removed.
    def set_aliases(self, aliases):
        if aliases:
            old = []

            for alias in Alias.objects.filter(group=self):
                if alias.name not in aliases:
                    alias.delete()
                else:
                    old.append(alias.name)

            new = [x for x in aliases if x not in old]

            for alias in new:
                Alias.add_player_alias(self, alias)

        else:
            Alias.objects.filter(group=self).delete()
    # }}}
# }}}


# {{{ GroupMemberships
class GroupMembership(models.Model):
    class Meta:
        db_table = 'groupmembership'

    player = models.ForeignKey(Player, null=False)
    group = models.ForeignKey(Group, null=False)

    start = models.DateField('Date joined', blank=True, null=True)
    end = models.DateField('Date left', blank=True, null=True)
    current = models.BooleanField('Current', default=True, null=False)
    playing = models.BooleanField('Playing', default=True, null=False)
    
    # {{{ String representation
    def __unicode__(self):
        return 'Player: %s Group: %s (%s - %s)' % (self.player.tag, self.group.name, 
                                                   str(self.start), str(self.end))
    # }}}
# }}}


# {{{ Aliases
class Alias(models.Model):
    class Meta:
        verbose_name_plural = 'alias'
        db_table = 'aliases'

    name = models.CharField('Alias', max_length=100, null=False)
    player = models.ForeignKey(Player, null=True)
    group = models.ForeignKey(Group, null=True)

    # {{{ String representation
    def __unicode__(self):
        return self.name
    # }}}
    
    # {{{ Standard adders
    @staticmethod
    def add_player_alias(player, name):
        new = Alias(player=player, name=name)
        new.save()

    @staticmethod
    def add_team_alias(group, name):
        new = Alias(group=group, name=name)
        new.save()
    # }}}
# }}}
