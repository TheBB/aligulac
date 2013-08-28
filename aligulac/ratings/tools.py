from ratings.models import Period, Player, Rating
from aligulac.settings import INACTIVE_THRESHOLD

# {{{ get_latest_period: Returns the latest computed period, or None.
def get_latest_period():
    try:
        return Period.objects.filter(computed=True).order_by('-start')[0]
    except:
        return None
# }}}

# {{{ filter_active: Filters a rating queryset by removing inactive ratings.
def filter_active(queryset):
    return queryset.filter(decay__lt=INACTIVE_THRESHOLD)
# }}}

# {{{ filter_inactive: Filters a rating queryset by removing active ratings.
def filter_inactive(queryset):
    return queryset.exclude(decay__lt=INACTIVE_THRESHOLD)
# }}}

# {{{ populate_teams: Adds team information to rows in a queryset (ratings or players) by populating the
# members team (short name), teamfull (full name) and teamid (team ID).
def populate_teams(queryset):
    for e in queryset:
        if isinstance(e, Player):
            player = e
        else:
            player = e.player

        membership = player.get_current_teammembership()
        if membership:
            e.team = membership.group.shortname
            e.teamfull = membership.group.name
            e.teamid = membership.group.id
# }}}
