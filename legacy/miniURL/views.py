import html.parser

from django.http import HttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.csrf import csrf_protect
from django.utils.translation import ugettext_lazy as _

from aligulac.cache import cache_page
from aligulac.tools import base_ctx

from miniURL.models import MiniURL

@csrf_protect
def new(request):
    h = html.parser.HTMLParser()
    longurl = h.unescape(request.GET['url'])

    try:
        miniURL = MiniURL(longURL=longurl)
        miniURL.save()
    except Exception as e:
        print(str(e))
        miniURL = MiniURL.objects.get(longURL=longurl)

    return HttpResponse(miniURL.code)

@cache_page
def find_redirect(request, code):
    mini = get_object_or_404(MiniURL, code=code)
    mini.nb_access += 1
    mini.save()

    return redirect(mini.longURL, permanent=True)
