from django.shortcuts import render_to_response
from django.utils.translation import ugettext as _

from aligulac.cache import cache_page
from aligulac.tools import (
    base_ctx,
    Message,
)

from faq.models import Post

@cache_page
def faq(request):
    base = base_ctx('About', 'FAQ', request)

    if request.LANGUAGE_CODE != 'en':
        base['messages'].append(Message(
            _('The FAQ section is only in English, sorry.'),
            type=Message.INFO,
        ))

    base['posts'] = Post.objects.all()
    return render_to_response('faq.djhtml', base)
