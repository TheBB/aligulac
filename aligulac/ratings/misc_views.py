# {{{ Imports
from collections import namedtuple

from django.core.exceptions import PermissionDenied
from django.db.models import F, Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, render_to_response

from ratings.models import (
    Group,
    Match,
    Player,
)
from aligulac.tools import base_ctx
from ratings.tools import display_matches
from ratings.templatetags.ratings_extras import (
    ratscale,
    ratscalediff,
)
# }}}

# {{{
# Format (description, queryset, type)
Clock = namedtuple('Clock', ['desc', 'object', 'type', 'date', 'extra'])
CLOCKS = [
    (
        "MMA and DongRaeGu played a Bo5+",
        Match.objects.symmetric_filter(pla_id=28, plb_id=4)\
        .filter(Q(sca__gte=3)|Q(scb__gte=3)).order_by("-date"),
        "match"
    ),
    (
        "Mvp won a Bo7",
        Match.objects.symmetric_filter(pla_id=13, sca=4, sca__gte=F("scb"))\
        .order_by("-date"),
        "match"
    ),
    (
        "A foreign terran won against a korean protoss (offline)",
        Match.objects.symmetric_filter(
            Q(pla__country="KR", rca="P", scb__gt=F("sca"), rcb="T") & ~Q(plb__country="KR")
        ).filter(offline=True).order_by("-date"),
        "match"
    ),
    (
        "A foreigner won in ProLeague",
        Match.objects.symmetric_filter(~Q(pla__country="KR") & Q(sca__gt=F("scb")))\
        .filter(eventobj__fullname__istartswith="ProLeague")\
        .order_by("-date"),
        "match"
    ),
    (
        "A foreginer won in GSL Code S",
        Match.objects.symmetric_filter(~Q(pla__country="KR") & Q(sca__gt=F("scb")))\
        .filter(Q(eventobj__fullname__istartswith="GSL", eventobj__fullname__icontains="Code S"))\
        .order_by("-date"),
        "match"
    )
]

def clocks(request):
    ctx = base_ctx('Misc', 'Clocks', request)

    ctx["title"] = "Number of days since..."
    ctx["clocks"] = list()
    for desc, q, t in CLOCKS:
        obj = None
        extra = None
        date = None

        if t == "match":
            q = q.prefetch_related("pla", "plb", "eventobj")
            matches = list(q[:10])

            if len(matches) > 1:
                extra = display_matches([matches[0]]), display_matches(matches[1:10])
            else:
                extra = display_matches([matches[0]]), None

            obj = matches[0]
            date = obj.date

        c = Clock(desc, obj, t, date.strftime("%Y-%m-%d"), extra)

        ctx["clocks"].append(c)

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
