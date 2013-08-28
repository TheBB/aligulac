from django.conf.urls import patterns, include, url
from aligulac import settings

from django.contrib import admin
admin.autodiscover()

urlpatterns = patterns('',
    # Homepage
    url(r'^$', 'aligulac.views.home'),

    # Admin interface
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
