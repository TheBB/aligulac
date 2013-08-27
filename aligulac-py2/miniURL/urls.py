#-*- coding: utf-8 -*-

from django.conf.urls import patterns, url
 
urlpatterns = patterns('miniURL.views',
    url(r'^$', 'list', name='url_list'),  # Empty string for the root
    url(r'^new/$', 'new', name='url_new'),
    url(r'^(?P<code>\w{16})/$', 'find_redirect', name='url_redirect'),  # (?P<code>\w{6}) will capture the needed 16 alphanumeric caracters.
)
