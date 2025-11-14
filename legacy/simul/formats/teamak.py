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

class TeamAK:

    def __init__(self, num):
        self._num = num

    def set_players(self, players):
        self._pla = players[0]
        self._plb = players[1]

    def compute(self):
        N = 100
        self._tally = [Tally(2), Tally(2)]
        for i in range(0,N):
            self.compute_match(self._pla, self._plb, 1.0/N)

    def compute_match(self, pla, plb, base):
        obj = Match(self._num)
        obj.set_players([pla[0], plb[0]])
        obj.compute()
        inst = obj.random_instance_detail(new=True)

        if inst[1] > inst[2]:
            plb = plb[1:]
        else:
            pla = pla[1:]

        if len(plb) != 0 and len(pla) != 0:
            self.compute_match(pla, plb, base)
        elif len(plb) == 0:
            self._tally[0][1] += base
            self._tally[1][0] += base
        else:
            self._tally[1][1] += base
            self._tally[0][0] += base
