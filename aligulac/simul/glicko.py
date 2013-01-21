#!/usr/bin/python3

import sqlite3
import atexit
import bs4
from bs4 import BeautifulSoup
from urllib.request import urlopen, Request

import progressbar

_user_agent = 'Mozilla/5.0 (X11; Linux x86_64; rv:16.0) Gecko/20100101 Firefox/16.0'
_from_file = False
_elo_factor = 40

db = sqlite3.connect('glicko.sql')
cur = db.cursor()

def close():
    cur.close()

atexit.register(close)

def _get_url(url):
    try:
        request = Request(url, headers={'User-Agent': _user_agent})
        result = urlopen(request)
        return result.read().decode()
    except Exception as e:
        print(' > glicko.update (request): ' + str(e))
        return None

def _next_nonstring(tag):
    while type(tag) == bs4.element.NavigableString:
        tag = tag.next_sibling
    return tag

def search(player):
    res = cur.execute('SELECT name, race, country, rating FROM players WHERE ' +\
                      'name LIKE \'%' + player + '%\'')
    results = []
    for row in res:
        elo = row[3]/_elo_factor
        results.append({'name': row[0], 'race': row[1], 'team': row[2],\
                        'elo': elo, 'elo_vt': elo, 'elo_vz': elo, 'elo_vp': elo})

    return results

def update():
    try:
        cur.execute('DROP TABLE players')
    except:
        pass

    cur.execute('''CREATE TABLE players (name text, race text, country text,
                scountry text, url text, rating integer)''')

    page_url = 'http://www.sc2charts.net/en/edb/ranking/players/&page={number}'

    if not _from_file:
        q = _get_url(page_url.format(number=1))
        if q == None:
            return
        with open('testupdate', 'w') as f:
            f.write(q)
    else:
        with open('testupdate', 'r') as f:
            q = f.read()

    soup = BeautifulSoup(q)
    res = soup.find_all(lambda t: t.name == 'div' and t.has_key('class') and\
                       'ps_item_o' in t['class'])[0].next_sibling
    res = _next_nonstring(res)
    num_pages = int(next(res.children).string)

    progress = progressbar.ProgressBar(num_pages, exp='Updating')
    for page in range(1, num_pages+1):
        if page > 1:
            q = _get_url(page_url.format(number=page))
            if q == None:
                return
            with open('testupdate', 'w') as f:
                f.write(q)
            soup = BeautifulSoup(q)

        progress.update_time(page)
        print(progress.dyn_str())

        res = soup.find_all(lambda t: t.name == 'div' and t.has_key('class') and\
                            'recent_item' in t['class'])
        for r in res[1:]:
            c = _next_nonstring(next(r.children))
            player_url = c['href']

            c = _next_nonstring(next(c.children))
            c = _next_nonstring(c.next_sibling)
            temp = next(c.children)
            if type(temp) != bs4.element.NavigableString:
                player_race = temp['alt'].upper()
                player_name = temp.next_sibling.strip()
            else:
                player_race = '?'
                player_name = temp.strip()

            c = _next_nonstring(c.next_sibling)
            q = next(c.children)
            if type(q) != bs4.element.NavigableString:
                player_scountry = q['alt'].upper()
            else:
                player_scountry = ''
            temp = q.next_sibling
            if temp != None:
                player_country = temp.strip()
            else:
                player_country = 'Unknown'

            c = _next_nonstring(c.next_sibling)
            player_rating = int(_next_nonstring(c.next_sibling).string)

            cur.execute('''INSERT INTO players VALUES (:name, :race, :country,
                        :scountry, :url, :rating)''', 
                        {'name': player_name, 'race': player_race,\
                         'country': player_country,\
                         'scountry': player_scountry, 'url': player_url,\
                         'rating': player_rating})

    progress.update_time(num_pages)
    print(progress.dyn_str())
    print('')

    db.commit()
