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

class Format:

    def __init__(self, schema_in, schema_out):
        self._schema_in = schema_in
        self._schema_out = schema_out
        self._players = [None] * self.num_players()
        self._updated = False
        self._tally = None
        self._saved_tally = None
        self._parents = []
        self._dependencies = []
        self._instance = None
        self.force_mc = False
        self.force_ex = False
        self.image = None

    def add_parent(self, parent):
        self._parents.append(parent)

    def add_dependency(self, dep):
        self._dependencies.append(dep)

    def schema_in(self):
        return self._schema_in

    def schema_out(self):
        return self._schema_out

    def num_players(self):
        return sum(self._schema_in)

    def is_ready(self):
        for p in self._players:
            if p == None:
                return False
        return True

    def is_fixed(self):
        raise NotImplementedError()

    def is_modified(self):
        raise NotImplementedError()

    def is_updated(self):
        return self._updated

    def notify(self):
        self._updated = False
        for p in self._parents:
            p.notify()

    def clear(self):
        raise NotImplementedError()

    def get_tally(self):
        return self._tally

    def get_player(self, key):
        if type(key) == int:
            return self._players[key]
        
        else:
            fits = lambda p: p.name.lower() == key.lower()
            gen = (p for p in self._players if fits(p))
            try:
                return next(gen)
            except:
                return None

    def get_players(self):
        return self._players

    def set_player(self, key, player):
        if self._players[key] != player:
            self._players[key] = player
            self.fill()

    def set_players(self, players):
        if len(players) == len(self._players):
            self._players = players
            self.fill()

    def should_use_mc(self):
        raise NotImplementedError()

    def fill(self):
        raise NotImplementedError()

    def instances(self):
        raise NotImplementedError()

    def random_instance(self, new=False):
        raise NotImplementedError()

    def tally_maker(self):
        return Tally(len(self._schema_out))

    def save_tally(self):
        self._saved_tally = self._tally

    def get_original_tally(self):
        return self._saved_tally

    def compute(self, N=None, override=False):
        if not self.is_ready():
            return

        if self.is_updated() and not override:
            return

        self._tally = dict()
        for p in self._players:
            self._tally[p] = self.tally_maker()

        if self.force_ex:
            self.compute_exact()
        elif self.should_use_mc() or self.force_mc:
            if N == None:
                self.compute_mc()
            else:
                self.compute_mc(N)
        else:
            self.compute_exact()

        self._updated = True

    def compute_mc(self, runs=1000):
        raise NotImplementedError()

    def compute_exact(self):
        raise NotImplementedError()

    def detail(self, strings):
        raise NotImplementedError()

    def summary(self, strings, title=None):
        raise NotImplementedError()
