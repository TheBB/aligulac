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

@cache_page
def balance(request):
    base = base_ctx('Reports', 'Balance', request)

    first = date(year=2010, month=7, day=1)
    last  = date.today().replace(day=1) - relativedelta(months=1)

    # {{{ Auxiliary functions for updating
    def get_data_perf_single(matches, rca, rcb):
        res = (
            matches.filter(rca=rca, rcb=rcb)
                .aggregate(
                    rta_sum      = Sum('rta__rating'),
                    rta_spec_sum = Sum('rta__rating_v%s' % rcb.lower()),
                    rtb_sum      = Sum('rtb__rating'),
                    rtb_spec_sum = Sum('rtb__rating_v%s' % rca.lower()),
                    sca_sum      = Sum('sca'),
                    scb_sum      = Sum('scb'),
                )
        )
        return (
            ntz(res['rta_sum']) + ntz(res['rta_spec_sum']),
            ntz(res['rtb_sum']) + ntz(res['rtb_spec_sum']),
            ntz(res['sca_sum']),
            ntz(res['scb_sum']),
        )

    def get_data_perf(matches, race):
        wa, wb, diff = 0, 0, 0.0
        for rcb in [r for r in 'PTZ' if r != race]:
            rta1, rtb1, sca1, scb1 = get_data_perf_single(matches, race, rcb)
            rtb2, rta2, scb2, sca2 = get_data_perf_single(matches, rcb, race)
            wa += sca1 + sca2
            wb += scb1 + scb2
            diff += rta1 + rta2 - rtb1 - rtb2

        perfdiff = icdf(wa/(wa+wb), loc=0.0, scale=1.0)
        return perfdiff - diff/(wa+wb)
    # }}}

    # {{{ Update data if necessary
    if not BalanceEntry.objects.filter(date__year=last.year, date__month=last.month).exists():
        while first <= last:
            matches = Match.objects.filter(date__gte=first, date__lt=(first+relativedelta(months=1)))
            pvt_w, pvt_l = count_matchup_games(matches, 'P', 'T')
            pvz_w, pvz_l = count_matchup_games(matches, 'P', 'Z')
            tvz_w, tvz_l = count_matchup_games(matches, 'T', 'Z')
            p_diff = get_data_perf(matches, 'P')
            t_diff = get_data_perf(matches, 'T')
            z_diff = get_data_perf(matches, 'Z')

            be, created = BalanceEntry.objects.get_or_create(
                date=first.replace(day=15),
                defaults={
                    'pvt_wins':    pvt_w,
                    'pvt_losses':  pvt_l,
                    'pvz_wins':    pvz_w,
                    'pvz_losses':  pvz_l,
                    'tvz_wins':    tvz_w,
                    'tvz_losses':  tvz_l,
                    'p_gains':     p_diff,
                    't_gains':     t_diff,
                    'z_gains':     z_diff,
                }
            )
            if not created:
                be.pvt_wins   = pvt_w
                be.pvt_losses = pvt_l
                be.pvz_wins   = pvz_w
                be.pvz_losses = pvz_l
                be.tvz_wins   = tvz_w
                be.tvz_losses = tvz_l
                be.p_gains    = p_diff
                be.t_gains    = t_diff
                be.z_gains    = z_diff
            be.save()

            first = first + relativedelta(months=1)
    # }}}

    base.update({
        'charts':   True,
        'patches':  PATCHES,
        'entries':  BalanceEntry.objects.all().order_by('date'),
    })

    return render_to_response('reports_balance.html', base)
