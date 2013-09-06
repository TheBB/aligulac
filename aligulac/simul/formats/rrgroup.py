import itertools
from operator import attrgetter

from simul.formats.composite import Composite
from simul.formats.match import Match
from simul.formats.format import Tally as ParentTally

from simul import progressbar

def get_ending(s):
    if (s[-1] == '1') and (s[0] != '1' or len(s) == 1):
        return 'st'
    elif (s[-1] == '2') and (s[0] != '1' or len(s) == 1):
        return 'nd'
    elif (s[-1] == '3') and (s[0] != '1' or len(s) == 1):
        return 'rd'
    else:
        return 'th'

class Tally(ParentTally):

    def __init__(self, nplayers, num):
        ParentTally.__init__(self, nplayers)
        self._nplayers = nplayers
        self._num = num

        self.mwins = [0] * nplayers
        self.sscore = [0] * (2*(nplayers-1)*num + 1)
        self.swins = [0] * ((nplayers-1) * num + 1)

    def get_sscore(self, key):
        return self.sscore[key + (self._nplayers - 1) * self._num]

    def add_sscore(self, key, value):
        self.sscore[key + (self._nplayers - 1) * self._num] += value

    def exp_mscore(self):
        exp = 0
        for i in range(0,len(self.mwins)):
            exp += i * self.mwins[i]

        return (exp, self._nplayers-1-exp)

    def exp_sscore(self):
        scr = 0
        for i in range(0,len(self.sscore)):
            scr += (i-(self._nplayers-1)*self._num) * self.sscore[i]
        
        wins = 0
        for i in range(0,len(self.swins)):
            wins += i * self.swins[i]

        return (wins, wins - scr)

class RRGroup(Composite):

    def __init__(self, nplayers, num, tie, threshold=1, subgroups=None):
        self._num = num
        self._tie = tie
        self._threshold = threshold

        schema_in = [nplayers]
        schema_out = [1] * nplayers
        Composite.__init__(self, schema_in, schema_out)

        if subgroups != None:
            self._original = False
            self._subgroups = subgroups
        else:
            self._original = True
            self._subgroups = dict()

    def setup(self):
        nmatches = len(self._schema_out) * (len(self._schema_out) - 1) // 2
        self._matches = []

        for r in range(0, nmatches):
            m = Match(self._num)
            self._matches.append(m)

            m.add_parent(self)

    def players_to_id(self, pa, pb):
        i = min(pa.num, pb.num)
        j = max(pa.num, pb.num)

        return int(round(i*(len(self._schema_out) - float(i+3)/2))) + j - 1

    def get_match(self, key):
        ex = 'No such match found \'' + str(key) + '\''

        if type(key) == int:
            return self._matches[key]

        key = key.lower().split(' ')
        if len(key) < 2:
            raise Exception(ex)

        fits_a = lambda m: (m.get_player(0).name.lower() == key[0] and\
                            m.get_player(1).name.lower() == key[1])
        fits_b = lambda m: (m.get_player(1).name.lower() == key[0] and\
                            m.get_player(0).name.lower() == key[1])
        fits = lambda m: fits_a(m) or fits_b(m)
        gen = (m for m in self._matches if fits(m))

        try:
            return next(gen)
        except:
            raise Exception(ex)
    
    def should_use_mc(self):
        np = len(self._schema_out)
        return (2*self._num)**(np*(np-1)/2) > 2e5

    def tally_maker(self):
        return Tally(len(self._schema_out), self._num)

    def fill(self):
        for i in range(0,len(self._players)):
            if self._players[i].flag == -1:
                self._players[i].flag = 1 << i
            self._players[i].num = i

        m = 0
        for pair in itertools.combinations(self._players, 2):
            self._matches[m].set_players(list(pair))
            m += 1

    def compute_mc(self, N=3000):
        for m in self._matches:
            m.compute()

        total = 0
        for i in range(0,N):
            instances = [m.random_instance_detail(new=True) for m in self._matches]
            if self.compute_instances(instances, float(1)/N):
                total += float(1)/N

        for t in self._tally.values():
            t.scale(total)

    def compute_exact(self):
        for m in self._matches:
            m.compute()

        gens = [m.instances_detail() for m in self._matches]
        total = 0
        for instances in itertools.product(*gens):
            base = 1
            for inst in instances:
                base *= inst[0]
            if self.compute_instances(instances, base):
                total += base

        for t in self._tally.values():
            t.scale(total)

    def compute_instances(self, instances, base):
        table = self.compute_table(instances, base)
        if table != False:
            self.table = table
            for i in range(0,len(table)):
                tally = self._tally[table[i]]
                for (shift, prob) in table[i].temp_spread:
                    tally[len(table)-i-1-shift] += prob * base

        for p in self._players:
            self._tally[p].mwins[p.temp_mscore] += base
            self._tally[p].add_sscore(p.temp_sscore, base)
            self._tally[p].swins[p.temp_swins] += base

        if table != False:
            return True
        else:
            return False

    def compute_table(self, instances, prob=1):
        for p in self._players:
            p.temp_mscore = 0
            p.temp_sscore = 0
            p.temp_swins = 0
            p.temp_spread = [(0,1)]

        for inst in instances:
            if inst[3] == None:
                print(inst)
            inst[3].temp_mscore += 1
            inst[3].temp_sscore += inst[5] - inst[6]
            inst[4].temp_sscore += inst[6] - inst[5]
            inst[3].temp_swins += inst[5]
            inst[4].temp_swins += inst[6]

        return self.break_ties(list(self._players), self._tie, instances)

    def break_ties(self, table, tie, instances):
        if tie[0] == 'imscore' or tie[0] == 'isscore' or tie[0] == 'iswins':
            for p in table:
                p.temp_imscore = 0
                p.temp_isscore = 0
                p.temp_iswins = 0

            combs = itertools.combinations(table, 2)
            for comb in combs:
                id = self.players_to_id(comb[0], comb[1])
                inst = instances[id]
                inst[3].temp_imscore += 1
                inst[3].temp_isscore += inst[5] - inst[6]
                inst[4].temp_isscore += inst[6] - inst[5]
                inst[3].temp_iswins += inst[5]
                inst[4].temp_iswins += inst[6]

        if tie[0] == 'mscore' or tie[0] == 'sscore' or tie[0] == 'swins'\
        or tie[0] == 'imscore' or tie[0] == 'isscore' or tie[0] == 'iswins':
            key = attrgetter('temp_' + tie[0])
            table = sorted(table, key=key, reverse=True)

            keyval = key(table[0])
            keyind = 0
            for i in range(1, len(table)):
                if key(table[i]) != keyval:
                    if i > keyind + 1:
                        temp = self.break_ties(table[keyind:i], tie, instances)
                        if temp != False:
                            table[keyind:i] = temp
                        else:
                            return False
                    keyval = key(table[i])
                    keyind = i

            if keyind < len(table) - 1 and keyind > 0:
                temp = self.break_ties(table[keyind:], tie, instances)
                if temp != False:
                    table[keyind:] = temp
                else:
                    return False
            elif keyind < len(table) - 1:
                table = self.break_ties(table, tie[1:], instances)
                if table == False:
                    return False

        if tie[0] == 'ireplay':
            if len(table) == len(self._players) and self._saved_tally == None:
                return False

            if len(table) != len(self._players):
                subgroup_id = sum([p.flag for p in table])

                if not subgroup_id in self._subgroups:
                    newplayers = []
                    for p in table:
                        newplayers.append(p.copy())
                    subgroup = RRGroup(len(table), self._num, self._tie,\
                                      subgroups=self._subgroups)
                    self._subgroups[subgroup_id] = subgroup
                    subgroup.set_players(newplayers)
                    subgroup.force_ex = self.force_ex
                    subgroup.force_mc = self.force_mc
                    subgroup.compute()
                else:
                    subgroup = self._subgroups[subgroup_id]

            root = 0
            for p in table:
                p.temp_spread = []
                if len(table) != len(self._players):
                    ref = next(iter(filter(lambda q: q.flag == p.flag, subgroup._players)))
                    reftally = subgroup.get_tally()[ref]
                else:
                    reftally = self._saved_tally[p]
                for f in range(0,len(reftally)):
                    p.temp_spread.append((root+f, reftally[f]))
                root -= 1

        return table

    def detail(self, strings):
        tally = self._tally
        nplayers = len(self._schema_out)

        out = strings['detailheader']

        out += strings['ptabletitle'].format(title='Detailed placement probabilities')
        out += strings['ptableheader']
        for h in range(len(self._schema_out), 0, -1):
            heading = str(h)
            heading += get_ending(heading)
            out += strings['ptableheading'].format(heading=heading)

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

        out += strings['ptabletitle'].format(title='Match score')
        out += strings['ptableheader']
        for h in range(0, nplayers):
            out += strings['ptableheading'].format(heading=str(h) + '-' +\
                                                  str(nplayers-h-1))

        for p in self._players:
            if p.name == 'BYE':
                continue
            out += '\n' + strings['ptablename'].format(player=p.name)
            for i in tally[p].mwins:
                if i > 1e-10:
                    out += strings['ptableentry'].format(prob=100*i)
                else:
                    out += strings['ptableempty']

        out += strings['ptablebetween']

        out += strings['ptabletitle'].format(title='Set score')
        out += strings['ptableheader']
        for h in range(-(nplayers-1)*self._num, (nplayers-1)*self._num+1):
            out += strings['ptableheading'].format(heading=str(h))

        for p in self._players:
            if p.name == 'BYE':
                continue
            out += '\n' + strings['ptablename'].format(player=p.name)
            for i in tally[p].sscore:
                if i > 1e-10:
                    out += strings['ptableentry'].format(prob=100*i)
                else:
                    out += strings['ptableempty']

        out += strings['detailfooter']

        return out

    def summary(self, strings, title=None):
        if title == None:
            title = str(len(self._players)) + '-player round robin'
        out = strings['header'].format(title=title)

        nm = len(self._schema_out) - 1
        players = sorted(self._players, key=lambda p:\
                         sum(self._tally[p][-self._threshold:])*100, reverse=True)

        for p in players:
            if p.name == 'BYE':
                continue
            t = self._tally[p]
            out += strings['gplayer'].format(player=p.name)

            (mw, ml) = t.exp_mscore()
            (sw, sl) = t.exp_sscore()
            out += strings['gpexpscore'].format(mw=mw, ml=ml, sw=sw, sl=sl)

            if self._threshold == 1:
                out += strings['gpprobwin'].format(prob=t.finishes[-1]*100)
            else:
                out += strings['gpprobthr'].format(prob=sum(\
                        t.finishes[-self._threshold:])*100,\
                        thr=self._threshold)

            place = str(len(self._schema_out)-t.finishes.index(max(t.finishes)))
            place += get_ending(place)
            out += strings['gpmlplace'].format(place=place,\
                    prob=max(t.finishes)*100)

        out += strings['nomimage']
        out += strings['footer'].format(title=title)

        return out
