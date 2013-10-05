# {{{ Imports
from datetime import date

from django import forms
from django.core.exceptions import PermissionDenied
from django.db.models import (
    F,
    Q,
    Sum,
    Count,
)
from django.http import HttpResponse
from django.shortcuts import get_object_or_404

from ratings.models import (
    Earnings,
    Group,
    GroupMembership,
    Match,
    P,
    Player,
    Rating,
    T,
    Z,
)
from ratings.templatetags.ratings_extras import (
    ratscale,
    ratscalediff,
)
from ratings.tools import (
    filter_active,
    filter_inactive,
    total_ratings,
)
# }}}

# {{{ training view
def training(request, team_id):
    team = get_object_or_404(Group, id=team_id)

    allowed = [
        ('Wake', 'mousesports')
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
