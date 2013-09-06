from simul.formats.match import Match

class Tally:

    def __init__(self, rounds):
        self.finishes = [0] * rounds
        self.win, self.loss = 0.0, 0.0

    def __getitem__(self, key):
        return self.finishes[key]

    def __setitem__(self, key, value):
        self.finishes[key] = value

    def __len__(self):
        return len(self.finishes)

    def __iter__(self):
        return iter(self.finishes)

    def scale(self, scale):
        self.finishes = [f/scale for f in self.finishes]

class TeamPL:

    def __init__(self, num):
        self._num = num

    def set_players(self, players):
        self._pla = players[:len(players)/2]
        self._plb = players[len(players)/2:]
        self._nplayers = len(self._pla)

        self._matches = []
        for i in range(0,self._nplayers):
            m = Match(self._num)
            m.set_players([self._pla[i], self._plb[i]])
            self._matches.append(m)

    def get_match(self, i):
        return self._matches[i]

    def get_tally(self):
        return self._tally

    def compute(self):
        N = 1000
        self._tally = [Tally(self._nplayers+1), Tally(self._nplayers+1)]

        for m in self._matches:
            m.compute()

        for i in range(0,N):
            self.compute_inst(1.0/N)

    def compute_inst(self, base):
        sca, scb = 0, 0
        for m in self._matches:
            inst = m.random_instance_detail(new=True)
            if inst[1] > inst[2]:
                sca += 1
            else:
                scb += 1
        self._tally[0][sca] += base
        self._tally[1][scb] += base
        if sca > scb:
            self._tally[0].win += base
            self._tally[1].loss += base
        else:
            self._tally[1].win += base
            self._tally[0].loss += base
