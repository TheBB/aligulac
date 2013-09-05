import html.parser

from django.http import HttpResponse
from django.shortcuts import render
from django.views.decorators.csrf import csrf_protect

from aligulac.cache import cache_page
from aligulac.tools import base_ctx

from miniURL.models import MiniURL

@cache_page
def list(request):
    base = base_ctx(request=request)
    base['minis'] = MiniURL.objects.order_by('-nb_access')
    return render(request, 'miniURL/list.html', base)

@csrf_protect
def new(request):
    h = html.parser.HTMLParser()
    longurl = h.unescape(request.POST['url'])

    if request.method == 'POST':
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
