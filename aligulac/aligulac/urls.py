# {{{ Imports
from django.conf.urls import (
    patterns,
    include,
    url,
)
from aligulac import settings

from django.contrib import admin
admin.autodiscover()
# }}}

handler404 = 'aligulac.views.h404'
handler500 = 'aligulac.views.h500'

urlpatterns = patterns('',
    url(r'^$', 'aligulac.views.home'),

    url(r'^periods/$', 'ratings.ranking_views.periods'),
    url(r'^periods/(?P<period_id>\d+)/$', 'ratings.ranking_views.period'),

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

    url(r'^admin/', include(admin.site.urls)),
)

# {{{ If in debug mode (i.e. with the django server), we must serve CSS and JS ourselves.
if settings.DEBUG:
    urlpatterns += patterns('',
        url(r'^css/(?P<path>.*)$', 'django.views.static.serve',
            {'document_root': settings.PROJECT_PATH + '../templates/css'}),
        url(r'^js/(?P<path>.*)$', 'django.views.static.serve',
            {'document_root': settings.PROJECT_PATH + '../templates/js'}),
    )
# }}}
