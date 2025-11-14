from incf.countryutils import data
from incf.countryutils import transformations as trafos

class Country(object):
    """encapsulating information about a country
    
    The constructor needs to be passed in an ISO 3166 numeric, two or 
    three letter country code or the simple English name.

    Raises ValueError if no corresponding country can be found
    """

    def __init__(self, key):
        """Infer the country from the key
        
        Valid keys are: two letter, three letter or numeric country code
        acording to ISO 3166 or the countries simple English name.

        Raises ValueError if key is not found.
        """

        if data.cn_to_ccn.has_key(key):
            self.cn = self.name = key
            self.ccn = self.numeric = data.cn_to_ccn[key]
        else:
            try:
                code = trafos.cc_to_ccn(key)
            except KeyError:
                raise ValueError, "%s is o ISO country code or name" % key
            self.ccn = self.numeric = code
            self.cn = self.name = trafos.ccn_to_cn(self.ccn)

        self.cca2 = self.alpha2 = trafos.ccn_to_cca2(self.numeric)
        self.cca3 = self.alpha3 = trafos.ccn_to_cca3(self.numeric)
        self.con = self.official_name = trafos.ccn_to_con(self.numeric)
        
        self.ctca2 = trafos.ccn_to_ctca2(self.numeric)
        self.ctn = trafos.ccn_to_ctn(self.numeric)

    @property 
    def continent(self):
        return Continent(self.ctn)


class Continent(object):
    """encapsulating information about a continent
    
    The constructor needs to be passed a two letter continent code
    or name ('AF': 'Africa', 'AN': 'Antarctica', 'AS': 'Asia',
    'EU': 'Europe', 'NA': 'North America', 'OC': 'Oceania',
    'SA': 'South America').

    Raises ValueError if no corresponding continent can be found
    """

    def __init__(self, key):
        """Infer the country from the key"""
        if data.ctca2_to_ctn.has_key(key):
            self.ctca2 = self.alpha2 = key
            self.ctn = self.name = data.ctca2_to_ctn[key]
        elif data.ctn_to_ctca2.has_key(key):
            self.ctn = self.name = key
            self.ctca2 = self.alpha2 = data.ctn_to_ctca2[key]
        else:
            raise ValueError, "%s is not a continent code or name" % key

    @property
    def countries(self):
        return (Country(c) for c in data.ctca2_to_ccn[self.alpha2]) 
