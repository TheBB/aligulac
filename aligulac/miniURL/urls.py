from django.conf.urls import (
    patterns,
    url,
)

urlpatterns = patterns('miniURL.views',
    url(r'^$', 'list', name='url_list'),
    url(r'^new/$', 'new', name='url_new'),
    url(r'^(?P<code>\w{16})/$', 'find_redirect', name='url_redirect'),
)
