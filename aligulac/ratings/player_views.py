from datetime import datetime, date, timedelta

from django import forms
from django.db.models import Sum
from django.http import HttpResponse
from django.shortcuts import render_to_response, get_object_or_404

from aligulac.cache import cache_page
from aligulac.tools import Message, base_ctx, generate_messages, post_param
from aligulac.settings import INACTIVE_THRESHOLD

from ratings.models import Match, Player
from ratings.tools import PATCHES, total_ratings, ntz, split_matchset, count_winloss_games, display_matches

from countries import data, transformations

msg_inactive = 'Due to %s\'s lack of recent games, they have been marked as <em>inactive</em> and '\
             + 'removed from the current rating list. Once they play a rated game they will be reinstated.'
msg_nochart =  '%s has no rating chart on account of having played matches in fewer than two periods.'

# {{{ meandate: Rudimentary function for sorting objects with a start and end date.
def meandate(tm):
    if tm.start is not None and tm.end is not None:
        return (tm.start.toordinal() + tm.end.toordinal()) / 2
    elif tm.start is not None:
        return tm.start.toordinal()
    elif tm.end is not None:
        return tm.end.toordinal()
    else:
        return 1000000
# }}}

# {{{ interp_rating: Takes a date and a rating list, and interpolates linearly.
def interp_rating(date, ratings):
    for ind, r in enumerate(ratings):
        if (r.period.end - date).days >= 0:
            try:
                right = (r.period.end - date).days
                left = (date - ratings[ind-1].period.end).days
                return (left*r.bf_rating + right*ratings[ind-1].bf_rating) / (left+right)
            except:
                return r.bf_rating
    return ratings[-1].bf_rating
# }}}

# {{{ PlayerModForm: Form for modifying a player.
class PlayerModForm(forms.Form):
    tag = forms.CharField(max_length=30, required=True)
    name = forms.CharField(max_length=100, required=False)
    birthday = forms.DateField(required=False)

    tlpd_id = forms.IntegerField(required=False)
    tlpd_db = forms.IntegerField(required=False)
    lp_name = forms.CharField(max_length=200, required=False)
    sc2c_id = forms.IntegerField(required=False)
    sc2e_id = forms.IntegerField(required=False)

    country = forms.ChoiceField(choices=data.countries, required=False)
# }}} 

# {{{ player view
@cache_page
def player(request, player_id):
    # {{{ Get player object and base context, generate messages and make changes if needed
    player = get_object_or_404(Player, id=player_id)
    base = base_ctx('Ranking', '%s:' % player.tag, request, context=player)
    base['messages'] += generate_messages(player)
    # }}}

    # {{{ Various easy data
    matches = player.get_matchset()
    matches_a, matches_b = split_matchset(matches, player)
    w_tot_a, l_tot_a = count_winloss_games(matches_a)
    l_tot_b, w_tot_b = count_winloss_games(matches_b)
    w_vp_a, l_vp_a = count_winloss_games(matches_a.filter(rcb=Player.P))
    l_vp_b, w_vp_b = count_winloss_games(matches_b.filter(rca=Player.P))
    w_vt_a, l_vt_a = count_winloss_games(matches_a.filter(rcb=Player.T))
    l_vt_b, w_vt_b = count_winloss_games(matches_b.filter(rca=Player.T))
    w_vz_a, l_vz_a = count_winloss_games(matches_a.filter(rcb=Player.Z))
    l_vz_b, w_vz_b = count_winloss_games(matches_b.filter(rca=Player.Z))

    base.update({
        'player':           player,
        'first':            matches.earliest('date'),
        'last':             matches.latest('date'),
        'totalmatches':     matches.count(),
        'offlinematches':   matches.filter(offline=True).count(),
        'aliases':          player.alias_set.all(),
        'earnings':         ntz(player.earnings_set.aggregate(Sum('earnings'))['earnings__sum']),
        'team':             player.get_current_team(),
        'total':            (w_tot_a + w_tot_b, l_tot_a, l_tot_b),
        'vp':               (w_vp_a + w_vp_b, l_vp_a, l_vp_b),
        'vt':               (w_vt_a + w_vt_b, l_vt_a, l_vt_b),
        'vz':               (w_vz_a + w_vz_b, l_vz_a, l_vz_b),
    })

    if player.country is not None:
        base['countryfull'] = transformations.cc_to_cn(player.country)
    # }}}

    # {{{ Recent matches
    matches = player.get_matchset()\
                    .select_related('pla__rating', 'plb__rating', 'period')\
                    .prefetch_related('message_set')\
                    .filter(date__range=(date.today() - timedelta(days=90), date.today()))\
                    .order_by('-date', '-id')[0:10]

    if matches.exists():
        base['matches'] = display_matches(matches, fix_left=player, ratings=True)
    # }}}

    # {{{ Team memberships
    team_memberships = list(player.groupmembership_set.filter(group__is_team=True))
    team_memberships.sort(key=lambda t: t.id, reverse=True)
    team_memberships.sort(key=meandate, reverse=True)
    team_memberships.sort(key=lambda t: t.current, reverse=True)
    base['teammems'] = team_memberships
    # }}}

    # {{{ If the player has at least one rating
    ratings = total_ratings(player.rating_set.filter(period__computed=True))
    if ratings.exists():
        rating = player.get_current_rating()
        base.update({
            'highs': (
                ratings.latest('rating'),
                ratings.latest('tot_vp'),
                ratings.latest('tot_vt'),
                ratings.latest('tot_vz'),
            ),
            'recentchange': player.get_latest_rating_update(),
            'firstrating': ratings.earliest('period'),
            'rating': rating,
        })

        if rating.decay >= INACTIVE_THRESHOLD:
            base['messages'].append(Message(msg_inactive % player.tag, 'Inactive', type=Message.INFO))

        base['charts'] = base['recentchange'].period_id > base['firstrating'].period_id
    else:
        base['messages'].append(Message('%s has no rating yet.' % player.tag, type=Message.INFO))
        base['charts'] = False
    # }}}

    # {{{ If the player has enough games to make a chart
    if base['charts']:
        ratings = total_ratings(player.rating_set.filter(period_id__lte=base['recentchange'].period_id))\
                  .order_by('period')
        base['ratings'] = ratings
        base['patches'] = PATCHES

        # {{{ Add stories and other extra information
        earliest = base['firstrating']
        latest = base['recentchange']

        # Look through team changes
        teampoints = []
        for mem in base['teammems']:
            if mem.start and earliest.period.end < mem.start < latest.period.end:
                teampoints.append({
                    'date': mem.start,
                    'rating': interp_rating(mem.start, ratings),
                    'data': [{'date': mem.start, 'team': mem.group, 'jol': 'joins'}],
                })
            if mem.end and earliest.period.end < mem.end < latest.period.end:
                teampoints.append({
                    'date': mem.end,
                    'rating': interp_rating(mem.end, ratings),
                    'data': [{'date': mem.end, 'team': mem.group, 'jol': 'leaves'}],
                })
        teampoints.sort(key=lambda p: p['date'])

        # Condense if team changes happened within 14 days
        cur = 0
        while cur < len(teampoints) - 1:
            if (teampoints[cur+1]['date'] - teampoints[cur]['date']).days <= 14:
                teampoints[cur]['data'].append(teampoints[cur+1]['data'][0])
                del teampoints[cur+1]
            else:
                cur += 1

        # Sort first by date, then by joined/left
        for point in teampoints:
            point['data'].sort(key=lambda a: a['jol'], reverse=True)
            point['data'].sort(key=lambda a: a['date'])

        # Look through stories
        stories = player.story_set.all()
        for s in stories:
            if earliest.period.start < s.date < latest.period.start:
                s.rating = interp_rating(s.date, ratings)
            else:
                s.skip = True

        base.update({
            'stories': stories,
            'teampoints': teampoints,
        })
        # }}}
    else:
        base['messages'].append(Message(msg_nochart % player.tag, type=Mesage.INFO))
    # }}}

    return render_to_response('player.html', base)
# }}}
