import os
import datetime

os.environ['MPLCONFIGDIR'] = '/home/efonn/.matplotlib/'

from django.shortcuts import get_object_or_404
from django.db.models import Max, Sum
from django.http import HttpResponse

from ratings.models import Match, Rating, Player
from aligulac.settings import PATH_TO_STATIC

from matplotlib.figure import Figure
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.dates import MonthLocator, DateFormatter
from matplotlib.ticker import MultipleLocator, NullLocator
from scipy import interpolate
from pychip import pchip

import numpy
from numpy import linspace, array, zeros

def player_plot(request, player_id):
    if 'big' in request.GET:
        fig = Figure(figsize=(20,4), facecolor='white')
    else:
        fig = Figure(figsize=(10,2), facecolor='white')
    rect = 0.05, 0.11, 0.90, 0.85
    ax = fig.add_axes(rect)
    axt = ax.twinx()

    def update_ax(ax1):
        y1, y2 = ax1.get_ylim()
        axt.set_ylim(y1, y2)

    ax.callbacks.connect('ylim_changed', update_ax)

    player = get_object_or_404(Player, id=player_id)
    lastper = Rating.objects.filter(player=player, decay__lt=4).aggregate(Max('period__id'))['period__id__max']
    ratings = Rating.objects.filter(player=player, period__computed=True, period_id__lte=lastper)

    if 'before' in request.GET:
        try:
            ints = [int(x) for x in request.GET['before'].split('-')]
            td = datetime.date(ints[0], ints[1], ints[2])
            ratings = ratings.filter(period__end__lte=td)
        except:
            pass

    if 'after' in request.GET:
        try:
            ints = [int(x) for x in request.GET['after'].split('-')]
            td = datetime.date(ints[0], ints[1], ints[2])
            ratings = ratings.filter(period__end__gte=td)
        except:
            pass

    ratings = list(ratings.order_by('period__id'))

    if len(ratings) == 0:
        ratings = Rating.objects.filter(player=player, period__computed=True, period_id__lte=lastper)
        ratings = list(ratings.order_by('period__id'))

    if len(ratings) > 0:
        t = [r.period.end.toordinal() for r in ratings]
        rtg = [1000*(1.0+r.bf_rating) for r in ratings]
        rtgp = [1000*(1.0+r.bf_rating+1.96*r.bf_dev) for r in ratings]
        rtgm = [1000*(1.0+r.bf_rating-1.96*r.bf_dev) for r in ratings]
        rvp = [1000*(1.0+r.bf_rating+r.bf_rating_vp) for r in ratings]
        rvt = [1000*(1.0+r.bf_rating+r.bf_rating_vt) for r in ratings]
        rvz = [1000*(1.0+r.bf_rating+r.bf_rating_vz) for r in ratings]

        newt = linspace(t[0], t[-1], 7*len(t))
        rtgnew = pchip(array(t), array(rtg), array(newt))
        rtgnewp = pchip(array(t), array(rtgp), array(newt))
        rtgnewm = pchip(array(t), array(rtgm), array(newt))
        rvpnew = pchip(array(t), array(rvp), array(newt))
        rvtnew = pchip(array(t), array(rvt), array(newt))
        rvznew = pchip(array(t), array(rvz), array(newt))

        t = [datetime.datetime.fromordinal(int(k)) for k in newt]
        ax.plot_date(t[:-1], rvpnew[:-1], 'g--', lw=1)
        ax.plot_date(t[:-1], rvtnew[:-1], 'b--', lw=1)
        ax.plot_date(t[:-1], rvznew[:-1], 'r--', lw=1)
        ax.fill_between(t[:-1], rtgnewm[:-1], rtgnewp[:-1], facecolor='#dddddd', edgecolor='#bbbbbb')
        ax.plot_date(t[:-1], rtgnew[:-1], 'k', lw=1.5)
    
        ax.set_xlim(t[0], t[-2])
        btm = min(rtg+rvp+rvt+rvz)-200
        top = max(rtg+rvp+rvt+rvz)+200
        ax.set_ylim(btm, top)
        ax.xaxis.set_major_formatter(DateFormatter('%b %y'))
        ax.yaxis.set_major_locator(MultipleLocator(100*round((top-btm)/500.)))
        axt.yaxis.set_major_locator(MultipleLocator(100*round((top-btm)/500.)))
        numpts = ratings[-1].period.id - ratings[0].period.id
        K = 16 if 'big' in request.GET else 8
        delta = max(numpts / (K * 2), 1)
        months = range(1,13)[0::delta]
        ax.xaxis.set_major_locator(MonthLocator(months))

        for tl in axt.get_xticklabels():
            tl.set_visible(False)

    response = HttpResponse(content_type='image/png')
    canvas = FigureCanvasAgg(fig)
    canvas.print_png(response)
    return response

def balance_plot(request):
    first = (2010,7)
    last = Match.objects.order_by('-date')[0].date
    last = (last.year, last.month)

    N = (last[0]-first[0])*12 + last[1]-first[1] + 1

    def nti(x):
        return 0 if x is None else x

    def add_to_array(qset, rc1, rc2, ar, col):
        temp = qset.filter(rca=rc1, rcb=rc2).aggregate(Sum('sca'), Sum('scb'))
        ar[0, col] += nti(temp['sca__sum'])
        ar[1, col] += nti(temp['scb__sum'])
        temp = qset.filter(rca=rc2, rcb=rc1).aggregate(Sum('sca'), Sum('scb'))
        ar[0, col] += nti(temp['scb__sum'])
        ar[1, col] += nti(temp['sca__sum'])

    if request.GET['matchup'].upper() in ['PVT','TVP','PVZ','ZVP','TVZ','ZVT']:
        races = request.GET['matchup'].upper().split('V')
    else:
        races = ['P','T']

    scores = zeros((2,N))
    time = zeros(N)

    ind = 0
    while first[0] < last[0] or (first[0] == last[0] and first[1] <= last[1]):
        matches = Match.objects.filter(date__gte='%i-%i-01' % first)
        if first[1] < 12:
            matches = matches.filter(date__lt='%i-%i-01' % (first[0], first[1]+1))
        else:
            matches = matches.filter(date__lt='%i-%i-01' % (first[0]+1, 1))

        add_to_array(matches, races[0], races[1], scores, ind)
        time[ind] = matches[0].date.toordinal() + 15
        first = (first[0], first[1]+1)
        if first[1] == 13:
            first = (first[0]+1, 1)
        ind += 1

    z = 1.96
    newtime = linspace(time[0], time[-1], 4*len(time))

    if 'big' in request.GET:
        fig = Figure(figsize=(20,4), facecolor='white')
    else:
        fig = Figure(figsize=(10,2), facecolor='white')
    rect = 0.05, 0.11, 0.90, 0.85
    ax = fig.add_axes(rect)

    def plot_rate(wins, losses, time, newtime, ax, fc, ec, lc):
        n = wins+losses
        f = wins/n
        width = z*numpy.sqrt(f*(1-f)/n+z**2/4/n**2)/(1+z**2/n)
        f = interpolate.splev(newtime, interpolate.splrep(time, f, s=0), der=0)
        width = interpolate.splev(newtime, interpolate.splrep(time, width), der=0)
        ax.fill_between(newtime, (f-width), (f+width), facecolor=fc, edgecolor=ec)
        ax.plot_date(newtime, f, lc, lw=2)

    plot_rate(scores[0,:], scores[1,:], time, newtime, ax, '#ddffdd', '#bbddbb', '#33aa33')
    ax.plot_date([newtime[0], newtime[-1]], [0.5, 0.5], 'k--', lw=1)

    ax.set_xlim(time[0], time[-1])
    ax.set_ylim(0.3, 0.7)
    ax.xaxis.set_major_formatter(DateFormatter('%b %y'))

    response = HttpResponse(content_type='image/png')
    canvas = FigureCanvasAgg(fig)

    with open(fn, 'w') as f:
        canvas.print_png(f)

    canvas.print_png(response)
    return response
