import itertools

from formats.composite import Composite
from formats.match import Match
from formats.format import Tally as ParentTally

class Tally(ParentTally):

    def __init__(self, rounds, players):
        ParentTally.__init__(self, rounds)
        self.pairs = dict()
        for p in players:
            self.pairs[p] = 0

class MSLGroup(Composite):
    
    def __init__(self, num):
        self._num = num
        Composite.__init__(self, [1]*4, [1]*4)

    def setup(self):
        self._first = [Match(self._num), Match(self._num)]
        self._second = [Match(self._num), Match(self._num)]
        self._final = Match(self._num)

        self._matches = self._first + self._second + [self._final]

        self._first[0].add_winner_link(self._second[0], 0)
        self._first[0].add_loser_link(self._second[1], 0)
        self._first[0].add_parent(self)
        self._first[1].add_winner_link(self._second[0], 1)
        self._first[1].add_loser_link(self._second[1], 1)
        self._first[1].add_parent(self)
        self._second[0].add_loser_link(self._final, 0)
        self._second[0].add_parent(self)
        self._second[1].add_winner_link(self._final, 1)
        self._second[1].add_parent(self)
        self._final.add_parent(self)

    def get_match(self, key):
        key = key.split(' ')[0]
        if key.lower() == 'first':
            return self._first[0]
        elif key.lower() == 'second':
            return self._first[1]
        elif key.lower() == 'winners':
            return self._second[0]
        elif key.lower() == 'losers':
            return self._second[1]
        elif key.lower() == 'final':
            return self._final
        else:
            raise Exception('No such match found \'' + key + '\'')

    def should_use_mc(self):
        return False

    def fill(self):
        self._first[0].set_players(self._players[:2])
        self._first[1].set_players(self._players[2:])

    def tally_maker(self):
        return Tally(len(self._schema_out), self._players)

    def compute_mc(self):
        self.compute_exact()

    def compute_exact(self):
        for m in self._first:
            m.compute_partial()

        for (if0, if1) in itertools.product(self._first[0].instances(),\
                                            self._first[1].instances()):
            base_f = if0[0] * if1[0]
            if0[2].broadcast_instance(if0)
            if1[2].broadcast_instance(if1)
            for m in self._second:
                m.compute_partial()

            for (is0, is1) in itertools.product(self._second[0].instances(),\
                                                self._second[1].instances()):
                base_s = base_f * is0[0] * is1[0]
                is0[2].broadcast_instance(is0)
                is1[2].broadcast_instance(is1)
                self._final.compute_partial()

                for ifin in self._final.instances():
                    prob = base_s * ifin[0]
                    self._tally[is1[1][0]][0] += prob
                    self._tally[ifin[1][0]][1] += prob
                    self._tally[ifin[1][1]][2] += prob
                    self._tally[is0[1][1]][3] += prob
                    self._tally[is0[1][1]].pairs[ifin[1][1]] += prob

    def detail(self, strings):
        tally = self._tally

        out = strings['detailheader']

        out += strings['ptabletitle'].format(title='Detailed placement probabilities')
        out += strings['ptableheader']
        for h in ['4th', '3rd', '2nd', '1st']:
            out += strings['ptableheading'].format(heading=h)

        for p in self._players:
            if p.name == 'BYE':
                continue
            out += '\n' + strings['ptablename'].format(player=p.name)
            for i in tally[p]:
                if i > 1e-10:
                    out += strings['ptableentry'].format(prob=100*i)
                else:
                    out += strings['ptableempty']

        out += strings['ptablebetween']

        out += strings['ptabletitle'].format(title='Probability of each pair advancing')
        out += strings['ptableheader']
        for p in self._players:
            if p.name != 'BYE':
                out += strings['ptableheading'].format(heading=p.name[:7])
        for p in self._players:
            if p.name == 'BYE':
                continue
            out += '\n' + strings['ptablename'].format(player=p.name)
            for q in self._players:
                if q.name == 'BYE':
                    continue
                if p != q and tally[p].pairs[q] >= 1e-10:
                    out += strings['ptableentry'].format(prob=100*tally[p].pairs[q])
                else:
                    out += strings['ptableempty']

        out += strings['detailfooter']

        return out

    def summary(self, strings, title=None):
        tally = self._tally

        if title == None:
            title = 'MSL-style four-player group'
        out = strings['header'].format(title=title)

        players = sorted(self._players, key=lambda a: sum(tally[a][2:]),\
                         reverse=True)

        for p in players:
            if sum(tally[p][2:]) > 1e-10 and p.name != 'BYE':
                out += strings['mslgplayer'].format(player=p.name,\
                                                    prob=100*sum(tally[p][2:]))

        out += strings['nomimage']
        out += strings['footer'].format(title=title)

        return out
