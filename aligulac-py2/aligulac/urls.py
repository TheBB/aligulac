from django.conf.urls import patterns, include, url
from aligulac import settings

from django.contrib import admin
admin.autodiscover()

urlpatterns = patterns('',
    url(r'^$', 'aligulac.views.home', name='home'),

    url(r'^periods/$', 'ratings.views.periods'),
    url(r'^periods/(?P<period_id>\d+)/$', 'ratings.views.period'),

    url(r'^earnings/$', 'ratings.views.earnings'),

    url(r'^players/(?P<player_id>\d+)(-[^ /]*)?/$', 'ratings.views.player'),
    url(r'^players/(?P<player_id>\d+)(-[^ /]*)?/period/(?P<period_id>\d+)/$', 'ratings.views.rating_details'),
    url(r'^players/(?P<player_id>\d+)(-[^ /]*)?/results/$', 'ratings.views.player_results'),
    url(r'^players/(?P<player_id>\d+)(-[^ /]*)?/historical/$', 'ratings.views.player_historical'),
    url(r'^players/(?P<player_id>\d+)(-[^ /]*)?/earnings/$', 'ratings.views.player_earnings'),

    url(r'^teams/$', 'ratings.teamviews.teams'),
    url(r'^teams/(?P<team_id>\d+)(-[^ /]*)?/$', 'ratings.teamviews.team'),
    url(r'^player_transfers/', 'ratings.teamviews.player_transfers'),

    url(r'^results/$', 'ratings.views.results'),
    url(r'^results/events/$', 'ratings.views.events'),
    url(r'^results/events/(?P<event_id>\d+)(-[^ /]*)?/$', 'ratings.views.events'),
    url(r'^results/search/$', 'ratings.views.results_search'),

    url(r'^records/race/$', 'ratings.views.records_race'),
    url(r'^records/history/$', 'ratings.views.records_history'),
    url(r'^records/hof/$', 'ratings.views.records_hof'),

    url(r'^predict/$', 'ratings.predictviews.predict'),
    url(r'^predict/match/$', 'ratings.predictviews.pred_match'),
    url(r'^predict/4pswiss/$', 'ratings.predictviews.pred_4pswiss'),
    url(r'^predict/sebracket/$', 'ratings.predictviews.pred_sebracket'),
    url(r'^predict/rrgroup/$', 'ratings.predictviews.pred_rrgroup'),
    url(r'^predict/proleague/$', 'ratings.predictviews.pred_proleague'),
    
    url(r'^compare/$', 'ratings.predictviews.compare'),

    url(r'^faq/$', 'faq.views.faq'),
    url(r'^blog/$', 'blog.views.blog'),
    url(r'^staff/$', 'aligulac.views.staff'),
    url(r'^db/$', 'aligulac.views.db'),
    url(r'^search/$', 'aligulac.views.search'),
    url(r'^m/', include('miniURL.urls')),
    
    url(r'^add/$', 'ratings.submitviews.add_matches'),
    url(r'^add/review/$', 'ratings.submitviews.review'),
    url(r'^add/events/$', 'ratings.submitviews.manage_events'),
    url(r'^add/open_events/$', 'ratings.submitviews.open_events'),
    url(r'^add/integrity/$', 'ratings.submitviews.integrity'),
    url(r'^add/misc/$', 'ratings.submitviews.manage'),

    url(r'^login/$', 'aligulac.views.loginv'),
    url(r'^logout/$', 'aligulac.views.logoutv'),
    url(r'^changepwd/$', 'aligulac.views.changepwd'),

    url(r'^api/search_players/$', 'ratings.apiviews.search_players'),
    url(r'^api/search_teams/$', 'ratings.apiviews.search_teams'),
    url(r'^api/search_events/$', 'ratings.apiviews.search_events'),
    url(r'^api/search/$', 'ratings.apiviews.search'),
    url(r'^api/rating_list/(?P<period>\d+)/$', 'ratings.apiviews.rating_list'),
    #url(r'^players/(?P<player_id>\d+)(-[^ /]*)?/earnings/$', 'ratings.views.player_earnings'),

    url(r'reports/$', 'ratings.views.balance'),
    url(r'reports/balance/$', 'ratings.views.balance'),

    url(r'^404/$', 'aligulac.views.h404'),
    url(r'^500/$', 'aligulac.views.h500'),

    url(r'^admin/', include(admin.site.urls)),
    # url(r'^admin/doc/', include('django.contrib.admindocs.urls')),
)

if settings.DEBUG:
    urlpatterns += patterns('',
        url(r'^css/(?P<path>.*)$', 'django.views.static.serve',\
            {'document_root': settings.PATH_TO_DIR + '../templates/css'}),
        url(r'^js/(?P<path>.*)$', 'django.views.static.serve',\
            {'document_root': settings.PATH_TO_DIR + '../templates/js'}),
                           )

handler404 = 'aligulac.views.h404'
handler500 = 'aligulac.views.h500'
