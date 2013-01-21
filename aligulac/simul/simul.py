#!/usr/bin/python

import argparse
import pickle
import sys
import os

try:
    import pyreadline as readline
except ImportError:
    import readline

import playerlist
import output
import tlpd
import glicko
import ali
import imager
import pyperclip

from formats import match, mslgroup, sebracket, debracket, rrgroup,\
        combination, ipl5

class Completer:
    def __init__(self, basewords):
        self.basewords = words
        self.words = words
        self.prefix = None

    def add_words(self, words):
        self.words = self.basewords + words

    def complete(self, prefix, index):
        if prefix != self.prefix:
            self.matching_words = [w for w in self.words if w.startswith(prefix)]
            self.prefix = prefix
        try:
            return self.matching_words[index]
        except IndexError:
            return None

def swipe_history():
    readline.remove_history_item(readline.get_current_history_length()-1)

def better_input(query, swipe=False):
    ret = input(query)
    if (swipe or ret.strip() == '') and ret != '':
        swipe_history()
    return ret

def get_from_file(file):
    try:
        with open(file, 'rb') as f:
            ret = pickle.load(f)
        return ret
    except Exception as e:
        print(' > simul.get_from_file: ' + str(e))
        return None

def put_to_file(obj, file):
    try:
        with open(file, 'wb') as f:
            pickle.dump(obj, f)
    except Exception as e:
        print(' > simul.put_to_file: ' + str(e))

def print_matches(list, pre='Modified matches', post='none'):
    sys.stdout.write(pre + ':')
    found = False
    for match in list:
        if match.is_modified():
            if found:
                sys.stdout.write(',')
            found = True
            sys.stdout.write(' ' + match.get_player(0).name + ' ' +\
                             str(match._result[0]) + '-' +\
                             str(match._result[1]) + ' ' +\
                             match.get_player(1).name)
    if found:
        print('')
    else:
        print(' ' + post)

def perf_eval(p, ot, ct):
    def cumsum(a):
        for i in range(1,len(a)):
            a[i] += a[i-1]
        return a
    def dot(a,b):
        ret = 0
        for i in range(0,len(a)):
            ret += a[i] * b[i]
        return ret
    bad = dot(cumsum(list(ot)), ct)
    good = dot(cumsum(list(ot)[-1::-1])[-1::-1], ct)
    return strings['perf'].format(name=p.name, bprob=100*bad, gprob=100*good)

def sanity_check(args):
    for n in args['num']:
        if n < 1:
            print('Number of sets to win must be at least 1')
            sys.exit(1)

    if args['type'] == 'rrgroup':
        if len(args['tie']) < 2:
            print('Must have at least two tiebreakers')
            sys.exit(1)
        if args['tie'][-1] != 'ireplay':
            print('Last tiebreaker must be ireplay')
            sys.exit(1)
        if args['tie'][0] == 'ireplay':
            print('First tiebreaker must not be ireplay')
            sys.exit(1)
        if args['players'] < 2:
            print('Must have at least two players')
            sys.exit(1)
        if args['threshold'] < 1:
            print('Threshold must be at least 1')
            sys.exit(1)

    if args['rounds'] < 2 and args['type'] == 'debracket':
        print('Must have at least two rounds')
        sys.exit(1)

def loop_image(obj):
    try:
        obj.image = imager.imgur_upload(imager.make_match_image(obj))
    except Exception as e:
        print(str(e))

def loop_find_match(obj, key):
    try:
        if type(obj) not in [match.Match] and len(s) > 1:
            m = obj.get_match(' '.join(key))
        elif type(obj) in [match.Match] and len(s):
            m = obj
        else:
            return None

        if m == False:
            print('Not enough arguments')
            return None

        return m

    except Exception as e:
        print(str(e))
        return None

if __name__ == '__main__':

    sys.path.append(os.getcwd())

    valid_formats = ['term','tl','tls','reddit']

    parser = argparse.ArgumentParser(description='Emulate a SC2 tournament'\
            + ' format.')
    parser.add_argument('-f', '--format', dest='format', default='term',\
            choices=valid_formats,\
            help='output format')
    parser.add_argument('-t', '--type', dest='type', default='match',\
            choices=['match','sebracket','rrgroup','mslgroup','debracket',\
                    'ipl5', 'combo'],\
            help='tournament type')
    parser.add_argument('--title', dest='title', default=None,\
            help='title')
    parser.add_argument('--tie', dest='tie', nargs='*',\
            choices=['mscore', 'sscore', 'swins', 'imscore', 'isscore', 'iswins',\
                     'ireplay'],\
            default=['mscore', 'sscore', 'imscore', 'isscore', 'ireplay'],\
            help='order of tiebreaks in a round robin group')
    parser.add_argument('-r', '--rounds', dest='rounds', default=2, type=int,\
            help='number of rounds in a bracket')
    parser.add_argument('-n', '--num', dest='num', nargs='+', default=[2], type=int,\
            help='number of sets required to win a match')
    parser.add_argument('-p', '--players', dest='players', default=4, type=int,\
            help='number of players in a group')
    parser.add_argument('--threshold', dest='threshold', default=1, type=int,\
            help='placement threshold in a group')
    parser.add_argument('-i', '--input', dest='input', default=None,\
            help='save and load data from file')
    parser.add_argument('--spec', dest='spec', default=None,\
            help='file for combination specs')
    parser.add_argument('--tlpd', dest='tlpd', default='none',\
            help='search in TLPD database')
    parser.add_argument('--tlpd-tabulator', dest='tabulator', default=-1, type=int,\
            help='tabulator ID for the TLPD database')
    parser.add_argument('--glicko', dest='glicko', action='store_true',\
            help='search in SC2Charts database')
    parser.add_argument('--ali', dest='ali', action='store_true',\
            help='search in Aligulac database')
    parser.add_argument('-nc', '--no-console', dest='noconsole', action='store_true',\
            help='skip the console')
    parser.add_argument('-ex', '--exact', dest='exact', action='store_true',\
            help='force exact computation')
    parser.add_argument('-mc', '--monte-carlo', dest='mc', action='store_true',\
            help='force monte carlo computation')
    parser.add_argument('--glicko-update', dest='glicko-update', action='store_true',\
            help='update local glicko database')
    parser.add_argument('--debug', dest='debug', action='store_true',\
            help='skip player entry')

    args = vars(parser.parse_args())
    sanity_check(args)

    if args['glicko-update']:
        glicko.update()
        sys.exit(0)

    if args['debug']:
        playerlist.debug = True

    finder = None
    if args['ali']:
        finder = ali.search
    elif args['glicko']:
        finder = glicko.search
    elif args['tlpd'] != 'none':
        iface = tlpd.Tlpd(args['tlpd'], args['tabulator'])
        finder = iface.search

    obj = None
    loaded = False
    if args['input'] != None and os.path.isfile(args['input']):
        obj = get_from_file(args['input'])
        loaded = True
    elif args['type'] == 'match':
        players = playerlist.PlayerList(2, finder)
        obj = match.Match(args['num'][0])
    elif args['type'] == 'sebracket':
        players = playerlist.PlayerList(2**len(args['num']), finder)
        obj = sebracket.SEBracket(args['num'])
    elif args['type'] == 'debracket':
        players = playerlist.PlayerList(pow(2,args['rounds']), finder)
        obj = debracket.DEBracket(args['num'][0], args['rounds'])
    elif args['type'] == 'mslgroup':
        players = playerlist.PlayerList(4, finder)
        obj = mslgroup.MSLGroup(args['num'][0])
    elif args['type'] == 'rrgroup':
        players = playerlist.PlayerList(args['players'], finder)
        obj = rrgroup.RRGroup(args['players'], args['num'][0], args['tie'],\
                              threshold=args['threshold'])
    elif args['type'] == 'combo':
        obj = combination.Combination(args['spec'])
    elif args['type'] == 'ipl5':
        players = playerlist.PlayerList(72, finder)
        obj = ipl5.IPL5Bracket()

    obj.force_ex = args['exact']
    obj.force_mc = args['mc']

    strings = output.get_strings(args['format'], type(obj))

    if not loaded:
        obj.set_players(players.players)
        obj.compute(override=True)
        obj.save_tally()

    out = obj.summary(strings, title=args['title'])
    pyperclip.copy(out)
    print(out)

    if not args['noconsole']:
        composite_commands = ['set','unset','list','detail','mout','mimage',\
                             'mcopy','detailcopy','perf']
        supported = {'all': ['save','load','compute','out','exit','change',\
                             'copy'],
                     match.Match: ['set','unset','list','image'],\
                     mslgroup.MSLGroup: composite_commands,\
                     sebracket.SEBracket: composite_commands,\
                     debracket.DEBracket: composite_commands,\
                     rrgroup.RRGroup: composite_commands,\
                     combination.Combination: composite_commands,\
                     ipl5.IPL5Bracket: composite_commands}

        words = supported['all'] + supported[type(obj)] + ['name','race','elo']
        completer = Completer(words)
        completer.add_words([p.name for p in obj.get_players()])
        readline.parse_and_bind("tab: complete")
        readline.set_completer(completer.complete)

        while True:
            s = better_input('> ').lower().split(' ')
            s = filter(lambda p: p != '', s)
            s = list(map(lambda p: p.strip(), s))
            if len(s) < 1:
                continue

            if s[0] not in supported['all'] and s[0] not in supported[type(obj)]:
                print('Invalid command for type \'' + str(type(obj)) + '\'')
                continue

            if s[0] == 'exit':
                break

            elif s[0] == 'compute':
                if len(s) > 1:
                    try:
                        obj.compute(N=int(s[1]), override=True)
                    except:
                        obj.compute(override=True)
                else:
                    obj.compute(override=True)

            elif s[0] == 'image' or s[0] == 'mimage':
                if s[0] == 'mimage':
                    m = loop_find_match(obj, s[1:])
                else:
                    m = obj

                if m == None:
                    continue

                if not m.is_updated():
                    m.compute()
                loop_image(m)

            elif s[0] in ['out','mout','detail','copy','mcopy','detailcopy']:
                if s[0] in ['mout','mcopy']:
                    m = loop_find_match(obj, s[1:])
                else:
                    m = obj

                if m == None:
                    continue

                if not m.is_updated() and type(m) not in [match.Match]:
                    print('Changes have been made - run \'compute\' to update')
                    continue
                elif not m.is_updated():
                    m.compute()

                if s[-1] in valid_formats:
                    strs = output.get_strings(s[-1], type=type(m))
                else:
                    strs = output.get_strings(args['format'], type=type(m))

                if s[0] in ['out','mout','copy','mcopy']:
                    out = m.summary(strs, title=args['title'])
                else:
                    out = m.detail(strs)

                if s[0] in ['copy','mcopy','detailcopy']:
                    pyperclip.copy(out)
                if s[0] in ['out','mout','detail']:
                    print(out)

            elif s[0] in ['perf']:
                if len(s) < 2:
                    print('Not enough arguments')
                    continue

                player = obj.get_player(s[1])
                otally = obj.get_original_tally()[player]
                ctally = obj.get_tally()[player]
                print(perf_eval(player, otally, ctally))

            elif s[0] == 'save':
                if len(s) > 1:
                    put_to_file(obj, s[1])
                elif args['input'] != None:
                    put_to_file(obj, args['input'])
                else:
                    print('No filename given')

            elif s[0] == 'load':
                temp = None
                if len(s) > 1:
                    temp = get_from_file(s[1])
                elif args['input'] != None:
                    temp = get_from_file(args['input'])
                else:
                    print('No filename given')
                
                if temp != None:
                    obj = temp
                    strings = output.get_strings(args['format'], type(obj))

            elif s[0] == 'set' or s[0] == 'unset':
                m = loop_find_match(obj, s[1:])

                if m == None:
                    continue

                if not m.can_modify():
                    print('Match not yet ready (unresolved dependencies?)')
                    continue

                if s[0] == 'set':
                    ia = int(better_input('Score for ' + m.get_player(0).name\
                                          + ': ', swipe=True))
                    ib = int(better_input('Score for ' + m.get_player(1).name\
                                          + ': ', swipe=True))
                    res = m.modify(ia, ib)
                    if not res:
                        print('Unable to modify match')
                elif s[0] == 'unset':
                    m.clear()

            elif s[0] == 'list':
                if type(obj) in [match.Match]:
                    matches = [obj]
                else:
                    matches = obj.get_matches()

                if type(matches) == list:
                    print_matches(matches)
                elif type(matches) == dict:
                    for key in matches.keys():
                        print_matches(matches[key], pre=key)

            elif s[0] == 'change':
                pass
                if len(s) < 2:
                    print('Not enough arguments')
                    continue

                player = obj.get_player(s[-1])
                if player == None:
                    print('No such player \'' + s[-1] + '\'')

                recompute = False

                if len(s) < 3 or s[1] == 'name':
                    player.name = better_input('Name: ')
                    completer.add_words([p.name for p in obj.get_players()])

                if len(s) < 3 or s[1] == 'race':
                    race = ''
                    while race not in ['P', 'Z', 'T']:
                        race = better_input('Race: ', swipe=True).upper()
                    player.race = race
                    recompute = True

                if len(s) < 3 or s[1] == 'elo':
                    elo = playerlist.get_elo()
                    if elo == False:
                        player.elo = 0
                        player.elo_race['T'] = 0
                        player.elo_race['Z'] = 0
                        player.elo_race['P'] = 0
                    else:
                        player.elo = elo
                        player.elo_race['T'] = playerlist.get_elo('vT')
                        player.elo_race['Z'] = playerlist.get_elo('vZ')
                        player.elo_race['P'] = playerlist.get_elo('vP')
                    recompute = True

                if recompute:
                    obj.notify()

    if args['input'] != None:
        put_to_file(obj, args['input'])
