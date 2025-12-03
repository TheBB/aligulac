# {{{ Imports
from tastypie.api import Api

from django.urls import path, include

from ratings.api.resources import (
    ActiveRatingResource,
    EarningResource,
    EventResource,
    MatchResource,
    PeriodResource,
    PlayerResource,
    RatingResource,
    TeamResource,
    PredictDualResource,
    PredictMatchResource,
    PredictSEBracketResource,
    PredictRRGroupResource,
    PredictPLResource,
)

from django.contrib import admin
admin.autodiscover()
# }}}

beta_api = Api(api_name='beta')
v1_api = Api(api_name='v1')
resources = [
    ActiveRatingResource,
    EarningResource,
    EventResource,
    MatchResource,
    PeriodResource,
    PlayerResource,
    RatingResource,
    TeamResource,
    PredictDualResource,
    PredictMatchResource,
    PredictSEBracketResource,
    PredictRRGroupResource,
    PredictPLResource,
]
for res in resources:
    beta_api.register(res())
    v1_api.register(res())

urlpatterns = [
    # Tastypie
    path('api/', include(beta_api.urls)),
    path('api/', include(v1_api.urls)),
]
