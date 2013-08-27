# naming convention (on top of ISO 3166)
# 
# cca2 : two letter country code
# cca3 : three letter country code
# ccn  : numeric country code
# cn   : country name (simple, English)
# con  : official country name
# ctn  : continent name (simple, English)
# ctca2: two letter continent code


# manually defined converters

# two letter continent code to continent name (simple, English)
ctca2_to_ctn = {
    'AF':'Africa',
    'AS':'Asia',
    'EU':'Europe',
    'NA':'North America',
    'SA':'South America',
    'OC':'Oceania',
    'AN':'Antarctica',
    }

# continent name (simple, English) to two letter continent code
ctn_to_ctca2 = {
    'Africa':'AF',
    'Asia':'AS',
    'Europe':'EU',
    'North America':'NA',
    'South America':'SA',
    'Oceania':'OC',
    'Antarctica':'AN',
    }

# initialize the rest

ccn_to_cca2  = {} # numeric country code to two letter country code 
ccn_to_cca3  = {} # etc.
ccn_to_cn    = {} 
ccn_to_con   = {} 
cn_to_ccn    = {}
cca3_to_ccn  = {}
cca2_to_ccn  = {}
ccn_to_ctca2 = {}

ctca2_to_ccn = {'AN':[],
                'AF':[],
                'AS':[],
                'EU':[],
                'NA':[],
                'SA':[],
                'OC':[],
                }

mappings = [('ctca2_to_ctn', ctca2_to_ctn),
            ('ctn_to_ctca2', ctn_to_ctca2),
            ('ccn_to_cca2', ccn_to_cca2),
            ('ccn_to_cca3', ccn_to_cca3),
            ('ccn_to_cn',ccn_to_cn),
            ('ccn_to_con',ccn_to_con),
            ('cn_to_ccn',cn_to_ccn),
            ('cca3_to_ccn',cca3_to_ccn),
            ('cca2_to_ccn',cca2_to_ccn),
            ('ccn_to_ctca2',ccn_to_ctca2),
            ('ctca2_to_ccn',ctca2_to_ccn),
            ]


# generate from the raw data
# source: http://en.wikipedia.org/wiki/List_of_countries_by_continent_(data_file)
raw = file('raw_data.txt','r')

for token in raw.readlines():
    ctca2, cca2, cca3, ccn, fullname = token.split(None,4)

    if ',' in fullname:
        cn,prefix = fullname.split(',')
        con = ' '.join([prefix.strip(),cn])
    else:
        cn = con = fullname.strip()

    # now populate the dicts

    ccn_to_cca2[ccn] = cca2
    ccn_to_cca3[ccn] = cca3
    ccn_to_cn[ccn] = cn
    ccn_to_con[ccn] = con
    cn_to_ccn[cn] = ccn
    cca3_to_ccn[cca3] = ccn 
    cca2_to_ccn[cca2] = ccn
    ccn_to_ctca2[ccn] = ctca2
    ctca2_to_ccn[ctca2].append(ccn)

raw.close()

# dump output to file

import pprint
data = open('data.py','w')

for id, mapping in mappings:
    data.write("%s = %s\n\n" % (id, pprint.pformat(mapping,4)) )

data.close()
