import json
import urllib
from aligulac import settings
from datetime import datetime, timedelta
from decimal import Decimal
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

        data = json.loads(jsonfile.read().decode())

        #print(sorted(data['rates'].keys()))

        # ccy use XBT instead
        try:
            data['rates']['XBT'] = data['rates']['BTC']
        except:
            # Bitcoin transfer rates not available at this time.
            pass

        return data

    def _tobase(self, amount, currency):
        return amount * Decimal(self.rates[currency])

    @property
    def rates(self):
        return self._data['rates']

    def convert(self, amount, currencyfrom, currencyto='USD'):
        if currencyfrom not in self.rates:
            self.interpolate(currencyfrom)
        if currencyto not in self.rates:
            self.interpolate(currencyto)

        usd = self._tobase(amount, currencyto.upper())
        return usd / Decimal(self.rates[currencyfrom.upper()])

    def interpolate(self, currency):
        """
        Linearly interpolates the rate for `currency`
        by using the rates closest before and after the
        current date.
        """
        one_day = timedelta(days=1)

        after = self._date + one_day
        nafter = 1
        before = self._date - one_day
        nbefore = 1

        rate_after = None
        rate_before = None

        tries = 0
        while rate_after is None and tries < 20:
            e = ExchangeRates(after)
            if currency in e.rates:
                rate_after = e.rates[currency]
                break
            after += one_day
            nafter += 1
            tries += 1

        tries = 0
        while rate_before is None and tries < 20 and rate_after is not None:
            e = ExchangeRates(before)
            if currency in e.rates:
                rate_before = e.rates[currency]
                break
            before -= one_day
            nbefore += 1
            tries += 1

        if rate_after is None or rate_after is None:
            raise RateNotFoundError(currency, self._date)

        coeff = (rate_after - rate_before) / (nafter + nbefore)
        self.rates[currency] =  rate_before + coeff * nbefore


class RateNotFoundError(Exception):
    def __init__(self, currency, date, *args, **kwargs):
        super().__init__("Exchange rate not found for currency"\
                            " {} on {}".format(currency, date), *args, **kwargs)
