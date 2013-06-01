# -*- coding: utf-8 -*-
from django import template
from datetime import timedelta, date
from dateutil.relativedelta import relativedelta
import md5
from aligulac import settings

from math import sqrt

register = template.Library()

# ----------------
# Tools for converting URLs
# ----------------

def css(value):
    if not settings.DEBUG:
        return 'http://css.aligulac.com/' + value + '.css'
    else:
        return '/css/' + value + '.css'
register.filter('css', css)

def js(value):
    if not settings.DEBUG:
        return 'http://js.aligulac.com/' + value + '.js'
    else:
        return '/js/' + value + '.js'
register.filter('js', js)

def static(value):
    return 'http://static.aligulac.com/' + value
register.filter('static', static)

def imgfolder(value, arg=''):
    if arg != '':
        return str(arg) + '/' + str(value) + '.png'
    else:
        return str(value) + '.png'
register.filter('imgfolder', imgfolder)

def urlfilter(value):
    value = value.replace(' ', '-')
    value = value.replace('/', '')
    return value
register.filter('urlfilter', urlfilter)

# ----------------
# Tools for scaling rating numbers
# ----------------

def ratscale(value):
    return int(round((float(value) + 1.0)*1000))
register.filter('ratscale', ratscale)

def ratscaled(value):
    return int(round(float(value)*1000))
register.filter('ratscaled', ratscaled)

def addf(value, arg):
    return float(value) + float(arg)
register.filter('addf', addf)

def racefull(value):
    return ['Protoss','Terran','Zerg','Random','Race switcher'][['P','T','Z','R','S'].index(value)]
register.filter('racefull', racefull)

# ----------------
# Calculating percentages
# ----------------

# Percentage of VALUE to VALUE+ARG
def pctg(value, arg):
    if float(value) + float(arg) > 0:
        return int(round(100*float(value)/(float(value)+float(arg))))
    else:
        return 0
register.filter('pctg', pctg)

# Percentage of VALUE to 1
def pctg2(value):
    return '%5.2f' % (100*float(value))
register.filter('pctg2', pctg2)

# Percentage of VALUE to ARG
def pctg3(value, arg):
    if float(arg) > 0:
        return '%.2f' % (100*float(value)/float(arg))
    else:
        return '%.2f' % 0.0
register.filter('pctg3', pctg3)

# ----------------
# Tools for OP and UP races
# ----------------

def oprace(value):
    if value.dom_p > value.dom_t and value.dom_p > value.dom_z:
        return 'P'
    elif value.dom_t > value.dom_p and value.dom_t > value.dom_z:
        return 'T'
    else:
        return 'Z'
register.filter('oprace', oprace)

def uprace(value):
    if value.dom_p < value.dom_t and value.dom_p < value.dom_z:
        return 'P'
    elif value.dom_t < value.dom_p and value.dom_t < value.dom_z:
        return 'T'
    else:
        return 'Z'
register.filter('uprace', uprace)

def oppctg(value):
    return int(round(100*(max([value.dom_p, value.dom_t, value.dom_z]) - 1.)))
register.filter('oppctg', oppctg)

def uppctg(value):
    return int(round(100*(1. - min([value.dom_p, value.dom_t, value.dom_z]))))
register.filter('uppctg', uppctg)

# ----------------
# Date tools for the results
# ----------------

def tomorrow(value):
    return value + timedelta(1)
register.filter('tomorrow', tomorrow)

def yesterday(value):
    return value - timedelta(1)
register.filter('yesterday', yesterday)

def nextmonth(value):
    return value + relativedelta(months=1)
register.filter('nextmonth', nextmonth)

def prevmonth(value):
    return value - relativedelta(months=1)
register.filter('prevmonth', prevmonth)

def datemax(value, arg):
    if value - arg > timedelta(0):
        return value
    else:
        return arg
register.filter('datemax', datemax)

def datemin(value, arg):
    if value - arg < timedelta(0):
        return value
    else:
        return arg
register.filter('datemin', datemin)

# ----------------
# Used for the events
# ----------------

def unfold(value):
    value = -int(value)
    q = ''
    for i in range(0,value):
        q += '</div>'
    return q
register.filter('unfold', unfold)

def indent(value):
    if int(value) < 1:
        return ''
    q = ''
    for i in range(0,int(value)):
        q += '&nbsp;&nbsp;&nbsp;&nbsp;'
    return q
register.filter('indent', indent)

def eventchildren(value):
    return value.event_set.order_by('lft')
register.filter('eventchildren', eventchildren)

def getN(lst):
    N = 1
    K = 60
    while N < len(lst) and sum([2+len(x.name) for x in lst[-N-1::]]) < K:
        N += 1
    return N 

def eventliststart(value, N=None):
    if N == None:
        N = getN(list(value))
    return list(value)[0:-N]
register.filter('eventliststart', eventliststart)

def eventlistend(value, N=None):
    if N == None:
        N = getN(list(value))
    return list(value)[-N:]
register.filter('eventlistend', eventlistend)

# ----------------
# Miscellaneous
# ----------------

# Prins a floating point number between 0 and 1 as a percentage
# TODO: Basically identical to pctg2. Fix this?
def prob(value):
    return '%6.2f' % (100*value)
register.filter('prob', prob)

# Checks whether a team has a logo file
def haslogo(value):
    try:
        with open('/usr/local/www/media/al/teams/%i.png' % int(value)) as f:
            return True
    except:
        return False
register.filter('haslogo', haslogo)

# Subtraction of integers
def sub(value, arg):
    return int(value) - int(arg)
register.filter('sub', sub)

# Used for getting confidence intervals
def devrange(value, arg):
    r = value.dev**2
    if arg == 'P':
        return sqrt(r + value.dev_vp**2)
    elif arg == 'T':
        return sqrt(r + value.dev_vt**2)
    elif arg == 'Z':
        return sqrt(r + value.dev_vz**2)
register.filter('devrange', devrange)

# Create a link to match prediction from a more complex format
def makematchlink(value):
    return "/predict/match/?bo=%i&amp;ps=%i%%2C%i&amp;s1=%i&amp;s2=%i" % \
            (2*value._num-1, value.get_player(0).dbpl.id, value.get_player(1).dbpl.id,\
             value._result[0], value._result[1])
register.filter('makematchlink', makematchlink)

# Exponentiation of integers
def pow(value, arg):
    return int(value)**int(arg)
register.filter('pow', pow)

# Used for printing javascript code for charts
def milliseconds(value):
    return (value - date(1970,1,1)).days * 24 * 60 * 60 * 1000
register.filter('milliseconds', milliseconds)

# Used for prizemoney
def add_separator(int):
    string = str(int)
    newstring = ''
    
    while True:
        if len(string) <= 3:
            newstring = string + newstring
            return newstring
        else:
            newstring = ',' + string[-3:] + newstring
            string = string[:-3]
register.filter('add_separator', add_separator)

def add_sep_and_cur(int, cur):
    str = add_separator(int)
    if not cur:
        return "$" + str    
    elif cur == "USD":
        return "$" + str
    elif cur == "EUR":
        return "€" + str
    elif cur == "KRW":
        return "₩" + str
    elif cur == "SEK" or cur == "NOK":
        return str + " kr"
    elif cur == "DKK":
        return str + " kr."
    elif cur == "GBP":
        return "£" + str
    elif cur == "AUD":
        return "A$" + str
    elif cur == "CNY":
        return "¥" + str
    elif cur == "TWD":
        return "NT$" + str
    elif cur == "PLN":
        return str + " zł"
    elif cur == "ZAR":
        return "R " + str
    else:
        return str + " " + cur
register.filter('add_sep_and_cur', add_sep_and_cur)

#{% if bool|is_false %} returns True if bool is False; False if bool is None.
#{% if not bool %} returns True in both cases. 
def is_false(bool):
    return bool is False
register.filter('is_false', is_false)

# Produces a small string hash
def smallhash(value):
    m = md5.new()
    m.update(value)
    return m.hexdigest()[:6]
register.filter('smallhash', smallhash)
