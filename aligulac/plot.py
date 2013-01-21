#!/usr/bin/python

import os

from matplotlib.figure import Figure
from matplotlib.patches import Polygon
from matplotlib.backends.backend_agg import FigureCanvasAgg
import matplotlib.numerix as nx

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "aligulac.settings")

from ratings.models import Rating, Player, Period

fig = Figure(figsize=(16,3))
ax = fig.add_subplot(1,1,1)

Np = 20

first_per = Period.objects.filter(computed=True).order_by('-end')[Np]

player = Player.objects.get(tag='DIMAGA')
ratings = list(Rating.objects.filter(player=player).order_by('-period')[:20])
ax.plot([r.period.end for r in ratings[::-1]], [1000*(1.0+r.rating) for r in ratings[::-1]], 'k', linewidth=2)
ax.plot([r.period.end for r in ratings[::-1]], [1000*(1.0+r.rating+r.rating_vp) for r in ratings[::-1]], 'g')
ax.plot([r.period.end for r in ratings[::-1]], [1000*(1.0+r.rating+r.rating_vt) for r in ratings[::-1]], 'b')
ax.plot([r.period.end for r in ratings[::-1]], [1000*(1.0+r.rating+r.rating_vz) for r in ratings[::-1]], 'r')
ax.set_xlim(first_per.end, ratings[0].period.end)

canvas = FigureCanvasAgg(fig)
canvas.print_figure('../media/test.png', dpi=50)
