from ratings.models import Player
from countries import data
from countries.transformations import cca3_to_ccn, ccn_to_cca2, cn_to_ccn

from django.db.models import Q, F, Sum, Max

def find_player(lst, make=False, soft=False):
    qset = Player.objects.all()
    
    for s in [s.strip() for s in lst if s.strip() != '']:
        # If numeric, assume it's a restriction on ID and nothing else
        if s.isdigit():
            qset = qset.filter(id=int(s))
            continue

        # Always search by player tag, team and aliases
        if soft:
            q = Q(tag__icontains=s) | Q(alias__name__icontains=s) |\
                    Q(teammembership__current=True, teammembership__team__name__icontains=s) |\
                    Q(teammembership__current=True, teammembership__team__alias__name__icontains=s)
        else:
            q = Q(tag__iexact=s) | Q(alias__name__iexact=s) |\
                    Q(teammembership__current=True, teammembership__team__name__iexact=s) |\
                    Q(teammembership__current=True, teammembership__team__alias__name__iexact=s)

        # Race query
        if len(s) == 1 and s.upper() in 'PTZSR':
            q |= Q(race=s.upper())

        # Country codes
        if len(s) == 2 and s.upper() in data.cca2_to_ccn:
            q |= Q(country=s.upper())
        if len(s) == 3 and s.upper() in data.cca3_to_ccn:
            q |= Q(country=ccn_to_cca2(cca3_to_ccn(s.upper())))
        renorm = s[0].upper() + s[1:].lower()
        if renorm in data.cn_to_ccn:
            q |= Q(country=ccn_to_cca2(cn_to_ccn(renorm)))

        qset = qset.filter(q)

    # Make player if needed and allowed
    if not qset.exists() and make:
        tag, country, race = None, None, None

        for s in [s.strip() for s in lst if s.strip() != '']:
            if s.isdigit():
                continue

            if len(s) == 1 and s.upper() in 'PTZSR':
                race = s.upper()
                continue

            if len(s) == 2 and s.upper() in data.cca2_to_ccn:
                country = s.upper()
                continue
            if len(s) == 3 and s.upper() in data.cca3_to_ccn:
                country = ccn_to_cca2(cca3_to_ccn(s.upper()))
                continue
            renorm = s[0].upper() + s[1:].lower()
            if renorm in data.cn_to_ccn:
                country = ccn_to_cca2(cn_to_ccn(renorm))
                continue

            tag = s

        if tag == None:
            raise Exception('Player \'' + ' '.join(lst) + '\' was not found and could not be made'\
                    + ' (missing player tag)')

        if race == None:
            raise Exception('Player \'' + ' '.join(lst) + '\' was not found and could not be made'\
                    + ' (missing race)')

        p = Player()
        p.tag = tag
        p.country = country
        p.race = race
        p.save()

        return Player.objects.filter(id=p.id)

    return qset.distinct()
