# {{{ Imports
from tastypie.api import Api

from django.conf.urls import (
    patterns,
    include,
    url,
)

from aligulac import settings

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

handler404 = 'aligulac.views.h404'
handler500 = 'aligulac.views.h500'

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

urlpatterns = patterns('',
    url(r'^$', 'aligulac.views.home'),

    url(r'^i18n/', include('django.conf.urls.i18n')),
    url(r'^language/', 'aligulac.views.language'),

    url(r'^periods/$', 'ratings.ranking_views.periods'),
    url(r'^periods/(?P<period_id>\d+)/$', 'ratings.ranking_views.period'),
    url(r'^periods/latest/$', 'ratings.ranking_views.period'),

    url(r'^earnings/$', 'ratings.ranking_views.earnings'),

    url(r'^players/(?P<player_id>\d+)(-[^ /]*)?/$', 'ratings.player_views.player'),
    url(r'^players/(?P<player_id>\d+)(-[^ /]*)?/period/(?P<period_id>\d+)/$',
        'ratings.player_views.adjustment'),
    url(r'^players/(?P<player_id>\d+)(-[^ /]*)?/results/$', 'ratings.player_views.results'),
    url(r'^players/(?P<player_id>\d+)(-[^ /]*)?/historical/$', 'ratings.player_views.historical'),
    url(r'^players/(?P<player_id>\d+)(-[^ /]*)?/earnings/$', 'ratings.player_views.earnings'),

    url(r'^teams/$', 'ratings.team_views.teams'),
    url(r'^teams/(?P<team_id>\d+)(-[^ /]*)?/$', 'ratings.team_views.team'),
    url(r'^transfers/$', 'ratings.team_views.transfers'),

    url(r'^results/$', 'ratings.results_views.results'),
    url(r'^results/events/$', 'ratings.results_views.events'),
    url(r'^results/events/(?P<event_id>\d+)(-[^ /]*)?/$', 'ratings.results_views.events'),
    url(r'^results/search/$', 'ratings.results_views.search'),

    url(r'^records/race/$', 'ratings.records_views.race'),
    url(r'^records/history/$', 'ratings.records_views.history'),
    url(r'^records/hof/$', 'ratings.records_views.hof'),

    url(r'^faq/$', 'faq.views.faq'),
    url(r'^blog/$', 'blog.views.blog'),
    url(r'^db/$', 'aligulac.views.db'),
    url(r'^search/$', 'aligulac.views.search'),
    url(r'^search/json/$', 'aligulac.views.auto_complete_search'),
    url(r'^m/', include('miniURL.urls')),

    url(r'^about/faq/$', 'faq.views.faq'),
    url(r'^about/blog/$', 'blog.views.blog'),
    url(r'^about/db/$', 'aligulac.views.db'),
    url(r'^about/api/$', 'aligulac.views.api'),

    url(r'^inference/$', 'ratings.inference_views.predict'),
    url(r'^inference/match/$', 'ratings.inference_views.match'),
    url(r'^inference/dual/$', 'ratings.inference_views.dual'),
    url(r'^inference/sebracket/$', 'ratings.inference_views.sebracket'),
    url(r'^inference/rrgroup/$', 'ratings.inference_views.rrgroup'),
    url(r'^inference/proleague/$', 'ratings.inference_views.proleague'),

    url(r'^reports/$', 'ratings.reports_views.balance'),
    url(r'^reports/balance/$', 'ratings.reports_views.balance'),

    url(r'^add/$', 'ratings.staff_views.add_matches'),
    url(r'^add/review/$', 'ratings.staff_views.review_matches'),
    url(r'^add/events/$', 'ratings.staff_views.events'),
    url(r'^add/events/children/(?P<id>\d+)/$', 'ratings.staff_views.event_children'),
    url(r'^add/open_events/$', 'ratings.staff_views.open_events'),
    url(r'^add/misc/$', 'ratings.staff_views.misc'),

    url(r'^login/$', 'aligulac.views.login_view'),
    url(r'^logout/$', 'aligulac.views.logout_view'),
    url(r'^changepwd/$', 'aligulac.views.changepwd'),

    url(r'^misc/$', 'ratings.misc_views.home'),
    url(r'^misc/days/$', 'ratings.misc_views.clocks'),
    url(r'^misc/balance/$', 'ratings.reports_views.balance'),

    url(r'^404/$', 'aligulac.views.h404'),
    url(r'^500/$', 'aligulac.views.h500'),

    url(r'^admin/', include(admin.site.urls)),

    # Tastypie
    url(r'^api/', include(beta_api.urls)),
    url(r'^api/', include(v1_api.urls)),
)

# {{{ If in debug mode (i.e. with the django server), we must serve CSS and JS ourselves.
if settings.DEBUG:
    urlpatterns += patterns('',
        url(r'^css/(?P<path>.*)$', 'django.views.static.serve',
            {'document_root': settings.PROJECT_PATH + '../resources/css'}),
        url(r'^js/(?P<path>.*)$', 'django.views.static.serve',
            {'document_root': settings.PROJECT_PATH + '../resources/js'}),
        url(r'^img/(?P<path>.*)$', 'django.views.static.serve',
            {'document_root': settings.PROJECT_PATH + '../resources/img'})
    )
# }}}
