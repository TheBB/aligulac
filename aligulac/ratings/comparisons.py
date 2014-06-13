from collections import Counter
from django.db.models import Sum
from itertools import groupby
from ratings.inference_views import (
    DualPredictionResult,
    MatchPredictionResult,
    RoundRobinPredictionResult
)
from ratings.models import Match
from ratings.templatetags.ratings_extras import (
    add_sep_and_cur,
    ratscale
)

# {{{ Metaclass magic! This is not really necessary, but fun!
def cached_properties(cls_name, cls_parents, cls_attrs):
    """
    Creates a class where it caches properties marked with Cached()
    """
    new_attrs = {}
    cached = set()
    for k, v in cls_attrs.items():
        if isinstance(v, Cached):
            new_attrs[k] = v.get_property(k)
            cached.add(k)
        else:
            new_attrs[k] = v

    old_init = new_attrs["__init__"]
    def __init__(self, *args, **kwargs):
        old_init(self, *args, **kwargs)
        for k in cached:
            setattr(self, "_" + k, None)

    new_attrs["__init__"] = __init__

    return type(cls_name, cls_parents, new_attrs)

class Cached():
    def get_property(self, name):
        @property
        def wrapper(self):
            if getattr(self, "_" + name) is None:
                self.compute()
            return getattr(self, "_" + name)
        return wrapper
# }}}

class Comparison(metaclass=cached_properties):
    best = Cached()
    worst = Cached()
    sorted = Cached()
    groups = Cached()

    def __init__(self, players, name, ascending=True):
        self.name = name
        self.players = players
        self.ascending = ascending
        self.values = {}

    def get_value(self, player):
        if player.id not in self.values:
            self.values[player.id] = self._get_value(player)
        return self.values[player.id]

    def get_value_print(self, player):
        if player.id not in self.values:
            self.get_value(player)
        return self._print(player)

    def get_position(self, player):
        pos = 1
        for g in self.groups:
            if player in g:
                return pos
            else:
                pos += len(g)
        return None

    def compute(self):
        self._sorted = list(self.players)
        f = 1 if self.ascending else -1
        self._sorted.sort(key=lambda x: f*self.get_value(x))

        self._groups = [
            list(g)
            for k, g in groupby(self._sorted, key=lambda x: self.get_value(x))
        ]
        self._best = self._groups[0]
        self._worst = self._groups[-1]

    @property
    def entries(self):
        return [ComparisonEntry(p, self) for p in self.players]

class ComparisonEntry():
    def __init__(self, player, comp):
        self.comp = comp
        self.player = player
        self.value = comp.get_value(player)
        self.value_print = comp.get_value_print(player)
        self.is_best = player in comp.best and \
                       len(comp.best) < len(comp.players)
        self.is_worst = player in comp.worst and \
                       len(comp.worst) < len(comp.players)
        self.index = comp.get_position(player)

def iterable(a):
    try:
        (x for x in a)
        return True
    except TypeError:
        return False

class SimpleComparison(Comparison):
    def __init__(self, players, name, properties, ascending):
        super().__init__(players, name, ascending)
        if not iterable(properties):
            self.properies = [properties]
        else:
            self.properies = list(properties)

    def _get_value(self, p):
        # We want this to be as nice as possible. Therefore, self.properties
        # should contain an iterable of the following
        #  - Attribute string → the value is the value of the attribute. (Called
        #    if needed)
        #  - Callable → The function is evaluated and the value returned.
        v = p
        for prop in self.properies:
            if isinstance(prop, str):
                a = getattr(v, prop)
                if callable(a):
                    v = a()
                else:
                    v = a
            if callable(prop):
                v = prop(v)
        return v

    def _print(self, player):
        value = self.get_value(player)
        return value

class RatingComparison(SimpleComparison):
    def __init__(self, players, name, properties):
        super().__init__(players, name, properties, ascending=False)

    def _print(self, player):
        value = self.get_value(player)
        return ratscale(value)

class EarningsComparison(Comparison):
    def __init__(self, players, name):
        super().__init__(players, name, ascending=False)

    def _get_value(self, player):
        earnings = player.earnings_set.aggregate(
            Sum('earnings')
        )['earnings__sum']

        if earnings is not None:
            return earnings
        else:
            return 0

    def _print(self, player):
        value = self.get_value(player)
        return add_sep_and_cur(value, "USD")

class PercentageComparison(SimpleComparison):
    def __init__(self, players, name, properties=None):
        super().__init__(players, name, properties, ascending=False)

    def _print(self, player):
        value = self.get_value(player)
        return "{}%".format(round(value * 100, 2))

class MatchComparison(Comparison, metaclass=cached_properties):

    appearances = Cached()
    winner_counter = Cached()
    loser_counter = Cached()
    matchpm_counter = Cached()
    gamewin_counter = Cached()
    gamelose_counter = Cached()
    game_counter = Cached()
    gamepm_counter = Cached()

    def __init__(self, players, name, matches=None,
                 kind="matches", pm=False, percent=False):
        super().__init__(players, name, False)

        if matches is None:
            self.matches = Match.objects.filter(
                pla__in=players,
                plb__in=players
            )
        else:
            self.matches = matches
        self.kind = kind
        self.pm = pm
        self.percent = percent
        self._needs_compute = True

    def compute(self):
        if self._needs_compute:
            if self.kind == "matches":
                self._appearances = Counter(x.pla_id for x in self.matches) +\
                                    Counter(x.plb_id for x in self.matches)
                self._winner_counter = Counter(
                    x.get_winner_id() for x in self.matches
                )
                self._loser_counter = self.appearances - self.winner_counter
                self._matchpm_counter = +self._winner_counter
                self._matchpm_counter.subtract(self._loser_counter)
            elif self.kind == "games":
                self._gamelose_counter = Counter()
                self._gamewin_counter = Counter()

                for m in self.matches:
                    wins = {}
                    wins[m.pla_id] = m.sca
                    wins[m.plb_id] = m.scb
                    losses = {}
                    losses[m.plb_id] = m.sca
                    losses[m.pla_id] = m.scb
                    self._gamewin_counter += Counter(wins)
                    self._gamelose_counter += Counter(losses)

                self._game_counter = (
                    self._gamewin_counter + self._gamelose_counter
                )
                self._gamepm_counter = +self._gamewin_counter
                self._gamepm_counter.subtract(self._gamelose_counter)

        self._needs_compute = False
        super().compute()

    def _get_value(self, player):
        if self.kind == "matches" and self.pm:
            return self.matchpm_counter[player.id]
        elif self.kind == "matches" and self.percent:
            if self.appearances[player.id] == 0:
                return 0
            return self.winner_counter[player.id] / self.appearances[player.id]
        elif self.kind == "matches":
            return self.winner_counter[player.id]
        elif self.kind == "games" and self.pm:
            return self.gamepm_counter[player.id]
        elif self.kind == "games" and self.percent:
            if self.game_counter[player.id] == 0:
                return 0
            return (
                self.gamewin_counter[player.id] / self.game_counter[player.id]
            )
        elif self.kind == "games":
            return self.gamewin_counter[player.id]

    def _print(self, player):
        v = self.get_value(player)
        if self.percent:
            return "{}%".format(round(v * 100, 2))
        else:
            p = "+" if self.pm and v > 0 else ""
            return p + str(v)

class FormComparison(Comparison):

    def __init__(self, players, name):
        super().__init__(players, name, False)
        self.forms = {}

    def winner_to_char(self, player, match):
        if match.sca == match.scb:
            return 'T'
        if match.sca > match.scb and match.pla_id == player.id:
            return 'W'
        if match.sca < match.scb and match.plb_id == player.id:
            return 'W'
        else:
            return 'L'

    def _get_value(self, player):
        if player.id not in self.forms:
            matches = Match.objects.symmetric_filter(pla=player)\
                                   .order_by('-date')
            recent_matches = matches[:min(5, len(matches))]
            self.forms[player.id] = [
                self.winner_to_char(player, m) for m in recent_matches
            ]
        return self.forms[player.id].count('W') / len(self.forms[player.id])

    def _print(self, player):
        return ' '.join(self.forms[player.id])

class PredictionComparison(PercentageComparison, metaclass=cached_properties):
    prediction = Cached()

    def __init__(self, players, name, bo=3, kind="match"):
        super().__init__(players, name)

        self.kind = kind
        self.bo = bo

    def compute(self):
        kwargs = {
            "dbpl": self.players,
            "bos": [self.bo]
        }
        if self.kind == "match":
            cls = MatchPredictionResult
            kwargs.update({
                "s1": 0,
                "s2": 0
            })
        elif self.kind == "dual":
            cls = DualPredictionResult
        elif self.kind == "rr":
            cls = RoundRobinPredictionResult

        self._prediction = cls(**kwargs)

        super().compute()

    def _get_value(self, p):
        if self.kind == "match":
            if p == self.prediction.pla:
                return self.prediction.proba
            else:
                return self.prediction.probb
        else:
            index = [
                x["player"]["id"] for x in self.prediction.table
            ].index(p.id)
            return self.prediction.table[index]["probs"][0]

class MetaComparison(Comparison, metaclass=cached_properties):
    sums = Cached()
    total = Cached()

    def __init__(self, players, name, comparisons):
        super().__init__(players, name, False)

        self.comparisons = comparisons

    def _non_self_comps(self):
        return (comp for comp in self.comparisons
                if comp != self and
                isinstance(comp, Comparison))

    def compute(self):
        self._sums = Counter(
            b for comp in self._non_self_comps()
            for b in comp.best if len(comp.best) == 1
        )
        self._total = len(list(self._non_self_comps()))
        super().compute()

    def _get_value(self, player):
        return self.sums[player]

    def _print(self, player):
        return "{}/{}".format(self.get_value(player), self.total)
