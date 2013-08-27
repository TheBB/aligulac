#!/usr/bin/python3

from urllib2 import urlopen, Request
import json

_url = 'http://aligulac.com/api/search/?q={player}'
_user_agent = 'Mozilla/5.0 (X11; Linux x86_64; rv:16.0) Gecko/20100101 Firefox/16.0'

def search(player):
    url = _url.format(player=player)
    request = Request(url, headers={'User-Agent': _user_agent})
    result = json.loads(urlopen(request).read().decode())

    ret = []
    for r in result:
        t = dict()
        t['name'] = r['tag']
        t['race'] = r['race']
        if 'country' in r and r['country'] != '':
            t['team'] = r['country']
        else:
            t['team'] = 'unknown'
        t['elo'] = float(r['rating'])
        t['elo_vp'] = float(r['rating_vp'])
        t['elo_vt'] = float(r['rating_vt'])
        t['elo_vz'] = float(r['rating_vz'])
        t['dev'] = float(r['dev'])
        t['dev_vp'] = float(r['dev_vp'])
        t['dev_vt'] = float(r['dev_vt'])
        t['dev_vz'] = float(r['dev_vz'])
        ret.append(t)

    return ret

if __name__ == '__main__':
    print(search('sen'))
