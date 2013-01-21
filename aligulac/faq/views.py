from django.shortcuts import render_to_response
from django.http import HttpResponse
from faq.models import Post

from aligulac.views import base_ctx

def faq(request):
    posts = Post.objects.order_by('index')

    base = base_ctx('About', 'FAQ', request)
    base.update({'posts': posts})
    base['curpage'] = 'FAQ'

    return render_to_response('faq.html', base)
