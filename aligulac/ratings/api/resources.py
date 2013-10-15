from tastypie import fields
from tastypie.resources import ModelResource, ALL, ALL_WITH_RELATIONS

from ratings.models import (
    Period,
    Player,
)


class PeriodResource(ModelResource):
    class Meta:
        queryset = Period.objects.all()
        allowed_methods = ['get', 'post']
        resource_name = 'period'

class PlayerResource(ModelResource):
    class Meta:
        queryset = Player.objects.all()
        allowed_methods = ['get', 'post']
        resource_name = 'player'
        filtering = {
            'tag': ALL,
        }

    dom_start = fields.ForeignKey(PeriodResource, 'dom_start', blank=True, null=True)
    dom_end = fields.ForeignKey(PeriodResource, 'dom_end', blank=True, null=True)
