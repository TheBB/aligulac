from ratings.models import Player

from formats.match import Match
from formats.playerlist import PlayerList

def dev(request):
    pla = Player.objects.get(id=11)
    plb = Player.objects.get(id=1)
    plist = PlayerList([pla, plb])

    obj = match.Match(5)
    obj.set_players(plist)
    obj.compute()

    return HttpResponse('Predict dev. %s vs %s' % (pla.tag, plb.tag))
