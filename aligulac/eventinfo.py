#!/usr/bin/python
from __future__ import with_statement
import os
import sys
import time
from urllib2 import urlopen, Request

from BeautifulSoup import BeautifulSoup

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "aligulac.settings")

from ratings.models import Match, Player

_user_agent = 'Mozilla/5.0 (X11; Linux x86_64; rv:16.0) Gecko/20100101 Firefox/16.0'
_base_url = 'http://www.sc2charts.net/en/matches/&c1=&c2=&c3=&archiv_page=%i'

def get_url(url):
    try:
        request = Request(url, headers={'User-Agent': _user_agent})
        result = urlopen(request).read()
        result = result.replace("</scr'+'ipt>", '')
        return result
    except:
        return None

def process_soup(soup):
    dates = soup.findAll(lambda t: (u'class', u'recent_date') in t.attrs)
    scores = soup.findAll(lambda t: (u'class', u'recent_score') in t.attrs)
    nm = 0

    for i in range(0,len(dates)):
        url = dates[i].parent['href']
        id = int(dates[i].parent['href'].split('/')[-2])

        if len(scores[i].contents) < 5:
            print '--- Skipped match %i (score missing on overview page)' % id
            continue

        date = '20' + '-'.join(str(dates[i].contents[0]).split('.')[-1::-1])

        try:
            ns = BeautifulSoup(get_url(url))

            q = ns.findAll(lambda t: (u'class', u'match_coverage') in t.attrs)
            setting = q[0].contents[0].strip()

            q = ns.findAll(lambda t: (u'class', u'edb_logo_img') in t.attrs)

            player_a = int(q[0].parent['href'].split('/')[-2].split('-')[0])
            player_b = int(q[1].parent['href'].split('/')[-2].split('-')[0])

        except:
            print '--- Skipped match %i (parsing error)' % id
            continue

        q = ns.findAll(lambda t: (u'class', u'match_score match_score_finished') in t.attrs)
        player_a_score = int(q[0].contents[1].contents[0])
        player_b_score = int(q[0].contents[3].contents[0])

        try:
            pa = Player.objects.get(sc2c_id=player_a)
            pb = Player.objects.get(sc2c_id=player_b)

            m = Match.objects.get(pla=pa, plb=pb, sca=player_a_score, scb=player_b_score, date=date)
            if m.event == '' and m.eventobj == None:
                m.event = setting + ' (SC2C)'
                m.save()
                print '%s: %s %i-%i %s (%i)' % (setting, pa.tag, player_a_score, player_b_score, pb.tag, m.id)
                nm += 1
            else:
                print '--- Skipped match %i (already decorated)' % id


        except:
            print '--- Skipped match %i (players not in local database: %i, %i)' % (id, player_a, player_b)

    return (nm, False)

if __name__ == "__main__":

    soup = BeautifulSoup(get_url(_base_url % 1))

    a = lambda t: (u'width', u'11') in t.attrs
    q = soup.findAll(lambda t: (u'class', u'ps_item') in t.attrs)[-1]
    npages = int(q.contents[0].contents[0])

    num = 0

    for page in range(366,npages+1):
        if page > 1:
            q = get_url(_base_url % page)
            while q == None:
                print 'Could not get page %i, waiting...' % page
                sys.stdout.flush()
                time.sleep(120)
                q = get_url(_base_url % page)
            soup = BeautifulSoup(q)

        print 'Processing page %i of %i' % (page, npages)
        (n,h) = process_soup(soup)
        num += n
        if h:
            break
        time.sleep(4)

    print 'Imported info for %i matches' % num
