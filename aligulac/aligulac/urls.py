# {{{ Imports
from os.path import normpath, dirname, join

from tastypie.api import Api

from django.urls import path, re_path, include
from django.conf.urls import url
import django.views.static

import aligulac.views
import ratings.team_views
import ratings.ranking_views
import ratings.player_views
import ratings.results_views
import ratings.records_views
import ratings.reports_views
import ratings.staff_views
import ratings.misc_views
import faq.views
import blog.views
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

urlpatterns = [
    url(r'^$', aligulac.views.home),

    path('i18n/', include('django.conf.urls.i18n')),
    path('language/', aligulac.views.language),

    path('periods/', ratings.ranking_views.periods),
    path('periods/<int:period_id>/', ratings.ranking_views.period),
    path('periods/latest/', ratings.ranking_views.period),

    path('earnings/', ratings.ranking_views.earnings),

    re_path(r'players/(?P<player_id>\d+)(-[^ /]*)?/$', ratings.player_views.player),
    re_path(r'players/(?P<player_id>\d+)(-[^ /]*)?/period/(?P<period_id>\d+)/$', ratings.player_views.adjustment),
    re_path(r'players/(?P<player_id>\d+)(-[^ /]*)?/results/$', ratings.player_views.results),
    re_path(r'players/(?P<player_id>\d+)(-[^ /]*)?/historical/$', ratings.player_views.historical),
    re_path(r'players/(?P<player_id>\d+)(-[^ /]*)?/earnings/$', ratings.player_views.earnings),

    path('teams/', ratings.team_views.teams),
    re_path(r'teams/(?P<team_id>\d+)(-[^ /]*)/$', ratings.team_views.team),
    path('transfers/', ratings.team_views.transfers),

    path('results/', ratings.results_views.results),
    path('results/events/', ratings.results_views.events),
    re_path(r'results/events/(?P<event_id>\d+)(-[^ /]*)?/$', ratings.results_views.events),
    path('results/search/', ratings.results_views.search),

    path('records/race/', ratings.records_views.race),
    path('records/history/', ratings.records_views.history),
    path('records/hof/', ratings.records_views.hof),

    path('faq/', faq.views.faq),
    path('blog/', blog.views.blog),
    path('db/', aligulac.views.db),
    path('search/', aligulac.views.search),
    path('search/json/', aligulac.views.auto_complete_search),
    path('m/', include('miniURL.urls')),

    path('about/faq/', faq.views.faq),
    path('about/blog/', blog.views.blog),
    path('about/db/', aligulac.views.db),
    path('about/api/', aligulac.views.api),

    path('inference/', ratings.inference_views.predict),
    path('inference/match/', ratings.inference_views.match),
    path('inference/dual/', ratings.inference_views.dual),
    path('inference/sebracket/', ratings.inference_views.sebracket),
    path('inference/rrgroup/', ratings.inference_views.rrgroup),
    path('inference/proleague/', ratings.inference_views.proleague),

    path('reports/', ratings.reports_views.balance),
    path('reports/balance/', ratings.reports_views.balance),

    path('add/', ratings.staff_views.add_matches),
    path('add/review/', ratings.staff_views.review_matches),
    path('add/events/', ratings.staff_views.events),
    path('add/events/children/<int:id>/', ratings.staff_views.event_children),
    path('add/open_events/', ratings.staff_views.open_events),
    path('add/player_info/<slug:choice>/', ratings.staff_views.player_info),
    path('add/player_info_lp/', ratings.staff_views.player_info_lp),
    path('add/misc/', ratings.staff_views.misc),

    path('login/', aligulac.views.login_view),
    path('logout/', aligulac.views.logout_view),
    path('changepwd/', aligulac.views.changepwd),

    path('misc/', ratings.misc_views.home),
    path('misc/days/', ratings.misc_views.clocks),
    path('misc/balance/', ratings.reports_views.balance),
    path('misc/compare/', ratings.misc_views.compare_search),
    re_path('misc/compare/(?P<players>\d+(-[^ /,]*)?(,\d+(-[^ /,]*)?)*)/$', ratings.misc_views.compare),

    path('404/', aligulac.views.h404, kwargs={'exception': None}),
    path('500/', aligulac.views.h500),

    path('admin/', admin.site.urls),

    # Tastypie
    path('api/', include(beta_api.urls)),
    path('api/', include(v1_api.urls)),
]

# {{{ If in debug mode (i.e. with the django server), we must serve CSS and JS ourselves.
if settings.DEBUG:
    resources = join(dirname(normpath(settings.PROJECT_PATH)), 'resources')
    urlpatterns += [
        re_path('fonts/(?P<path>.*)$', django.views.static.serve, {'document_root': join(resources, 'fonts')}),
        re_path('css/(?P<path>.*)$', django.views.static.serve, {'document_root': join(resources, 'css')}),
        re_path('js/(?P<path>.*)$', django.views.static.serve, {'document_root': join(resources, 'js')}),
        re_path('img/(?P<path>.*)$', django.views.static.serve, {'document_root': join(resources, 'img')})
    ]
# }}}
