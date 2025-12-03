from aligulac import settings
from django.views.decorators.cache import cache_page as django_cache_page

def cache_page(view):
    fname = view.__module__ + '.' + view.__name__

    try:
        seconds = settings.CACHE_TIMES[fname]
    except:
        seconds = 60

    if seconds is None:
        return view

    return django_cache_page(seconds)(view)
