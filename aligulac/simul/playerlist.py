from math import sqrt

from ratings.models import Rating, Player
from ratings.tools import cdf

debug = False

def make_player(player):
    if player is None:
        pl = Player('BYE', 'T', -10000, 0, 0, 0)
        pl.dbpl = None
        return pl

    rats = Rating.objects.filter(player=player).order_by('-period__id')
    if rats.count() == 0:
        pl = Player(player.tag, player.race, 0.0, 0.0, 0.0, 0.0, 0.6, 0.6, 0.6, 0.6)
        pl.dbpl = player
    else:
        rat = rats[0]
        pl = Player(player.tag, player.race, rat.rating, rat.rating_vp, rat.rating_vt, rat.rating_vz,\
                    rat.dev, rat.dev_vp, rat.dev_vt, rat.dev_vz)
        pl.dbpl = player

    return pl

class Player:

    def __init__(self, name='', race='', elo=0, elo_vp=0, elo_vt=0, elo_vz=0,\
                 dev=0.6, dev_vp=0.6, dev_vt=0.6, dev_vz=0.6, copy=None):
        if copy == None:
            self.name = name
            self.race = race
            self.elo = elo
            self.elo_race = {'P': elo_vp, 'T': elo_vt, 'Z': elo_vz}
            self.dev = dev
            self.dev_race = {'P': dev_vp, 'T': dev_vt, 'Z': dev_vz}
            self.flag = -1
        else:
            self.name = copy.name
            self.race = copy.race
            self.elo = copy.elo
            self.elo_race = copy.elo_race
            self.dev = copy.dev
            self.dev_race = copy.dev_race
            self.flag = copy.flag

    def elo_vs_opponent(self, opponent):
        if opponent.race in 'PTZ':
            return self.elo + self.elo_race[opponent.race]
        else:
            return self.elo

    def dev_vs_opponent(self, opponent):
        if opponent.race in 'PTZ':
            return self.dev**2 + self.dev_race[opponent.race]**2
        else:
            return self.dev**2 + sum([d**2 for d in self.dev_race.values()])/9

    def prob_of_winning(self, opponent):
        my_elo = self.elo_vs_opponent(opponent)
        op_elo = opponent.elo_vs_opponent(self)
        my_dev = self.dev_vs_opponent(opponent)
        op_dev = opponent.dev_vs_opponent(self)
        return cdf(my_elo - op_elo, scale=sqrt(1+my_dev+op_dev))

    def copy(self):
        return Player(copy=self)
