from datetime import datetime, date

from django import forms
from django.db.models import Min, Max
from django.http import HttpResponse
from django.shortcuts import render_to_response, get_object_or_404
from django.views.decorators.csrf import csrf_protect

from aligulac.cache import cache_page
from aligulac.tools import get_param, base_ctx, StrippedCharField, generate_messages, Message

from ratings.models import Match
from ratings.tools import display_matches

# {{{ results view
@cache_page
def results(request):
    base = base_ctx('Results', 'By Date', request)

    try:
        day = datetime.strptime(get_param(request, 'd', None), '%Y-%m-%d').date()
    except:
        day = date.today()

    bounds = Match.objects.aggregate(Min('date'), Max('date'))
    day = min(max(bounds['date__min'], day), bounds['date__max'])
    base.update({
        'mindate': bounds['date__min'],
        'maxdate': bounds['date__max'],
        'td':      day,
    })

    matches = Match.objects.filter(date=day).order_by('eventobj__lft', 'event', 'id')\
                   .prefetch_related('message_set')
    base['matches'] = display_matches(matches, date=False, ratings=True, messages=True)

    return render_to_response('results.html', base)
# }}}
