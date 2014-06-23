# {{{ Imports
import re

from collections import Counter, namedtuple
from datetime import datetime

from django import forms
from django.core.exceptions import PermissionDenied, ValidationError
from django.db.models import F, Q, Sum
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, render_to_response, redirect
from django.utils.translation import ugettext_lazy as _

from itertools import zip_longest

from urllib.parse import quote

from ratings.comparisons import (
    Comparison,
    EarningsComparison,
    FormComparison,
    MatchComparison,
    MetaComparison,
    PercentageComparison,
    PredictionComparison,
    RatingComparison,
    SimpleComparison
)
from ratings.models import (
    Event,
    Group,
    GroupMembership,
    Match,
    Player,
)
from ratings.templatetags.ratings_extras import player_url
from aligulac.cache import cache_page
from aligulac.tools import (
    base_ctx,
    Message,
    NotUniquePlayerMessage
)
from ratings.tools import display_matches, find_player, ntz
from ratings.templatetags.ratings_extras import (
    add_sep_and_cur,
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
        { "url": "/misc/compare/",
          "title": _("Compare"),
          "desc": _("Tool for comparing players.")
        }
    )

    # http://docs.python.org/3.2/library/itertools.html
    def grouper(n, iterable, fillvalue=None):
        "grouper(3, 'ABCDEFG', 'x') --> ABC DEF Gxx"
        args = [iter(iterable)] * n
        return zip_longest(*args, fillvalue=fillvalue)

    ctx["miscpages"] = grouper(2, ctx["miscpages"])

    return render_to_response("misc.djhtml", ctx)

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

    return render_to_response("clocks.djhtml", ctx)
# }}}


# {{{ Compare players

class CompareForm(forms.Form):
    players = forms.CharField(
        max_length=10000,
        required=True,
        label=_('Players'),
        initial='')

    # {{{ Constructor
    def __init__(self, request=None):
        if request is not None:
            super().__init__(request.GET)
        else:
            super().__init__()
        self.messages = []
    # }}}

    # Copied from inference_views.PredictForm
    def clean_players(self):
        lines = self.cleaned_data['players'].splitlines()
        lineno, ok, players = -1, True, []

        for line in lines:
            lineno += 1
            if line.strip() == '':
                continue

            pls = find_player(query=line, make=False)
            if not pls.exists():
                # Translators: Matches as in search matches
                self.messages.append(Message(_("No matches found: '%s'.") % line.strip(), type=Message.ERROR))
                ok = False
            elif pls.count() > 1:
                self.messages.append(NotUniquePlayerMessage(
                    line.strip(), pls, update=self['players'].auto_id,
                    updateline=lineno, type=Message.ERROR
                ))
                ok = False
            else:
                players.append(pls.first())

        if not ok:
            raise ValidationError(_('One or more errors found in player list.'))


        if len(players) < 2:
            raise ValidationError(_('Enter at least two players.'))
        if len(players) > 6:
            raise ValidationError(_('Enter at most six players.'))
        return players

    # {{{ get_messages: Returns a list of messages after validation
    def get_messages(self):
        if not self.is_valid():
            ret = []
            for field, errors in self.errors.items():
                for error in errors:
                    if field == '__all__':
                        ret.append(Message(error, type=Message.ERROR))
                    else:
                        ret.append(Message(error=error, field=self.fields[field].label))
            return self.messages + ret

        return self.messages
    # }}}

    # {{{ generate_url: Returns an URL to continue to (assumes validation has passed)
    def generate_url(self):
        return '/misc/compare/%s/' % (
            ','.join(
                player_url(p, with_path=False)
                for p in self.cleaned_data['players']
            ),
        )
    # }}}


@cache_page
def compare_search(request):

    base = base_ctx('Misc', 'Compare', request)
    base["title"] = _("Comparison")

    if "op" in request.GET:
        op = request.GET["op"].lower()

    if "players" not in request.GET:
        form = CompareForm()
        validate = False
    else:
        form = CompareForm(request=request)
        if "op" not in request.GET:
            validate = False
        elif op == "compare":
            validate = True
        else:
            validate = False

    base["form"] = form

    if not validate:
        return render_to_response('compare.search.djhtml', base)

    if not form.is_valid():
        base["messages"] += form.get_messages()
        return render_to_response('compare.search.djhtml', base)

    return redirect(form.generate_url())

@cache_page
def compare(request, players):
    base = base_ctx('Misc', 'Compare', request)

    # {{{ Check that we have enough players
    if players is None:
        return redirect('/misc/compare/')

    player_regex = re.compile(r"(\d+)(-[^ /,]*)?")

    try:
        players = [
            int(player_regex.match(x).group(1))
            for x in players.split(',')
        ]
    except:
        return redirect('/misc/compare/')

    fail_url =  (
        "/misc/compare/?op=edit&players=" +
        quote('\n'.join(str(x) for x in players))
    )

    if len(players) < 2 or len(players) > 6:
        return redirect(fail_url)
    # }}}

    q = Player.objects.filter(id__in=players)\
                      .prefetch_related('current_rating')

    # Make sure that they're in the right order
    clean_players = list(players)
    for p in q:
        idx = players.index(p.id)
        clean_players[idx] = p


    def fmt_url_player(x):
        if isinstance(x, int):
            return str(x)
        else:
            return x.tag + " " + str(x.id)

    edit_url =  (
        "/misc/compare/?op=edit&players=" +
        quote('\n').join(quote(fmt_url_player(x)) for x in clean_players)
    )

    # If a player couldn't be found
    if any(isinstance(x, int) for x in clean_players):
        return redirect(edit_url)

    base["title"] = _("Comparison")
    base["subnav"] = [
        (_("New"), "/misc/compare/"),
        (_("Edit"), edit_url)
    ]
    base['players'] = clean_players

    comparisons = [_("Rating")]

    comparisons.extend(
        RatingComparison(clean_players, name, prop)
        for prop, name in RATING_COMPARISONS
    )

    comparisons.append(_("Probability of winning..."))
    if len(clean_players) == 2:
        comparisons.append(PredictionComparison(
            clean_players, _("a Bo3"), bo=3, kind='match')
        )

    if len(clean_players) > 2:
        comparisons.append(PredictionComparison(
            clean_players, _("a round robin group"), bo=3, kind='rr')
        )

    if len(clean_players) == 4:
        comparisons.append(PredictionComparison(
            clean_players, _("a dual tournament"), bo=3, kind='dual')
        )

    if len(clean_players) == 2:
        comparisons.append(_("Between these players"))
        matches = Match.objects.filter(
            pla__in=players,
            plb__in=players
        ).prefetch_related('pla', 'plb')
        comparisons.append(MatchComparison(
            clean_players, _("Match wins"), matches))
        comparisons.append(MatchComparison(
            clean_players, _("Match +/-"), matches, pm=True))
        comparisons.append(None)
        comparisons.append(MatchComparison(
            clean_players, _("Game wins"), matches, kind="games"))
        comparisons.append(MatchComparison(
            clean_players, _("Game +/-"), matches, kind="games", pm=True))

    comparisons.append(_("Lifetime"))
    matches = Match.objects.symmetric_filter(
        pla__in=players
    )
    comparisons.append(MatchComparison(
        clean_players, _("Match wins"), matches))
    comparisons.append(MatchComparison(
        clean_players, _("Match win %"), matches, percent=True))
    comparisons.append(MatchComparison(
        clean_players, _("Match +/-"), matches, pm=True))
    comparisons.append(None)
    comparisons.append(MatchComparison(
        clean_players, _("Game wins"), matches, kind="games"))
    comparisons.append(MatchComparison(
        clean_players, _("Game win %"), matches, kind="games", percent=True))
    comparisons.append(MatchComparison(
        clean_players, _("Game +/-"), matches, kind="games", pm=True))

    # comparisons.append(_("WCS 2014"))
    # matches = Match.objects.symmetric_filter(
    #     pla__in=players,
    #     eventobj__uplink__parent=23398
    # )
    # comparisons.append(MatchComparison(
    #     clean_players, _("Match wins"), matches))
    # comparisons.append(MatchComparison(
    #     clean_players, _("Match win %"), matches, percent=True))
    # comparisons.append(MatchComparison(
    #     clean_players, _("Match +/-"), matches, pm=True))
    # comparisons.append(None)
    # comparisons.append(MatchComparison(
    #     clean_players, _("Game wins"), matches, kind="games"))
    # comparisons.append(MatchComparison(
    #     clean_players, _("Game win %"), matches, kind="games", percent=True))
    # comparisons.append(MatchComparison(
    #     clean_players, _("Game +/-"), matches, kind="games", pm=True))

    comparisons.append(_("Other stats"))
    comparisons.append(EarningsComparison(clean_players, _("Earnings")))

    comparisons.append(FormComparison(clean_players, _("Current Form")))

    comparisons.append(_("Meta"))

    comparisons.append(MetaComparison(clean_players, _("Total"), comparisons))

    base['comparisons'] = comparisons

    return render_to_response('compare.djhtml', base)

# (property chain, label)
RATING_COMPARISONS = (
    (('current_rating', 'rating'), _("General")),
    (('current_rating', lambda x: x.get_totalrating_vp()), _("vP")),
    (('current_rating', lambda x: x.get_totalrating_vt()), _("vT")),
    (('current_rating', lambda x: x.get_totalrating_vz()), _("vZ"))
)

# }}}

