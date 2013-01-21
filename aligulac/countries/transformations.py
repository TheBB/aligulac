# various converters between country codes and names
# including the possibility to look up the continent
# a country belongs to.
#
# source: ISO 3166 and
# http://en.wikipedia.org/wiki/List_of_countries_by_continent_(data_file)

import data

import types

def ccn_to_ccn(code):
    """Normalize the numeric country code

    Accepts integer and string types as input
    Returns a three digit string of the numeric code
    """
    if not isinstance(code,types.StringTypes):
        code = str(code)
    while len(code) < 3:
        code = '0' + code
    return code

def ccn_to_cca2(code):
    """Given an ISO 3166 numeric country code return the corresponding
    two letter country code.
    
    The code passed in can be of string, unicode or integer type.
    
    Raises KeyError if code does not exist.
    """
    
    return data.ccn_to_cca2[ccn_to_ccn(code)]

def ccn_to_cca3(code):
    """Given an ISO 3166 numeric country code return the corresponding
    three letter country code.
    
    The code passed in can be of string, unicode or integer type.
    
    Raises KeyError if code does not exist.
    """
    
    return data.ccn_to_cca3[ccn_to_ccn(code)]

def ccn_to_cn(code):
    """Given an ISO 3166 numeric country code return the corresponding
    simple English name of the country.
    
    The code passed in can be of string, unicode or integer type.
    
    Raises KeyError if code does not exist.
    """
    
    return data.ccn_to_cn[ccn_to_ccn(code)]

def ccn_to_con(code):
    """Given an ISO 3166 numeric country code return the corresponding
    official English name of the country.
    
    The code passed in can be of string, unicode or integer type.
    
    Raises KeyError if code does not exist.
    """
    
    return data.ccn_to_con[ccn_to_ccn(code)]

def cn_to_ccn(code):
    """Given the simple English name of the country return the
    corresponding ISO 3166 numeric country code.
    
    The code passed in can be of string or unicode type.
    
    Raises KeyError if code does not exist.
    """    
    return data.cn_to_ccn[code]

def cca2_to_ccn(code):
    """Given the ISO 3166 two letter country code of the country 
    return the corresponding numeric country code.
    
    The code passed in can be of string or unicode type.
    
    Raises KeyError if code does not exist.
    """    
    return data.cca2_to_ccn[code.upper()]

def cca3_to_ccn(code):
    """Given the ISO 3166 three letter country code of the country 
    return the corresponding numeric country code.
    
    The code passed in can be of string or unicode type.
    
    Raises KeyError if code does not exist.
    """    
    return data.cca3_to_ccn[code.upper()]

def ccn_to_ctca2(code):
    """Given an ISO 3166 numeric country code return the corresponding
    two letter continent code according to 
    http://en.wikipedia.org/wiki/List_of_countries_by_continent_(data_file).
    
    The code passed in can be of string, unicode or integer type.
    
    Raises KeyError if code does not exist.
    """

    return data.ccn_to_ctca2[ccn_to_ccn(code)]

def ctca2_to_ccn(code):
    """Given a two letter continent code return the corresponding
    list of numeric country codes according to 
    http://en.wikipedia.org/wiki/List_of_countries_by_continent_(data_file).
    
    The code passed in can be of string or unicode type.
    
    Raises KeyError if code does not exist.
    """

    return data.ctca2_to_ccn[code]

# combined trafos

def ccn_to_ctn(code):
    """Given an ISO 3166 numeric country code return the corresponding
    continent name according to 
    http://en.wikipedia.org/wiki/List_of_countries_by_continent_(data_file).
    
    The code passed in can be of string, unicode or integer type.
    
    Raises KeyError if code does not exist.
    """

    ctca2 = data.ccn_to_ctca2[ccn_to_ccn(code)]
    return data.ctca2_to_ctn[ctca2]


def cca_to_ccn(code):
    """Given the ISO 3166 two or three letter country code of the 
    country return the corresponding numeric country code.
    
    The code passed in can be of string or unicode type.
    
    Raises KeyError if code does not exist.
    """
    if len(code) == 2:
        return cca2_to_ccn(code)
    elif len(code) == 3:
        return cca3_to_ccn(code)
    else:
        raise KeyError, code

def cca_to_cn(code):
    """Given the ISO 3166 two or three letter country code of the 
    country return the simple English name of the country.
    
    The code passed in can be of string or unicode type.
    
    Raises KeyError if code does not exist.
    """
    return ccn_to_cn(cca_to_ccn(code))

def cc_to_ccn(code):
    """Given the ISO 3166 numeric or two or three letter country code 
    of the country return the numeric code.
    
    The code passed in can be of integer, string, or unicode type.
    
    Raises KeyError if code does not exist.
    """
    try:
        return cca_to_ccn(code)
    except (KeyError, TypeError):
        return ccn_to_ccn(code)

def cc_to_cn(code):
    """Given the ISO 3166 numeric or two or three letter country code 
    of the country return the simple English name of the country.
    
    The code passed in can be of integer, string, or unicode type.
    
    Raises KeyError if code does not exist.
    """
    return ccn_to_cn(cc_to_ccn(code))

def cc_to_con(code):
    """Given the ISO 3166 numeric or two or three letter country code 
    of the country return the official English name of the country.
    
    The code passed in can be of integer, string, or unicode type.
    
    Raises KeyError if code does not exist.
    """
    return ccn_to_con(cc_to_ccn(code))

def cca_to_con(code):
    """Given the ISO 3166 two or three letter country code of the 
    country return the official English name of the country.
    
    The code passed in can be of string or unicode type.
    
    Raises KeyError if code does not exist.
    """
    return ccn_to_con(cca_to_ccn(code))


def cca_to_ctn(code):
    """Given the ISO 3166 two or three letter country code of the 
    country return the corresponding continent name.
    
    The code passed in can be of string or unicode type.

    Raises KeyError if code does not exist.
    """
    return ccn_to_ctn(cca_to_ccn(code))

def cca_to_ctca2(code):
    """Given the ISO 3166 two or three letter country code of the 
    country return the corresponding two letter continent code
    
    The code passed in can be of string or unicode type
    
    Raises KeyError if code does not exist
    """
    return ccn_to_ctca2(cca_to_ccn(code))

def cn_to_ctca2(code):
    """Given the simple English name of a country return the 
    corresponding two letter continent code.
    
    The name passed in can be of string or unicode type.
    
    Raises KeyError if code does not exist.
    """
    return ccn_to_ctca2(cn_to_ccn(code))

def cn_to_ctn(code):
    """Given the simple English name of a country return the 
    English name of the corresponding continent.
    
    The name passed in can be of string or unicode type.
    
    Raises KeyError if code does not exist.
    """
    return ccn_to_ctn(cn_to_ccn(code))
