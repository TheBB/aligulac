from django.http import HttpResponse

from aligulac.tools import base_ctx

def add_matches(request):
    base = base_ctx('Submit', 'Matches', request)

    return HttpResponse(base['user'])
