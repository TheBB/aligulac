# Create your views here.

#-*- coding: utf-8 -*-
from django.shortcuts import redirect, get_object_or_404, render
from models import MiniURL
from forms import MiniURLForm
import urllib
import HTMLParser

from aligulac.views import base_ctx
from django.http import HttpResponse


def list(request):
    """Print all redirects"""
    base = base_ctx(request=request)

    base['minis'] = MiniURL.objects.order_by('-nb_access')

    return render(request, 'miniURL/list.html', base)


def new(request):
    """Add a redirect"""
    h = HTMLParser.HTMLParser()
    longurl = h.unescape(request.POST['url'])

    if request.method == "POST":
        try:
            miniURL = MiniURL(longURL=longurl)
            miniURL.save()
        except:
            miniURL = MiniURL.objects.get(longURL=longurl)

    return HttpResponse(miniURL.code)


def find_redirect(request, code):
    """Redirect to the registered URL"""
    mini = get_object_or_404(MiniURL, code=code)
    mini.nb_access += 1
    mini.save()
 
    return redirect(mini.longURL, permanent=True)
