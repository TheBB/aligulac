=================
incf.countryutils
=================

`incf.countryutils` provides a convenience API on top of
a list of countries by continent (data_file) as found on Wikipedia_
(a copy is included in the distribution).

It supports transformations between the different types of country
codes and names like in:

 >>> from incf.countryutils import transformations
 >>> transformations.cca2_to_ccn('de')
 '276'
 >>> transformations.ccn_to_cn(276)
 'Germany'

Country codes supported are *numeric* (`ccn`; internal reference format),
*two letter country codes* (`cca2`), and *three letter country codes* (`cca3`).
In addition, `incf.countryutils` knows the *simple English name* of each
country (`cn`) as well as the *official English name*. 

Transformation names follow the pattern `<f1>_to_<f2>` where `f1` and `f2`
refer to country codes or names. All transformations to and from the reference
format (`ccn`) are provided.

When providing a numeric country code as an argument integer as well as
string representations are accepted.

Moreover, there are some combined transformations available for convenience.
Most notably this is <any country code>_to_<simple or official name>:

 >>> transformations.cc_to_cn('FR')
 'France'
 >>> transformations.cc_to_cn('FRa')
 'France'
 >>> transformations.cc_to_cn('250')
 'France'
 >>> transformations.cc_to_cn(250)
 'France'
 >>> transformations.cc_to_con(250)
 'French Republic France'

Lookup by name is only supported for the simple English name:

 >>> transformations.cn_to_ccn('Italy')
 '380'
 >>> transformations.ccn_to_con('380')
 'Italian Republic Italy'


Continents
==========

Based on the data from Wikipedia_ `incf.countryutils` allows looking 
up the continent a country belongs to (`ctn`: continent name; 
`ctca2`: two letter continent code):

 >>> transformations.cn_to_ctn('Italy')
 'Europe'
 >>> transformations.cca_to_ctn('us')
 'North America'

Continents have two letter codes as well like in:

 >>> transformations.cca_to_ctca2('usa')
 'NA'

Given a continent, one can obtain its constituent countries:

 >>> transformations.ctca2_to_ccn('AN')
 ['010', '074', '260', '334', '239']


Alternative API (OO)
====================

There is an alternative, more object-oriented API based on the
notion of `Country` and `Continent` types. On creation, a country 
or continent needs to be passed a name or code:

 >>> from incf.countryutils.datatypes import Country
 >>> china = Country('China')
 >>> china
 <incf.countryutils.datatypes.Country object at 0x...>

The country's names and codes are available as attributes:

 >>> china.name
 'China'
 >>> china.official_name
 "People's Republic of China"
 >>> china.numeric
 '156'
 >>> china.alpha2
 'CN'
 >>> china.alpha3
 'CHN'

and the `continent` property refers to a corresponding `Continent` 
instance:

 >>> china.continent
 <incf.countryutils.datatypes.Continent object at 0x...>

which in turn has the following attributes:

 >>> china.continent.name
 'Asia'
 >>> china.continent.alpha2
 'AS'

Asking a continent for its constituent countries returns
a generator object returning country instances in turn:

 >>> china.continent.countries
 <generator object at 0x...>
 >>> china.continent.countries.next()
 <incf.countryutils.datatypes.Country object at 0x...>
 >>> [c.name for c in china.continent.countries]
 ['Afghanistan', 'Armenia', 'Azerbaijan', 'Bahrain', ...]



Related packages
================

The use case driving the development of this package has been the
wish to be able to get at a continent given a country where the 
country can be specified in any ISO 3166 compliant way. 

There is also pycountry_ which handles also regional subdivision,
currency, and language. It may also gain the capabilities provided
here but note that pycountry_ requires lxml_ which may not always
be readily available on some platforms. 

Finally, for those interested in looking up countries by IP address
there is ip2cc_. 



.. _Wikipedia: http://en.wikipedia.org/wiki/List_of_countries_by_continent_(data_file)
.. _pycountry: http://pypi.python.org/pypi/pycountry

.. _lxml: http://pypi.python.org/pypi/lxml

.. _ip2cc: http://pypi.python.org/pypi/ip2cc
