# {{{ Imports
from tastypie import fields
from tastypie.authentication import Authentication
from tastypie.resources import ModelResource, ALL, ALL_WITH_RELATIONS

from django.db.models import F

from aligulac.settings import DEBUG

from ratings.models import (
    APIKey,
    Earnings,
    Event,
    Group,
    GroupMembership,
    Match,
    Period,
    Player,
    Rating,
)
from ratings.tools import (
    filter_active,
    total_ratings,
)
# }}}

# {{{ Authenticator
class APIKeyAuthentication(Authentication):
    def is_authenticated(self, request, **kwargs):
        if DEBUG:
            return True

        try:
            key = request.POST['apikey'] if request.method == 'POST' else request.GET['apikey']
        except:
            return False

        modified = APIKey.objects.filter(key=key).update(requests=F('requests')+1)
        return modified == 1
# }}}

# {{{ PeriodResource
class PeriodResource(ModelResource):
    class Meta:
        queryset = Period.objects.filter(computed=True)
        allowed_methods = ['get', 'post']
        resource_name = 'period'
        authentication = APIKeyAuthentication()
        excludes = ['computed']
        filtering = {
            key: ALL
            for key in [
                'id',
                'start',
                'end',
                'needs_recompute',
                'num_retplayers',
                'num_games',
                'dom_p',
                'dom_t',
                'dom_z',
        ]}
        ordering = [
            'id',
            'start',
            'end',
            'num_retplayers',
            'num_newplayers',
            'num_games',
            'dom_p',
            'dom_t',
            'dom_z',
        ]
# }}}

# {{{ SmallRatingResource (for inline)
class SmallRatingResource(ModelResource):
    class Meta:
        queryset = total_ratings(Rating.objects.all())
        allowed_methods = ['get', 'post']
        resource_name = 'rating'
        authentication = APIKeyAuthentication()
        fields = [
            'rating',
            'rating_vp',
            'rating_vt',
            'rating_vz',
            'dev',
            'dev_vp',
            'dev_vt',
            'dev_vz',
            'decay',
        ]

    def dehydrate(self, bundle):
        bundle.data['tot_vp'] = bundle.data['rating'] + bundle.data['rating_vp']
        bundle.data['tot_vt'] = bundle.data['rating'] + bundle.data['rating_vt']
        bundle.data['tot_vz'] = bundle.data['rating'] + bundle.data['rating_vz']
        return bundle
# }}}

# {{{ RatingResource
class RatingResource(ModelResource):
    class Meta:
        queryset = total_ratings(Rating.objects.all())
        allowed_methods = ['get', 'post']
        resource_name = 'rating'
        authentication = APIKeyAuthentication()
        filtering = {
            'period': ALL_WITH_RELATIONS,
            'player': ALL_WITH_RELATIONS,
            'prev': ALL_WITH_RELATIONS,
            'decay': ALL,
            'domination': ALL,
            'rating':     ALL, 'rating_vp':     ALL, 'rating_vt':     ALL, 'rating_vz':     ALL,
            'dev':        ALL, 'dev_vp':        ALL, 'dev_vt':        ALL, 'dev_vz':        ALL,
            'bf_rating':  ALL, 'bf_rating_vp':  ALL, 'bf_rating_vt':  ALL, 'bf_rating_vz':  ALL,
            'bf_dev':     ALL, 'bf_dev_vp':     ALL, 'bf_dev_vt':     ALL, 'bf_dev_vz':     ALL,
            'comp_rat':   ALL, 'comp_rat_vp':   ALL, 'comp_rat_vt':   ALL, 'comp_rat_vz':   ALL,
            'position':   ALL, 'position_vp':   ALL, 'position_vt':   ALL, 'position_vz':   ALL,
        }
        ordering = [
            'period', 'player', 'prev', 'decay', 'domination',
            'rating',     'rating_vp',     'rating_vt',     'rating_vz',
            'dev',        'dev_vp',        'dev_vt',        'dev_vz',
            'bf_rating',  'bf_rating_vp',  'bf_rating_vt',  'bf_rating_vz',
            'bf_dev',     'bf_dev_vp',     'bf_dev_vt',     'bf_dev_vz',
            'comp_rat',   'comp_rat_vp',   'comp_rat_vt',   'comp_rat_vz',
            'position',   'position_vp',   'position_vt',   'position_vz',
        ]

    def dehydrate(self, bundle):
        bundle.data['tot_vp'] = bundle.data['rating'] + bundle.data['rating_vp']
        bundle.data['tot_vt'] = bundle.data['rating'] + bundle.data['rating_vt']
        bundle.data['tot_vz'] = bundle.data['rating'] + bundle.data['rating_vz']
        return bundle

    period = fields.ForeignKey(PeriodResource, 'period', null=False)
    player = fields.ForeignKey('ratings.api.resources.SmallPlayerResource', 'player', null=False, full=True)
    prev = fields.ForeignKey('self', 'prev', null=True)
# }}}

# {{{ ActiveRatingResource
class ActiveRatingResource(ModelResource):
    class Meta:
        queryset = filter_active(total_ratings(Rating.objects.all()))
        allowed_methods = ['get', 'post']
        resource_name = 'activerating'
        authentication = APIKeyAuthentication()
        filtering = {
            'period': ALL_WITH_RELATIONS,
            'player': ALL_WITH_RELATIONS,
            'prev': ALL_WITH_RELATIONS,
            'decay': ALL,
            'domination': ALL,
            'rating':     ALL, 'rating_vp':     ALL, 'rating_vt':     ALL, 'rating_vz':     ALL,
            'dev':        ALL, 'dev_vp':        ALL, 'dev_vt':        ALL, 'dev_vz':        ALL,
            'bf_rating':  ALL, 'bf_rating_vp':  ALL, 'bf_rating_vt':  ALL, 'bf_rating_vz':  ALL,
            'bf_dev':     ALL, 'bf_dev_vp':     ALL, 'bf_dev_vt':     ALL, 'bf_dev_vz':     ALL,
            'comp_rat':   ALL, 'comp_rat_vp':   ALL, 'comp_rat_vt':   ALL, 'comp_rat_vz':   ALL,
            'position':   ALL, 'position_vp':   ALL, 'position_vt':   ALL, 'position_vz':   ALL,
        }
        ordering = [
            'period', 'player', 'prev', 'decay', 'domination',
            'rating',     'rating_vp',     'rating_vt',     'rating_vz',
            'dev',        'dev_vp',        'dev_vt',        'dev_vz',
            'bf_rating',  'bf_rating_vp',  'bf_rating_vt',  'bf_rating_vz',
            'bf_dev',     'bf_dev_vp',     'bf_dev_vt',     'bf_dev_vz',
            'comp_rat',   'comp_rat_vp',   'comp_rat_vt',   'comp_rat_vz',
            'position',   'position_vp',   'position_vt',   'position_vz',
        ]

    def dehydrate(self, bundle):
        bundle.data['tot_vp'] = bundle.data['rating'] + bundle.data['rating_vp']
        bundle.data['tot_vt'] = bundle.data['rating'] + bundle.data['rating_vt']
        bundle.data['tot_vz'] = bundle.data['rating'] + bundle.data['rating_vz']
        return bundle

    period = fields.ForeignKey(PeriodResource, 'period', null=False)
    player = fields.ForeignKey('ratings.api.resources.SmallPlayerResource', 'player', null=False, full=True)
    prev = fields.ForeignKey('self', 'prev', null=True)
# }}}

# {{{ SmallPlayerResource (for inline)
class SmallPlayerResource(ModelResource):
    class Meta:
        queryset = Player.objects.all()
        allowed_methods = ['get', 'post']
        resource_name = 'player'
        authentication = APIKeyAuthentication()
        fields = [
            'tag',
            'country',
            'race',
        ]
# }}}

# {{{ PlayerResource
class PlayerResource(ModelResource):
    class Meta:
        queryset = Player.objects.all().prefetch_related('alias_set')
        allowed_methods = ['get', 'post']
        resource_name = 'player'
        authentication = APIKeyAuthentication()
        filtering = {
            'tag':             ALL,
            'name':            ALL,
            'birthday':        ALL,
            'mcnum':           ALL,
            'tlpd_id':         ALL,
            'tlpd_db':         ALL,
            'lp_name':         ALL,
            'sc2c_id':         ALL,
            'sc2e_id':         ALL,
            'country':         ALL,
            'race':            ALL,
            'dom_val':         ALL,
            'current_rating':  ALL_WITH_RELATIONS,
            'dom_start':       ALL_WITH_RELATIONS,
            'dom_end':         ALL_WITH_RELATIONS,
        }
        ordering = [
            'tag',
            'name',
            'birthday',
            'mcnum',
            'tlpd_id',
            'tlpd_db',
            'lp_name',
            'sc2c_id',
            'sc2e_id',
            'country',
            'race',
            'dom_val',
            'current_rating',
            'dom_start',
            'dom_end',
        ]

    def dehydrate_aliases(self, bundle):
        return [a.name for a in bundle.obj.alias_set.all()]

    dom_start = fields.ForeignKey(PeriodResource, 'dom_start', blank=True, null=True)
    dom_end = fields.ForeignKey(PeriodResource, 'dom_end', blank=True, null=True)
    current_rating = fields.ForeignKey(SmallRatingResource, 'current_rating', blank=True, null=True, full=True)

    current_teams = fields.ToManyField(
        'ratings.api.resources.SmallGroupMembershipResourceFromPlayer', null=True, full=True,
        attribute=lambda b: b.obj.groupmembership_set.filter(current=True, group__is_team=True),
        help_text='Current team(s)'
    )
    past_teams = fields.ToManyField(
        'ratings.api.resources.SmallGroupMembershipResourceFromPlayer', null=True, full=True,
        attribute=lambda b: b.obj.groupmembership_set.filter(current=False, group__is_team=True),
        help_text='Past teams'
    )

    aliases = fields.ListField(null=True, help_text='Aliases')
# }}}

# {{{ SmallEventResource (for inline)
class SmallEventResource(ModelResource):
    class Meta:
        queryset = Event.objects.all()
        allowed_methods = ['get', 'post']
        resource_name = 'event'
        authentication = APIKeyAuthentication()
        fields = ['fullname']
# }}}

# {{{ EventResource
class EventResource(ModelResource):
    class Meta:
        queryset = Event.objects.all()
        allowed_methods = ['get', 'post']
        resource_name = 'event'
        authentication = APIKeyAuthentication()
        excludes = ['lft', 'rgt', 'closed', 'big', 'noprint']
        filtering = {
            key: ALL
            for key in [
                'name',
                'fullname',
                'parent',
                'homepage',
                'lp_name',
                'tlpd_id',
                'tlpd_db',
                'tl_thread',
                'prizepool',
                'earliest',
                'latest',
                'category',
                'type',
        ]}

    parent = fields.ForeignKey('self', 'parent', null=True)
    children = fields.ToManyField(
        'self', attribute=lambda b: Event.objects.filter(uplink__parent=b.obj, uplink__distance=1),
        null=True, help_text='Direct children events'
    )
    earnings = fields.ToManyField(
        'ratings.api.resources.EarningResource', attribute = lambda b: b.obj.earnings_set,
        null=True, help_text='Prizes awarded'
    )
# }}}

# {{{ SmallPlayerResource (for inline)
class SmallPlayerResource(ModelResource):
    class Meta:
        queryset = Player.objects.all()
        allowed_methods = ['get', 'post']
        resource_name = 'player'
        authentication = APIKeyAuthentication()
        fields = [
            'tag',
            'country',
            'race',
        ]
# }}}

# {{{ MatchResource
class MatchResource(ModelResource):
    class Meta:
        queryset = Match.objects.all()
        allowed_methods = ['get', 'post']
        resource_name = 'match'
        authentication = APIKeyAuthentication()
        filtering = {
            'period': ALL_WITH_RELATIONS,
            'eventobj': ALL_WITH_RELATIONS,
            'rta': ALL_WITH_RELATIONS, 'rtb': ALL_WITH_RELATIONS,
            'pla': ALL_WITH_RELATIONS, 'plb': ALL_WITH_RELATIONS,
            'sca': ALL, 'scb': ALL, 'rca': ALL, 'rcb': ALL,
            'date': ALL,
            'treated': ALL,
            'event': ALL,
            'game': ALL,
            'offline': ALL,
        }
        ordering = [
            'period', 'eventobj', 'rta', 'rtb', 'pla', 'plb', 'sca', 'scb', 'rca', 'rcb',
            'date', 'treated', 'event', 'game', 'offline'
        ]

    pla = fields.ForeignKey(SmallPlayerResource, 'pla', null=False, full=True)
    plb = fields.ForeignKey(SmallPlayerResource, 'plb', null=False, full=True)
    rta = fields.ForeignKey(SmallRatingResource, 'rta', null=True, full=True)
    rtb = fields.ForeignKey(SmallRatingResource, 'rtb', null=True, full=True)
    eventobj = fields.ForeignKey(SmallEventResource, 'eventobj', null=True, full=True)
# }}}

# {{{ EarningResource
class EarningResource(ModelResource):
    class Meta:
        queryset = Earnings.objects.all()
        allowed_methods = ['get', 'post']
        resource_name = 'earning'
        authentication = APIKeyAuthentication()
        filtering = {
            'event':         ALL_WITH_RELATIONS,
            'player':        ALL_WITH_RELATIONS,
            'earnings':      ALL,
            'origearnings':  ALL,
            'currency':      ALL,
            'placement':     ALL,
        }
        ordering = ['event', 'player', 'earnings', 'origearnings', 'currency', 'placement']

    event = fields.ForeignKey(SmallEventResource, 'event', null=False, full=True)
    player = fields.ForeignKey(SmallPlayerResource, 'player', null=False, full=True)
# }}}

# {{{ SmallGroupMembershipResourceFromPlayer
class SmallGroupMembershipResourceFromPlayer(ModelResource):
    class Meta:
        queryset = GroupMembership.objects.all()
        allowed_methods = ['get', 'post']
        resource_name = 'groupmembership'
        authentication = APIKeyAuthentication()
        excludes = ['current', 'id']

    team = fields.ForeignKey('ratings.api.resources.SmallTeamResource', 'group', full=True)
# }}}

# {{{ SmallGroupMembershipResourceFromGroup
class SmallGroupMembershipResourceFromGroup(ModelResource):
    class Meta:
        queryset = GroupMembership.objects.all()
        allowed_methods = ['get', 'post']
        resource_name = 'groupmembership'
        authentication = APIKeyAuthentication()
        excludes = ['current', 'playing', 'id']

    player = fields.ForeignKey(SmallPlayerResource, 'player', full=True)
# }}}

# {{{ SmallTeamResource
class SmallTeamResource(ModelResource):
    class Meta:
        queryset = Group.objects.filter(is_team=True)
        allowed_methods = ['get', 'post']
        resource_name = 'team'
        authentication = APIKeyAuthentication()
        fields = ['name', 'shortname']
# }}}

# {{{ TeamResource
class TeamResource(ModelResource):
    class Meta:
        queryset = Group.objects.filter(is_team=True).prefetch_related('alias_set')
        allowed_methods = ['get', 'post']
        resource_name = 'team'
        authentication = APIKeyAuthentication()
        excludes = ['is_team', 'is_manual']
        filtering = {
            key: ALL
            for key in [
                'name',
                'shortname',
                'scoreak',
                'scorepl',
                'meanrating',
                'founded',
                'disbanded',
                'active',
                'homepage',
                'lp_name',
        ]}
        ordering = [
            'name',
            'shortname',
            'scoreak',
            'scorepl',
            'meanrating',
            'founded',
            'disbanded',
            'active',
            'homepage',
            'lp_name',
        ]

    def dehydrate_aliases(self, bundle):
        return [a.name for a in bundle.obj.alias_set.all()]

    current_players = fields.ToManyField(
        SmallGroupMembershipResourceFromGroup, null=True, full=True,
        attribute=lambda b: b.obj.groupmembership_set.filter(current=True, playing=True),
        help_text='Currently affiliated players'
    )
    current_nonplayers = fields.ToManyField(
        SmallGroupMembershipResourceFromGroup, null=True, full=True,
        attribute=lambda b: b.obj.groupmembership_set.filter(current=True, playing=False),
        help_text='Currently affiliated non-players'
    )
    past_players = fields.ToManyField(
        SmallGroupMembershipResourceFromGroup, null=True, full=True,
        attribute=lambda b: b.obj.groupmembership_set.filter(current=False),
        help_text='Past players'
    )

    aliases = fields.ListField(null=True, help_text='Aliases')
# }}}
