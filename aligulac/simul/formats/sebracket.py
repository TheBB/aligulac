import itertools

from formats.composite import Composite
from formats.match import Match
from formats.format import Tally as ParentTally

import progressbar

class Tally(ParentTally):

    def __init__(self, rounds, players):
        ParentTally.__init__(self, rounds)
        self.eliminators = dict()
        for p in players:
            self.eliminators[p] = 0

class SEBracket(Composite):

    def __init__(self, num):
        self._num = num
        
        schema_in = [1] * 2**len(num)
        schema_out = []
        r = len(num) - 1
        while r >= 0:
            schema_out.append(2**r)
            r -= 1
        schema_out.append(1)
        Composite.__init__(self, schema_in, schema_out)

    def setup(self):
        self._matches = dict()
        self._bracket = []

        prev_round = None
        this_round = []

        for r in range(0, len(self._num)):
            for i in range(0, 2**(len(self._num)-1-r)):
                m = Match(self._num[r])
                this_round.append(m)

                m.add_parent(self)
                if prev_round != None:
                    prev_round[2*i].add_winner_link(m, 0)
                    prev_round[2*i+1].add_winner_link(m, 1)

            self._matches['Round ' + str(r+1)] = this_round
            self._bracket.append(this_round)
            prev_round = this_round
            this_round = []

    def get_match(self, key):
        ex = 'No such match found \'' + key + '\''

        key = key.split(' ')[0].split('-')
        if len(key) < 2:
            raise Exception(ex)

        try:
            return self._bracket[int(key[0])-1][int(key[1])-1]
        except:
            raise Exception(ex)

    def should_use_mc(self):
        return len(self._num) > 4

    def fill(self):
        for i in range(0,len(self._players)):
            self._bracket[0][i//2].set_player(i % 2, self._players[i])

    def tally_maker(self):
        return Tally(len(self._schema_out), self._players)

    def compute_mc(self, N=50000):
        for m in self._bracket[0]:
            m.compute_partial()

        progress = progressbar.ProgressBar(N, exp='Monte Carlo')
        for i in range(0,N):
            self.compute_mc_round(0, 1/N)

            if i % 500 == 0:
                progress.update_time(i)
                print(progress.dyn_str())

        progress.update_time(N)
        print(progress.dyn_str())
        print('')

    def compute_mc_round(self, r, base=1):
        num = len(self._bracket[r])

        if r > 0:
            for m in self._bracket[r]:
                m.compute_partial()

        instances = [m.random_instance(new=True) for m in self._bracket[r]]
        self.compute_instances(instances, r, base)

        if num > 1:
            self.compute_mc_round(r+1, base)
        else:
            self._tally[instances[0][1][1]][r+1] += base

    def compute_exact(self):
        self.compute_round(0)

    def compute_round(self, r, base=1):
        num = len(self._bracket[r])

        for m in self._bracket[r]:
            m.compute_partial()

        gens = [m.instances() for m in self._bracket[r]]
        for instances in itertools.product(*gens):
            prob = base
            for inst in instances:
                prob *= inst[0]

            self.compute_instances(instances, r, prob)

            if num > 1:
                self.compute_round(r+1, prob)
            else:
                self._tally[instances[0][1][1]][r+1] += prob

    def compute_instances(self, instances, r, base):
        for inst in instances:
            inst[2].broadcast_instance(inst)
            self._tally[inst[1][0]][r] += base
            self._tally[inst[1][0]].eliminators[inst[1][1]] += base

    def detail(self, strings):
        tally = self._tally

        out = strings['detailheader']

        out += strings['ptabletitle'].format(title='Detailed placement probabilities')
        out += strings['ptableheader']
        for h in range(len(self._num), -1, -1):
            if h > 0:
                out += strings['ptableheading'].format(heading='Top ' + str(2**h))
            else:
                out += strings['ptableheading'].format(heading='Win')

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

        out += strings['ptabletitle'].format(title='Most likely to be eliminated by...')
        for p in self._players:
            if p.name == 'BYE':
                continue
            out += '\n' + strings['ptablename'].format(player=p.name)
            elims = sorted(self._players, key=lambda a: tally[p].eliminators[a],\
                           reverse=True)
            for elim in elims[:3]:
                if tally[p].eliminators[elim] > 1e-10:
                    out += strings['ptabletextnum'].format(text=elim.name,\
                               prob=100*tally[p].eliminators[elim])

        out += strings['detailfooter']

        return out
    
    def summary(self, strings, title=None):
        tally = self._tally

        if title == None:
            title = str(2**len(self._num)) + '-man single elimination bracket'
        out = strings['header'].format(title=title)

        players = sorted(self._players, key=lambda a: tally[a][-1],\
                         reverse=True)

        out += strings['mlwinnerlist']
        for p in players[0:16]:
            if tally[p][-1] > 1e-10 and p.name != 'BYE':
                out += strings['mlwinneri'].format(player=p.name,\
                                                   prob=100*tally[p][-1])

        def exp_rounds(k):
            ret = 0
            for i in range(0,len(k)):
                ret += i*k[i]
            return ret

        players = sorted(self._players, key=lambda a: exp_rounds(tally[a]), 
                         reverse=True)

        expls = ['win', 'lose in the finals', 'lose in the semifinals',\
                 'lose in the quarterfinals']
        out += strings['exroundslist']
        for p in players:
            if p.name == 'BYE':
                continue
            exp = exp_rounds(tally[p])
            rounded = len(self._num) - round(exp)
            if rounded < 4:
                expl = expls[rounded]
            else:
                expl = 'lose in the round of ' + str(2 << rounded -1)

            out += strings['exroundsi'].format(player=p.name, rounds=exp,\
                                               expl=expl)

        out += strings['nomimage']
        out += strings['footer']

        return out
