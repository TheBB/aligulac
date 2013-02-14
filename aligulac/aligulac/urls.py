from django.conf.urls import patterns, include, url
from aligulac import settings

from django.contrib import admin
admin.autodiscover()

urlpatterns = patterns('',
    url(r'^$', 'aligulac.views.home', name='home'),

    url(r'^periods/$', 'ratings.views.periods'),
    url(r'^periods/(?P<period_id>\d+)/$', 'ratings.views.period'),

    url(r'^players/(?P<player_id>\d+)/$', 'ratings.views.player'),
    url(r'^players/(?P<player_id>\d+)/period/(?P<period_id>\d+)/$', 'ratings.views.rating_details'),
    url(r'^players/(?P<player_id>\d+)/plot/$', 'ratings.views.player_plot'),
    url(r'^players/(?P<player_id>\d+)/results/$', 'ratings.views.player_results'),
    url(r'^players/(?P<player_id>\d+)/historical/$', 'ratings.views.player_historical'),

    url(r'^teams/$', 'ratings.teamviews.teams'),
    url(r'^teams/(?P<team_id>\d+)/$', 'ratings.teamviews.team'),

    url(r'^results/$', 'ratings.views.results'),
    url(r'^results/events/$', 'ratings.views.events'),
    url(r'^results/events/(?P<event_id>\d+)/$', 'ratings.views.events'),
    url(r'^results/search/$', 'ratings.views.results_search'),

    url(r'^records/$', 'ratings.views.records'),

    url(r'^predict/$', 'ratings.predict.predict'),
    url(r'^predict/match/$', 'ratings.predict.pred_match'),
    url(r'^predict/4pswiss/$', 'ratings.predict.pred_4pswiss'),
    url(r'^predict/sebracket/$', 'ratings.predict.pred_sebracket'),
    url(r'^predict/rrgroup/$', 'ratings.predict.pred_rrgroup'),

    url(r'^faq/$', 'faq.views.faq'),
    url(r'^blog/$', 'blog.views.blog'),
    url(r'^db/$', 'aligulac.views.db'),
    url(r'^search/$', 'aligulac.views.search'),

    url(r'^add/$', 'ratings.submitviews.add_matches'),
    url(r'^add/review/$', 'ratings.submitviews.review'),
    url(r'^add/events/$', 'ratings.submitviews.manage_events'),
    url(r'^add/integrity/$', 'ratings.submitviews.integrity'),
    url(r'^add/misc/$', 'ratings.submitviews.manage'),

    url(r'^login/$', 'aligulac.views.loginv'),
    url(r'^logout/$', 'aligulac.views.logoutv'),
    url(r'^changepwd/$', 'aligulac.views.changepwd'),

    url(r'^api/search/$', 'aligulac.views.api_search'),
    # url(r'^admin/doc/', include('django.contrib.admindocs.urls')),

    url(r'^404/$', 'aligulac.views.h404'),

    url(r'^favicon\.ico$', 'django.views.generic.simple.redirect_to',\
            {'url': 'http://aligulac.com:81/al/favicon.ico'}),
    url(r'^admin/', include(admin.site.urls)),
)

if settings.DEBUG:
    urlpatterns += patterns('',
        url(r'^css/(?P<path>.*)$', 'django.views.static.serve',\
            {'document_root': '/home/efonn/projects/aligulac/templates/css'}),
        url(r'^js/(?P<path>.*)$', 'django.views.static.serve',\
            {'document_root': '/home/efonn/projects/aligulac/templates/js'}),
                           )

handler404 = 'aligulac.views.h404'
handler500 = 'aligulac.views.h500'
