# {{{ Imports
from datetime import date
from dateutil.relativedelta import relativedelta

from django.db import connection
from django.db.models import Sum
from django.shortcuts import render_to_response

from aligulac.cache import cache_page
from aligulac.tools import (
    base_ctx,
    ntz,
)

from ratings.models import (
    BalanceEntry,
    Match,
)
from ratings.tools import (
    count_matchup_games,
    icdf,
    ntz,
    PATCHES,
)
# }}}

# {{{ Balance report view
@cache_page
def balance(request):
    base = base_ctx('Reports', 'Balance', request)

    base.update({
        'charts':   True,
        'patches':  PATCHES,
        'entries':  BalanceEntry.objects.all().order_by('date'),
    })

    base.update({"title": "Balance report"})

    return render_to_response('reports_balance.html', base)
# }}}
