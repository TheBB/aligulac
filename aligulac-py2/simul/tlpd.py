#!/usr/bin/python3

from urllib.request import urlopen, Request
import re

class Tlpd:

    _user_agent = 'Mozilla/5.0 (X11; Linux x86_64; rv:16.0) Gecko/20100101'\
            + ' Firefox/16.0'

    _tlpd_tabulator = 'http://www.teamliquid.net/tlpd/{db}'\
            + '/players/detailed-elo'

    _tlpd_url = 'http://www.teamliquid.net/tlpd/tabulator/update.php?'\
            + 'tabulator_id={tabulator}&tabulator_page=1&tabulator_order_col='\
            + 'default&tabulator_search={player}'

    from_file = False

    def __init__(self, db='sc2-korean', tabulator=-1):
        self._tabulator = tabulator
        self._database = db

    def search(self, player):
        if self._tabulator == -1:
            self.get_tabulator_id()

        if not self.from_file:
            if self._tabulator == -1:
                return None

            try:
                url = self._tlpd_url.format(player=player, tabulator=self._tabulator)
                request = Request(url, headers={'User-Agent': self._user_agent})
                result = urlopen(request)
                q = result.read().decode()
            except Exception as e:
                print(' > tlpd.search (request): ' + str(e))
                return None

            with open('testsearch', 'w') as f:
                f.write(q)
        else:
            with open('testsearch', 'r') as f:
                q = f.read()

        out = re.compile('<a title="[^ ]* \([PTZ]\)" ?href="\\/tlpd\\/'\
                + self._database + '\\/players\\/').finditer(q)

        intervals = []
        prev = None
        for match in out:
            if prev != None:
                this = match.span()
                that = prev.span()
                intervals.append(q[that[0]:this[0]])
            prev = match
        this = match.span()
        intervals.append(q[this[0]:])

        results = []
        for plstr in intervals:
            res = dict()

            #print("---------------------------------")
            #print(plstr)
            #print("---------------------------------")

            try:
                temp = re.compile('title="[^ ]* \([PTZ]\)"').findall(plstr)
                #print(temp)
                res['name'] = temp[0][7:-5]
                res['race'] = temp[0][-3:-2]

                temp = re.compile('title="[A-Za-z0-9\\- ]*" href="\\/tlpd\\/'\
                                  + self._database + '\\/teams').findall(plstr)
                #print(temp)
                if len(temp) > 0:
                    temp = re.compile('title="[A-Za-z0-9\\- ]*"').findall(temp[0])
                    res['team'] = temp[0][7:-1]
                else:
                    res['team'] = 'unknown team or retired'

                temp = re.compile('  \d+').findall(plstr)
                #print(temp)
                res['elo'] = int(temp[0][2:])

                temp = re.compile('<span style="color\:#00005D">\d+').findall(plstr)
                #print(temp)
                res['elo_vt'] = int(temp[0][-4:])
                temp = re.compile('<span style="color\:#912A2E">\d+').findall(plstr)
                #print(temp)
                res['elo_vz'] = int(temp[0][-4:])
                temp = re.compile('<span style="color\:#006E2F">\d+').findall(plstr)
                #print(temp)
                res['elo_vp'] = int(temp[0][-4:])
            except IndexError:
                pass
            except Exception as e:
                print(' > tlpd.search (parse): ' + str(e))
            finally:
                if len(res) == 7:
                    results.append(res)

        return results

    def get_tabulator_id(self):
        if self.from_file == False:
            try:
                url = self._tlpd_tabulator.format(db=self._database)
                request = Request(url, headers={'User-Agent': self._user_agent})
                result = urlopen(request)
                q = result.read().decode()
            except Exception as e:
                print(' > tlpd.get_tabulator_id (request): ' + str(e))
                self._tabulator = -1
                return

            with open('testtabulator', 'w') as f:
                f.write(q)
        else:
            with open('testtabulator', 'r') as f:
                q = f.read()

        out = re.compile('tblt_ids\[\'tblt\'\] = \'\d+\';').findall(q)
        if len(out) > 0:
            self._tabulator = int(re.compile('\d+').findall(out[0])[0])
            print('--- Got TLPD tabulator ID: ' + str(self._tabulator))
        else:
            print(' > tlpd.get_tabulator_id (parse)')
            self._tabulator = -1

if __name__ == '__main__':
    tlpd = Tlpd()
    print(tlpd.search('rain'))
