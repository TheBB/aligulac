# {{{ Imports
from collections import namedtuple
from datetime import datetime

from django.core.exceptions import PermissionDenied
from django.db.models import F, Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, render_to_response

from itertools import zip_longest

from ratings.models import (
    Event,
    Group,
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

    ctx["title"] = "Miscellaneous Pages"
    ctx["miscpages"] = (
        { "url": "/misc/balance/",
          "title": "Balance Report",
          "desc": "Charts showing balance in StarCraft II over time."
        },
        { "url": "/misc/days/",
          "title": "Number of days since...",
          "desc": "Page showing the most recent time some things happened."
        },
    )

    # http://docs.python.org/3.2/library/itertools.html
    def grouper(n, iterable, fillvalue=None):
        "grouper(3, 'ABCDEFG', 'x') --> ABC DEF Gxx"
        args = [iter(iterable)] * n
        return zip_longest(*args, fillvalue=fillvalue)

    ctx["miscpages"] = grouper(2, ctx["miscpages"])

    return render_to_response("misc.html", ctx)

# {{{
# Format (description, hover_description, queryset, type)
Clock = namedtuple('Clock', ['desc', 'alt_desc', 'object', 'type', 'date', 'years', 'days', 'extra'])
CLOCKS = [
    (
        "MMA and DongRaeGu played a Bo5+",
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
        "Mvp won a premier event",
        None,
        Event.objects.filter(type="event",
                             earnings__player_id=13,
                             earnings__placement=1,
                             earnings__earnings__gte=10000)
        .order_by("-latest"),
        "event_winner"
    ),
    (
        "A Korean terran won against a Korean protoss in a Bo5+ (offline)",
        None,
        Match.objects.symmetric_filter(
            Q(pla__country="KR", rca="P", scb__gt=F("sca"), rcb="T", plb__country="KR")
        ).filter(Q(sca__gte=3) | Q(scb__gte=3), offline=True).order_by("-date"),
        "match"
    ),
    (
        "A foreign terran won against a Korean protoss (offline)",
        None,
        Match.objects.symmetric_filter(
            Q(pla__country="KR", rca="P", scb__gt=F("sca"), rcb="T") & ~Q(plb__country="KR")
        ).filter(offline=True).order_by("-date"),
        "match"
    ),
    (
        "A foreigner won in Proleague",
        None,
        Match.objects.symmetric_filter(~Q(pla__country="KR") & Q(sca__gt=F("scb")))
        .filter(eventobj__fullname__istartswith="proleague")
        .order_by("-date"),
        "match"
    ),
    (
        "A foreginer won in the GSL Code S",
        None,
        Match.objects.symmetric_filter(~Q(pla__country="KR") & Q(sca__gt=F("scb")))
        .filter(eventobj__fullname__istartswith="GSL", eventobj__fullname__icontains="Code S")
        .order_by("-date"),
        "match"
    ),
    (
        "A CIS player won a major event",
        "Player from BY, RU, UA or KZ with 1st place prize money >= $2000",
        Event.objects.filter(earnings__placement=1,
                             earnings__player__country__in=["BY","RU","UA","KZ"],
                             earnings__earnings__gte=2000)
        .order_by("-latest"),
        "event_winner"
    ),
    (
        "A Nordic player won a major event",
        "Player from SE, NO, DK, IS or FI with 1st place prize money >= $2000",
        Event.objects.filter(earnings__placement=1,
                             earnings__player__country__in=["SE", "NO", "FI"],
                             earnings__earnings__gte=2000)
        .order_by("-latest"),
        "event_winner"
    ),
    (
        "A North American player won a major event",
        "Player from US or CA with 1st place prize money >= $2000",
        Event.objects.filter(earnings__placement=1,
                             earnings__player__country__in=["US", "CA"],
                             earnings__earnings__gte=2000)
        .order_by("-latest"),
        "event_winner"
    ),
    (
        "A foreginer won a premier event",
        "At least on game played offline with 1st place prize money >= $10,000",
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
        "JaeDong got second place in an event",
        None,
        (
            Event.objects
            .filter(type="event")
            .filter(earnings__player_id=73,
                    earnings__placement=2)
            .order_by("-latest")
        ),
        "event_winner"
    )
]

@cache_page
def clocks(request):
    ctx = base_ctx('Misc', 'Days Since...', request)

    ctx["title"] = "Number of days since..."
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

        diff = datetime.today().date() - date
        years = diff.days // 365
        days = diff.days % 365
        c = Clock(desc, alt_desc, obj, t, date, years, days, extra)

        ctx["clocks"].append(c)

    ctx["clocks"].sort(key=lambda c: c.date, reverse=True)

    return render_to_response("clocks.html", ctx)
# }}}

# {{{ training view
# Questions to TheBB
def training(request, team_id):
    team = get_object_or_404(Group, id=team_id)

    allowed = [
        ('Wake', 'mousesports'),
        ('mouz', 'mousesports'),
        ('TheBB', 'mousesports'),
    ]

    if not request.user.is_authenticated() or (request.user.username, team.name) not in allowed:
        raise PermissionDenied

    players = Player.objects.filter(
        groupmembership__group=team,
        groupmembership__current=True,
        groupmembership__playing=True,
    )

    out = []

    for rca in 'ptz':
        players_race = players.filter(race=rca.upper())
        for rcb in 'ptz':
            players_race_weak = players_race
            for other in [r for r in 'ptz' if r != rcb]:
                players_race_weak = players_race_weak.filter(
                    **{'current_rating__rating_v%s__lt' % rcb: F('current_rating__rating_v%s' % other)}
                )

            if players_race_weak.exists():
                out.append('<h3>Weak %sv%s</h3><ul>' % (rca.upper(), rcb.upper()))
                for p in players_race_weak:
                    out.append(
                        '<li>%s (%.0f; %+.0f)</li>' 
                        % ( 
                            p.tag, 
                            ratscale(p.current_rating.get_totalrating(rcb.upper())),
                            ratscalediff(p.current_rating.get_rating(rcb.upper())),
                        )
                    )
                out.append('</ul>')

                opponents = sorted(
                    [p for p in players if p.race == rcb.upper()],
                    key=lambda p: p.current_rating.get_totalrating(rca.upper()), reverse=True
                )

                out.append(
                    '<p>Strongest %sv%s players are, in order: %s.</p>'
                    % (rcb.upper(), rca.upper(), ', '.join([o.tag for o in opponents]))
                )

    return HttpResponse('\n'.join(out))
# }}}
