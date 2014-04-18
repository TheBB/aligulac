# {{{ Imports
from collections import namedtuple
from datetime import datetime

from django.core.exceptions import PermissionDenied
from django.db.models import F, Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, render_to_response
from django.utils.translation import ugettext_lazy as _

from itertools import zip_longest

from ratings.models import (
    Event,
    Group,
    GroupMembership,
    Match,
    Player,
)
from aligulac.cache import cache_page
from aligulac.tools import base_ctx
from ratings.tools import display_matches
from ratings.templatetags.ratings_extras import (
    ratscale,
    ratscalediff,
)
# }}}

@cache_page
def home(request):
    ctx = base_ctx('Misc', request=request)

    ctx["title"] = _("Miscellaneous Pages")
    ctx["miscpages"] = (
        { "url": "/misc/balance/",
          "title": _("Balance Report"),
          "desc": _("Charts showing balance in StarCraft II over time.")
        },
        { "url": "/misc/days/",
          "title": _("Number of days since…"),
          "desc": _("Page showing the most recent time some things happened.")
        },
    )

    # http://docs.python.org/3.2/library/itertools.html
    def grouper(n, iterable, fillvalue=None):
        "grouper(3, 'ABCDEFG', 'x') --> ABC DEF Gxx"
        args = [iter(iterable)] * n
        return zip_longest(*args, fillvalue=fillvalue)

    ctx["miscpages"] = grouper(2, ctx["miscpages"])

    return render_to_response("misc.html", ctx)

# {{{ Clocks
# Format (description, hover_description, queryset, type)
Clock = namedtuple('Clock', ['desc', 'alt_desc', 'object', 'type', 'date', 'years', 'days', 'extra'])
CLOCKS = [
    (
        _("MMA and DongRaeGu played a Bo5+"),
        None,
        (
            Match.objects
            .symmetric_filter(pla_id=28, plb_id=4)
            .filter(Q(sca__gte=3) | Q(scb__gte=3))
            .order_by("-date")
        ),
        "match"
    ),
    (
        _("Mvp won a premier event"),
        None,
        Event.objects.filter(type="event",
                             earnings__player_id=13,
                             earnings__placement=1,
                             earnings__earnings__gte=10000)
        .order_by("-latest"),
        "event_winner"
    ),
    (
        _("A Korean terran won against a Korean protoss in a Bo5+ (offline)"),
        None,
        Match.objects.symmetric_filter(
            Q(pla__country="KR", rca="P", scb__gt=F("sca"), rcb="T", plb__country="KR")
        ).filter(Q(sca__gte=3) | Q(scb__gte=3), offline=True).order_by("-date"),
        "match"
    ),
    (
        _("A foreign terran won against a Korean protoss (offline)"),
        None,
        Match.objects.symmetric_filter(
            Q(pla__country="KR", rca="P", scb__gt=F("sca"), rcb="T") & ~Q(plb__country="KR")
        ).filter(offline=True).order_by("-date"),
        "match"
    ),
    (
        _("A foreigner won in Proleague"),
        None,
        Match.objects.symmetric_filter(~Q(pla__country="KR") & Q(sca__gt=F("scb")))
        .filter(eventobj__fullname__istartswith="proleague")
        .order_by("-date"),
        "match"
    ),
    (
        _("A foreigner won in the GSL Code S"),
        None,
        Match.objects.symmetric_filter(~Q(pla__country="KR") & Q(sca__gt=F("scb")))
        .filter(eventobj__fullname__istartswith="GSL", eventobj__fullname__icontains="Code S")
        .order_by("-date"),
        "match"
    ),
    (
        _("A CIS player won a major event"),
        _("Player from BY, RU, UA or KZ with 1st place prize money >= $2000"),
        Event.objects.filter(earnings__placement=1,
                             earnings__player__country__in=["BY","RU","UA","KZ"],
                             earnings__earnings__gte=2000)
        .order_by("-latest"),
        "event_winner"
    ),
    (
        _("A Nordic player won a major event"),
        _("Player from SE, NO, DK, IS or FI with 1st place prize money >= $2000"),
        Event.objects.filter(earnings__placement=1,
                             earnings__player__country__in=["SE", "NO", "FI"],
                             earnings__earnings__gte=2000)
        .order_by("-latest"),
        "event_winner"
    ),
    (
        _("A North American player won a major event"),
        _("Player from US or CA with 1st place prize money >= $2000"),
        Event.objects.filter(earnings__placement=1,
                             earnings__player__country__in=["US", "CA"],
                             earnings__earnings__gte=2000)
        .order_by("-latest"),
        "event_winner"
    ),
    (
        _("A foreigner won a premier event"),
        _("At least one game played offline with 1st place prize money >= $10,000"),
        (
            Event.objects
            .filter(type="event")
            .filter(downlink__child__match__offline=True)
            .filter(~Q(earnings__player__country="KR"),
                    earnings__placement=1,
                    earnings__earnings__gte=10000)
            .distinct()
            .order_by("-latest")
        ),
        "event_winner"
    ),
    (
        _("Jaedong got second place in an event"),
        None,
        (
            Event.objects
            .filter(type="event")
            .filter(earnings__player_id=73,
                    earnings__placement=2)
            .order_by("-latest")
        ),
        "event_winner"
    ),
    (
        _("SlayerS disbanded"),
        None,
        lambda: Group.objects.get(id=47).disbanded,
        "one_time"
    ),
    (
        _("HasuObs joined mousesports"),
        None,
        lambda: GroupMembership.objects.get(player_id=83,group_id=22).start,
        "one_time"
    )
]

@cache_page
def clocks(request):
    ctx = base_ctx('Misc', 'Days Since…', request)

    ctx["title"] = _("Number of days since…")
    ctx["clocks"] = list()
    for desc, alt_desc, q, t in CLOCKS:
        obj = None
        extra = None
        date = None

        if t == "match":
            q = q.prefetch_related("pla", "plb", "eventobj")
            matches = list(q[:10])

            extra = display_matches(matches)

            obj = matches[0]
            date = obj.date

        elif t == "event_winner":
            q = q.prefetch_related("earnings_set")
            events = list(q[:10])
            obj = events[0]
            extra = list()
            for e in events:
                pearnings = list(
                    e.earnings_set
                    .exclude(placement=0)
                    .order_by("placement")
                    .prefetch_related("player")[:2]
                )
                extra.append((e, pearnings))

            date = obj.latest

        elif t == "one_time":
            date = q()

        diff = datetime.today().date() - date
        years = diff.days // 365
        days = diff.days % 365
        c = Clock(desc, alt_desc, obj, t, date, years, days, extra)

        ctx["clocks"].append(c)

    ctx["clocks"].sort(key=lambda c: c.date, reverse=True)

    return render_to_response("clocks.html", ctx)
# }}}
