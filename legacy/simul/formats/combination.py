import json
import sys

from formats.composite import Composite
from formats.rrgroup import RRGroup
from formats.sebracket import SEBracket

class Round:
    pass

class SchemaTally:
    pass

class Combination(Composite):

    def __init__(self, specfile):
        try:
            with open(specfile, 'r') as f:
                if not self.parse_spec(json.loads(f.read())):
                    sys.exit(0)
        except Exception as e:
            print(e)
            sys.exit(0)
        Composite.__init__(self, [1, 1], [1, 1])

    def parse_spec(self, spec):
        self._title = spec['title']

        rounds = dict()
        for rnd_name in spec['rounds']:
            rounds[rnd_name] = self.parse_round_spec(spec['rounds'][rnd_name])

        if not self.validate_feeds(rounds):
            return False

        return True

    def validate_feeds(self, rounds):
        schemas = dict()
        for rnd in rounds.values():
            dups = len(rnd.blobs)

            tally = SchemaTally()
            tally.sch_in = []
            tally.sch_out = []
            for k in range(0,dups):
                tally.sch_in.append(list(rnd.single_schema_in))
                tally.sch_out.append(list(rnd.single_schema_out))

            if len(rnd.feed) != len(rnd.single_schema_out):
                print('Round \'' + rnd_name + '\': expected ' +\
                      str(len(rnd.single_schema_out)) + ' feed rules, but found '\
                      + str(len(rnd.feed)))
                return False

        for rnd in rounds.values():
            for feed in rnd.feed:
                print(feed)

        return True

    def parse_round_spec(self, spec):
        rnd = Round()
        rnd.blobs = []

        if 'duplicates' in spec:
            dups = spec['duplicates']
        else:
            dups = 1

        if spec['type'] == 'rrgroup':
            for i in range(0,dups):
                rnd.blobs.append(RRGroup(spec['players'], spec['num'], spec['tie']))
        elif spec['type'] == 'sebracket':
            for i in range(0,dups):
                rnd.blobs.append(SEBracket(spec['num']))

        rnd.single_schema_in = rnd.blobs[0].schema_in()
        rnd.schema_in = [dups*s for s in rnd.blobs[0].schema_in()]
        rnd.single_schema_out = rnd.blobs[0].schema_out()
        rnd.schema_out = [dups*s for s in rnd.blobs[0].schema_out()]

        rnd.feed = spec['feed']

        return rnd
