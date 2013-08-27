# -*- coding: utf-8 -*-

from aligulac import settings
from django.views.decorators.cache import cache_page as django_cache_page

def cache_page(f):

    fname = f.__module__ + "." + f.func_name
    
    seconds = 60
    if "CACHE_TIMES" in dir(settings) and fname in settings.CACHE_TIMES:
        seconds = settings.CACHE_TIMES[fname]
    
    if seconds is None:
        return f

    return django_cache_page(seconds)(f)
