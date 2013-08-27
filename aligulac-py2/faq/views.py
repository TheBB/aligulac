from aligulac.cache import cache_page

from django.shortcuts import render_to_response
from django.http import HttpResponse
from faq.models import Post

from aligulac.views import base_ctx

@cache_page
def faq(request):
    posts = Post.objects.order_by('index')

    base = base_ctx('About', 'FAQ', request)
    base.update({'posts': posts})

    return render_to_response('faq.html', base)
