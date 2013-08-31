from django.conf.urls import patterns, include, url
from aligulac import settings

from django.contrib import admin
admin.autodiscover()

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

    url(r'^admin/', include(admin.site.urls)),
)

# If in debug mode (i.e. with the django server), we must serve CSS and JS ourselves.
if settings.DEBUG:
    urlpatterns += patterns('',
        url(r'^css/(?P<path>.*)$', 'django.views.static.serve',
            {'document_root': settings.PROJECT_PATH + '../templates/css'}),
        url(r'^js/(?P<path>.*)$', 'django.views.static.serve',
            {'document_root': settings.PROJECT_PATH + '../templates/js'}),
    )
