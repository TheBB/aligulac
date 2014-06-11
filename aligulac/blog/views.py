from django.shortcuts import render_to_response
from django.utils.translation import ugettext as _

from aligulac.cache import cache_page
from aligulac.tools import (
    base_ctx,
    Message,
)

from blog.models import Post

@cache_page
def blog(request):
    base = base_ctx('About', 'Blog', request)

    if request.LANGUAGE_CODE != 'en':
        base['messages'].append(Message(
            _('The blog/news section is only in English, sorry.'),
            type=Message.INFO,
        ))

    base['blogposts'] = Post.objects.all()[:10]
    return render_to_response('blog.djhtml', base)
