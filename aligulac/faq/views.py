from django.shortcuts import render_to_response

from aligulac.cache import cache_page
from aligulac.tools import base_ctx

from faq.models import Post

@cache_page
def faq(request):
    base = base_ctx('About', 'FAQ', request)
    base['posts'] = Post.objects.all()
    return render_to_response('faq.html', base)
