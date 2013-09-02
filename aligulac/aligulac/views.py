from django.shortcuts import render_to_response

from aligulac.cache import cache_page
from aligulac.tools import base_ctx

from blog.models import Post

from ratings.models import Rating
from ratings.tools import filter_active, populate_teams

@cache_page
def home(request):
    base = base_ctx(request=request)

    entries = filter_active(Rating.objects.filter(period=base['curp']))\
              .order_by('-rating')\
              .select_related('player')[0:10]

    populate_teams(entries)

    blogs = Post.objects.order_by('-date')[0:3]

    base.update({
        'entries': entries,
        'blogposts': blogs
    })

    return render_to_response('index.html', base)
