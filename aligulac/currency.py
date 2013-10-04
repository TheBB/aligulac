import datetime
import json
import urllib
from aligulac import settings

#Class adapted from https://bitbucket.org/alquimista/currency

class ExchangeRates(object):

    def __init__(self, date):
        self._date = date
        self._data = self._loadjson(date)

    def _loadjson(self, date):
        date = self._date.strftime('%Y-%m-%d')
        url = 'http://openexchangerates.org/api/historical/' + date + '.json?app_id=' + settings.EXCHANGE_ID
        try:
            jsonfile = urllib.request.urlopen(url)
        except urllib.error.HTTPerror as err:
            #API limit reached for the month or other error
            return False
        return json.loads(jsonfile.read().decode())

    def _tobase(self, amount, currency):
        return amount * float(self.rates[currency])

    @property
    def rates(self):
        return self._data['rates']

    def convert(self, amount, currencyfrom, currencyto='USD'):
        usd = self._tobase(amount, currencyto.upper())
        return usd / float(self.rates[currencyfrom.upper()])
