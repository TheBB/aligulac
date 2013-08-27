from django.shortcuts import render_to_response
from django.http import HttpResponse
from blog.models import Post

from aligulac.views import base_ctx

def blog(request):
    posts = Post.objects.order_by('-date')[:10]

    base = base_ctx('About', 'Blog', request)
    base.update({'blogposts': posts})

    return render_to_response('blog.html', base)
