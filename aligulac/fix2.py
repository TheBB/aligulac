#!/usr/bin/python
import os
from urllib2 import urlopen, Request

from BeautifulSoup import BeautifulSoup

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "aligulac.settings")

db = 'sc2-korean'
tabulator = 11951
pages = 350
_user_agent = 'Mozilla/5.0 (X11; Linux x86_64; rv:16.0) Gecko/20100101 Firefox/16.0'
get_tbl_url = 'http://www.teamliquid.net/tlpd/{db}/games'
page_url = 'http://www.teamliquid.net/tlpd/tabulator/update.php?tabulator_id={tabulator}&'\
        + 'tabulator_page={page}&tabulator_order_col=1&tabulator_search='

def get_url(url):
    request = Request(url, headers={'User-Agent': _user_agent})
    result = urlopen(request).read()
    return result

if tabulator == None:
    s = get_url(get_tbl_url.format(db=db))
    soup = BeautifulSoup(get_url(get_tbl_url.format(db=db)))
    temp = soup.findAll(lambda t: (u'title', u'Next page') in t.attrs)[-1]
    tabulator = int(temp['onclick'].split(',')[1])
    print 'Tabulator: ', tabulator

for pagenum in range(1, pages+1):
    s = get_url(page_url.format(page=pagenum, tabulator=tabulator))
    print page_url.format(page=pagenum, tabulator=tabulator)

    soup = BeautifulSoup(s)
    table = soup.findAll(lambda t: (u'id', u'tblt_table') in t.attrs)[0]

    for r in range(3, len(table.contents), 4):
        row = table.contents[r]

        mid = int(row.contents[1].contents[1]['href'].split('/')[-1].split('_')[0])

        date = '20' + row.contents[3].contents[0].strip()
        event = row.contents[5].contents[1].contents[0].strip()

        rca = row.contents[9].contents[2]['title'][-2]
        pla = row.contents[9].contents[2].contents[0].strip()
        ida = int(row.contents[9].contents[2]['href'].split('/')[-1].split('_')[0])

        rcb = row.contents[11].contents[2]['title'][-2]
        plb = row.contents[11].contents[2].contents[0].strip()
        idb = int(row.contents[11].contents[2]['href'].split('/')[-1].split('_')[0])
        
        with open('tlpd_out', 'a') as f:
            f.write(','.join(['"'+str(p)+'"' for p in [mid, date, event, pla, rca, ida, plb, rcb, idb]]))
            f.write('\n')
