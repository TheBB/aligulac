from math import sqrt

from aligulac.settings import (
    INIT_DEV,
)
from aligulac.tools import etn

from ratings.models import (
    Player,
    Rating, 
    start_rating,
)
from ratings.tools import (
    cdf,
    get_latest_period
)

debug = False

def make_player(player):
    if player is None:
        pl = Player('BYE', 'T', -10000, 0, 0, 0)
        pl.dbpl = None
        return pl

    try:
        rating = player.current_rating
        pl = Player(
            player.tag,
            player.race,
            rating.rating, rating.rating_vp, rating.rating_vt, rating.rating_vz,
            rating.dev, rating.dev_vp, rating.dev_vt, rating.dev_vz,
        )
    except:
        pl = Player(
            player.tag,
            player.race,
            start_rating(player.country, etn(lambda: get_latest_period().id) or 1), 0.0, 0.0, 0.0,
            INIT_DEV, INIT_DEV, INIT_DEV, INIT_DEV,
        )

    pl.dbpl = player

    return pl

class Player:

    def __init__(self, name='', race='', elo=0, elo_vp=0, elo_vt=0, elo_vz=0,
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

    def __str__(self):
        return self.name

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
