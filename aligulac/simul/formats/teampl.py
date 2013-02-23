from simul.formats.match import Match

class Tally:

    def __init__(self, rounds):
        self.finishes = [0] * rounds

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
        self._pla = players[0]
        self._plb = players[1]

    def compute(self):
        N = 1000
        self._tally = [Tally(2), Tally(2)]

        self._matches = []
        for i in range(0,7):
            m = Match(self._num)
            m.set_players([self._pla[i], self._plb[i]])
            m.compute()
            self._matches.append(m)

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
        if sca > scb:
            self._tally[0][1] += base
            self._tally[1][0] += base
        else:
            self._tally[1][1] += base
            self._tally[0][0] += base
