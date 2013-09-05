from django.shortcuts import render_to_response

from aligulac.cache import cache_page
from aligulac.tools import base_ctx

from blog.models import Post

@cache_page
def blog(request):
    base = base_ctx('About', 'Blog', request)
    base['blogposts'] = Post.objects.all()[:10]
    return render_to_response('blog.html', base)
