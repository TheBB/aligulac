from django import template
from django.template.defaultfilters import stringfilter
from django.utils.safestring import mark_safe

from datetime import timedelta, date, datetime
from dateutil.relativedelta import relativedelta

import markdown2
import hashlib
from math import sqrt

from aligulac.settings import PRF_NA, PRF_INF, PRF_MININF, DEBUG

register = template.Library()

# {{{ Miscellaneous filters

# {{{ markdown: Filters text written in markdown.
@register.filter
@stringfilter
def markdown(value):
    return mark_safe(markdown2.markdown(value, safe_mode=True))
# }}}

# {{{ addf: Adds floating point numbers.
@register.filter
def addf(value, arg):
    return float(value) + float(arg)
# }}}

# {{{ subf: Subtracts floating point numbers.
@register.filter
def subf(value, arg):
    return float(value) - float(arg)
# }}}

# {{{ sub: Subtracts integers.
@register.filter
def sub(value, arg):
    return int(value) - int(arg)
# }}}

# {{{ Integer exponentiation.
@register.filter
def pow(value, arg):
    return int(value) ** int(arg)
# }}}

# {{{ racefull: Converts a single-character race to human readable format.
@register.filter
def racefull(value):
    return ['Protoss','Terran','Zerg','Random','Race switcher'][['P','T','Z','R','S'].index(value)]
# }}}

# {{{ haslogo: Checks whether a team given by ID has a logo file.
@register.filter
def haslogo(value):
    try:
        with open('/usr/local/www/media/al/teams/%i.png' % int(value)) as f:
            return True
    except:
        return False
# }}}

# {{{ Creates match prediction links.
@register.filter
def makematchlink(value):
    return (
        '/inference/match/?bo=%i&amp;ps=%i%%2C%i&amp;s1=%i&amp;s2=%i' % (
            2*value['sim']._num-1,
            value['pla_id'],
            value['plb_id'],
            value['pla_score'],
            value['plb_score'],
    ))
# }}}

# {{{ milliseconds: Converts a date (not datetime) to millisecond format, needed for using the charts.
@register.filter
def milliseconds(value):
    return (value - date(1970,1,1)).days * 24 * 60 * 60 * 1000
# }}}

# {{{ add_separator: Adds separators to a large number.
@register.filter
def add_separator(value):
    string = str(value)
    newstring = ''
    
    while True:
        if len(string) <= 3:
            newstring = string + newstring
            return newstring
        else:
            newstring = ',' + string[-3:] + newstring
            string = string[:-3]
# }}}

# {{{ add_sep_and_cur: Adds separators and currency symbol to a prize sum.
@register.filter
def add_sep_and_cur(value, cur):
    s = add_separator(value)
    if not cur:
        return "$" + s
    elif cur == "USD":
        return "$" + s
    elif cur == "EUR":
        return "€" + s
    elif cur == "KRW":
        return "₩" + s
    elif cur == "SEK" or cur == "NOK":
        return s + " kr"
    elif cur == "DKK":
        return s + " kr."
    elif cur == "GBP":
        return "£" + s
    elif cur == "AUD":
        return "A$" + s
    elif cur == "CNY":
        return "¥" + s
    elif cur == "TWD":
        return "NT$" + s
    elif cur == "PLN":
        return s + " zł"
    elif cur == "ZAR":
        return "R " + s
    else:
        return s + " " + cur
# }}}

# {{{ is_false: Checks for identity (not just equality) with False.
@register.filter
def is_false(b):
    return b is False
# }}}

# {{{ smallhash: Generates a small (6-character) string hash.
@register.filter
def smallhash(value):
    m = hashlib.md5()
    m.update(value.encode('utf-8'))
    return m.hexdigest()[:6]
# }}}

# {{{
@register.filter
def makedate(value):
    if isinstance(value, str):
        try:
            value = datetime.strptime(value, '%Y-%m-%d').date()
        except:
            value = None
    return value
# }}}
# }}}

# {{{ URL generation filters

# {{{ css: Generates a CSS file URL
@register.filter
@stringfilter
def css(value):
    if not DEBUG:
        return 'http://css.aligulac.com/' + value + '.css'
    else:
        return '/css/' + value + '.css'
# }}}

# {{{ js: Generates a JS file URL
@register.filter
@stringfilter
def js(value):
    if not DEBUG:
        return 'http://js.aligulac.com/' + value + '.js'
    else:
        return '/js/' + value + '.js'
# }}}

# {{{ static: Generates URL for static files (must include extension)
@register.filter
@stringfilter
def static(value):
    return 'http://static.aligulac.com/' + value
register.filter('static', static)
# }}}

# {{{ imgfolder: Generates URL for images (PNG only), where the alternative argument gives folder.
# Does not pass through static.
@register.filter
@stringfilter
def imgfolder(value, arg=''):
    if arg != '':
        return str(arg) + '/' + str(value) + '.png'
    else:
        return str(value) + '.png'
# }}}

# {{{ urlfilter: Generates URL-safe strings for player, team and event names, etc.
@register.filter
@stringfilter
def urlfilter(value):
    value = value.replace(' ', '-')
    value = value.replace('/', '')
    return value
# }}}

# }}}

# {{{ Rating number display filters

# {{{ ratscale: Scales a rating number to human-readable format
@register.filter
def ratscale(value):
    return int(round((float(value) + 1.0)*1000))
# }}}

# {{{ ratscalediff: Scales a rating number difference to human-readable format
@register.filter
def ratscalediff(value):
    return int(round(float(value)*1000))
# }}}

# {{{ ratscaleplus: Like ratscale, but takes infinities and N/A into account (for performances)
@register.filter
def ratscaleplus(value):
    if value <= PRF_MININF:
        return '–\u221E'
    elif value <= PRF_INF:
        return '+\u221E'
    elif value <= PRF_NA:
        return 'N/A'
    else:
        return ratscale(value)
# }}}

# {{{ devrange: Computes RD against a certain race.
@register.filter
def ratingdev(event, race):
    return event.get_totaldev(race)
# }}}

# }}}

# {{{ Percentage filters

# {{{ pctg_add: Percentage of value to value+arg.
@register.filter
def pctg_add(value, arg):
    if float(value) + float(arg) > 0:
        return '%.2f' % (100*float(value)/(float(value)+float(arg)))
    else:
        return 0

@register.filter
def pctg_add_f(value, arg):
    if float(value) + float(arg) > 0:
        return 100*float(value)/(float(value)+float(arg))
    else:
        return 0
# }}}

# {{{ pctg_one: Percentage of value to 1.
@register.filter
def pctg_one(value):
    return '%5.2f' % (100*float(value))
# }}}

# {{{ pctg: Percentage of value to arg.
@register.filter
def pctg(value, arg):
    if float(arg) > 0:
        return '%.2f' % (100*float(value)/float(arg))
    else:
        return '%.2f' % 0.0
# }}}

# }}}

# {{{ Filters to use with OP/UP races

# {{{ oprace: Gets the OP race of a period.
@register.filter
def oprace(value):
    if value.dom_p > value.dom_t and value.dom_p > value.dom_z:
        return 'P'
    elif value.dom_t > value.dom_p and value.dom_t > value.dom_z:
        return 'T'
    else:
        return 'Z'
# }}}

# {{{ uprace: Gets the UP race of a period.
@register.filter
def uprace(value):
    if value.dom_p < value.dom_t and value.dom_p < value.dom_z:
        return 'P'
    elif value.dom_t < value.dom_p and value.dom_t < value.dom_z:
        return 'T'
    else:
        return 'Z'
# }}}

# {{{ oppctg: Gets the percentage of OP-ness of a period.
@register.filter
def oppctg(value):
    return int(round(100*(max([value.dom_p, value.dom_t, value.dom_z]) - 1.)))
# }}}

# {{{ uppctg: Gets the percentage of UP-ness of a period.
@register.filter
def uppctg(value):
    return int(round(100*(1. - min([value.dom_p, value.dom_t, value.dom_z]))))
# }}}

# }}}

# {{{ Date filters

# {{{ tomorrow: Gets the next day.
@register.filter
def tomorrow(value):
    return value + timedelta(1)
# }}}

# {{{ yesterday: Gets the previous day.
@register.filter
def yesterday(value):
    return value - timedelta(1)
# }}}

# {{{ nextmonth: Skips one month forward.
@register.filter
def nextmonth(value):
    return value + relativedelta(months=1)
# }}}

# {{{ prevmonth: Skips one month back.
@register.filter
def prevmonth(value):
    return value - relativedelta(months=1)
# }}}

# {{{ datemax: Finds the latest of two dates.
@register.filter
def datemax(value, arg):
    if value - arg > timedelta(0):
        return value
    else:
        return arg
# }}}

# {{{ datemin: Finds the earliest of two dates.
@register.filter
def datemin(value, arg):
    if value - arg < timedelta(0):
        return value
    else:
        return arg
# }}}

# }}}

# {{{ Event-related filters

# {{{ unfold: Returns -value times </div>. (Just... read the code.)
@register.filter
def unfold(value):
    value = -int(value)
    q = ''
    for i in range(0,value):
        q += '</div>'
    return q
# }}}

# {{{ indent: Returns 4 x value times &nbsp;
@register.filter
def indent(value):
    if int(value) < 1:
        return ''
    q = ''
    for i in range(0,int(value)):
        q += '&nbsp;&nbsp;&nbsp;&nbsp;'
    return q
# }}}

# {{{ getN: Takes a list of strings and finds the maximal N so that the concatenation of the last N elements
# (interspersed with commas) has length less than 60.
@register.filter
def getN(lst):
    N = 1
    K = 60
    while N < len(lst) and sum([2+len(x.name) for x in lst[-N-1::]]) < K:
        N += 1
    return N 
# }}}

# {{{ eventliststart: Returns the first part of a list split by the strategy described by getN.
@register.filter
def eventliststart(value, N=None):
    if N == None:
        N = getN(list(value))
    return list(value)[0:-N]
# }}}

# {{{ eventlistend: Returns the last part of a list split by the strategy described by getN.
@register.filter
def eventlistend(value, N=None):
    if N == None:
        N = getN(list(value))
    return list(value)[-N:]
# }}}

# }}}
