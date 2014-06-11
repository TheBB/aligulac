import hashlib
import markdown2
from math import sqrt
import re

from countries import (
    transformations,
)
from datetime import (
    timedelta,
    date,
    datetime,
)
from dateutil.relativedelta import relativedelta

from django import template
from django.template.defaultfilters import (
    stringfilter,
    date as djangodate,
)
from django.utils.safestring import mark_safe
from django.utils.translation import ugettext_lazy as _
from django.utils.translation import ugettext

from aligulac.settings import (
    PRF_NA,
    PRF_INF,
    PRF_MININF,
    DEBUG,
)

from ratings.models import (
    Player,
    Event,
    TLPD_DB_WOLKOREAN,
    TLPD_DB_WOLINTERNATIONAL,
    TLPD_DB_HOTS,
    TLPD_DB_HOTSBETA,
    TLPD_DB_WOLBETA,
)
    
register = template.Library()


# signifiy: Put a + in front if positive, = if zero
@register.filter
def signify(value):
    if value < 0:
        return '–' + str(abs(value))
    elif value > 0:
        return '+' + str(value)
    else:
        return '='

# makearrows: Takes a rating difference and outputs an arrow image
@register.filter
def makearrows(value):
    if value == 0:
        return 'trans'

    if abs(value) > 0.1:
        strength = '3'
    elif abs(value) > 0.04:
        strength = '2'
    else:
        strength = '1'
    return ('up' if value > 0 else 'down') + 'arrow' + strength

# markdown: Filters text written in markdown.
@register.filter
@stringfilter
def markdown(value):
    return mark_safe(markdown2.markdown(value, safe_mode=True))

# jsescape: Escapes a string to be placed inside a
#              javascript string
@register.filter
@stringfilter
def jsescape(value):
    return value.replace(r"'", r"\'").replace(r'"', r'\"')

# urlify: Adds links to URLs.
@register.filter
@stringfilter
def urlify(value):
    pat1 = re.compile(
        r"(^|[\n ])(([\w]+?://[\w\#$%&~.\-;:=,?@\[\]+]*)(/[\w\#$%&~/.\-;:=,?@\[\]+]*)?)",
        re.IGNORECASE | re.DOTALL
    )
    pat2 = re.compile(
        r"(^|[\n ])(((www|ftp)\.[\w\#$%&~.\-;:=,?@\[\]+]*)(/[\w\#$%&~/.\-;:=,?@\[\]+]*)?)",
        re.IGNORECASE | re.DOTALL
    )

    value = pat1.sub(r'\1<a href="\2">\3</a>', value)
    value = pat2.sub(r'\1<a href="http://\2">\3</a>', value)
    return mark_safe(value)

# player_url: Generate a player URL.
@register.filter
def player_url(value, with_path=True):
    step1 = "{}-{}".format(value.id, urlfilter(value.tag))
    if not with_path:
        return step1
    return "/players/" + step1 + "/"

# vs_url: Generate a search query for the two players
@register.filter
def vs_url(value, arg):
    return "/results/search/?search=&after=&before=&players={}%0D%0A{}" \
        "&event=&bestof=all&offline=both&game=all&op=Search".format(value, arg)

# addf: Adds floating point numbers.
@register.filter
def addf(value, arg):
    return float(value) + float(arg)

# subf: Subtracts floating point numbers.
@register.filter
def subf(value, arg):
    return float(value) - float(arg)

# sub: Subtracts integers.
@register.filter
def sub(value, arg):
    return int(value) - int(arg)

# Integer exponentiation.
@register.filter
def pow(value, arg):
    return int(value) ** int(arg)

# racefull: Converts a single-character race to human readable format.
@register.filter
def racefull(value):
    return ([
        _('Protoss'),
        _('Terran'),
        _('Zerg'),
        _('Random'),
        _('Race switcher')][['P','T','Z','R','S'].index(value)]
    )

# countryfull: Converts a country code to human readable format.
@register.filter
def countryfull(value):
    if value is not None:
        return transformations.cc_to_cn(value)
    return value

# haslogo: Checks whether a team given by ID has a logo file.
@register.filter
def haslogo(value):
    try:
        with open('/usr/local/www/media/al/teams/%i.png' % int(value)) as f:
            return True
    except:
        return False

# Creates match prediction links.
@register.filter
def makematchlink(value):
    if value['pla']['id'] is None or value['plb']['id'] is None:
        return None

    return (
        '/inference/match/?bo=%i&amp;ps=%i%%2C%i&amp;s1=%i&amp;s2=%i' % (
            2*value['sim']._num-1,
            value['pla']['id'],
            value['plb']['id'],
            value['pla']['score'],
            value['plb']['score'],
    ))

# milliseconds: Converts a date (not datetime) to millisecond format, needed for using the charts.
@register.filter
def milliseconds(value):
    return (value - date(1970,1,1)).days * 24 * 60 * 60 * 1000

# add_separator: Adds separators to a large number.
@register.filter
def add_separator(value):
    svalue = str(value)

    if '.' in svalue:
        string, decimals = tuple(svalue.split('.'))
    else:
        string, decimals = svalue, None
    newstring = ''

    while True:
        if len(string) <= 3:
            newstring = string + newstring
            if decimals is not None and len(decimals.rstrip('0')) != 0:
                return newstring + '.' + decimals.rstrip('0')
            else:
                return newstring
        else:
            newstring = ',' + string[-3:] + newstring
            string = string[:-3]

# add_sep_and_cur: Adds separators and currency symbol to a prize sum.
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
    # elif cur in ['XBT', 'BTC']:
    #     return "\u0243 " + s
    else:
        return s + " " + cur

# is_false: Checks for identity (not just equality) with False.
@register.filter
def is_false(b):
    return b is False

# smallhash: Generates a small (6-character) string hash.
@register.filter
def smallhash(value):
    m = hashlib.md5()
    m.update(value.encode('utf-8'))
    return m.hexdigest()[:6]

# makedate: Produces a date in the right format, or none.
@register.filter
def makedate(value):
    if isinstance(value, str):
        try:
            value = datetime.strptime(value, '%Y-%m-%d').date()
        except:
            value = None
    return value

# get_tlpd_list: Takes a TLPD DB bit-flag integer and returns a list of databases.
@register.filter
def get_tlpd_list(value):
    value = int(value) if value is not None else 0

    dbs = [
        (TLPD_DB_WOLBETA,           'sc2-beta',           _('TLPD:WoL:B')),
        (TLPD_DB_WOLKOREAN,         'sc2-korean',         _('TLPD:WoL:KR')),
        (TLPD_DB_WOLINTERNATIONAL,  'sc2-international',  _('TLPD:WoL:IN')),
        (TLPD_DB_HOTSBETA,          'hots-beta',          _('TLPD:HotS:B')),
        (TLPD_DB_HOTS,              'hots',               _('TLPD:HotS')),
    ]

    ret = []
    for db_flag, tlpd_db_name, human_db_name in dbs:
        if value & db_flag != 0:
            ret.append((tlpd_db_name, human_db_name))
    return ret

# URL generation filters

# css: Generates a CSS file URL
@register.filter
@stringfilter
def css(value):
    if not DEBUG:
        return 'http://css.aligulac.com/' + value + '.css'
    else:
        return '/css/' + value + '.css'

# js: Generates a JS file URL
@register.filter
@stringfilter
def js(value):
    if not DEBUG:
        return 'http://js.aligulac.com/' + value + '.js'
    else:
        return '/js/' + value + '.js'

# img: Generates a png-image file URL
@register.filter
@stringfilter
def img(value, folder=None):
    img_file = ""
    if folder is not None:
        img_file += str(folder) + "/"
    img_file  += str(value)
    if not DEBUG:
        return 'http://img.aligulac.com/' + img_file + '.png'
    else:
        return '/img/' + img_file + '.png'

# static: Generates URL for static files (must include extension)
@register.filter
@stringfilter
def static(value):
    return 'http://static.aligulac.com/' + value
register.filter('static', static)

# imgdir: Gets the url of the image directory
# For example {{ '/'|imgdir }} gives the root dir containing images and
#             {{ '/flags/'|imgdir }} gives the dir containing flags.
@register.filter
@stringfilter
def imgdir(value):
    value = str(value)
    if not value.startswith('/'):
        value = '/' + value
    if not DEBUG:
        return 'http://img.aligulac.com' + value
    else:
        return '/img' + value

# urlfilter: Generates URL-safe strings for player, team and event names, etc.
@register.filter
@stringfilter
def urlfilter(value):
    value = value.replace(' ', '-')
    value = value.replace('/', '')
    return value

# Rating number display filters

# ratscale: Scales a rating number to human-readable format
@register.filter
def ratscale(value):
    return int(round((float(value) + 1.0)*1000))

# ratscalediff: Scales a rating number difference to human-readable format
@register.filter
def ratscalediff(value):
    return int(round(float(value)*1000))

# ratscaleplus: Like ratscale, but takes infinities and N/A into account (for performances)
@register.filter
def ratscaleplus(value):
    if value <= PRF_MININF:
        return '–\u221E'
    elif value <= PRF_INF:
        return '+\u221E'
    elif value <= PRF_NA:
        return _('N/A')
    else:
        return ratscale(value)

# devrange: Computes RD against a certain race.
@register.filter
def ratingdev(event, race):
    return event.get_totaldev(race)

# Percentage filters

# pctg_add: Percentage of value to value+arg.
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

# pctg_one: Percentage of value to 1.
@register.filter
def pctg_one(value):
    return '%5.2f' % (100*float(value))

# pctg: Percentage of value to arg.
@register.filter
def pctg(value, arg):
    if float(arg) > 0:
        return '%.2f' % (100*float(value)/float(arg))
    else:
        return '%.2f' % 0.0

@register.filter
def pctg_scl(value, arg):
    if float(arg) > 0:
        return '%.2f' % (100*float(value)/(1.0001*float(arg)))
    else:
        return '%.2f' % 0.0

# Filters to use with OP/UP races

# oprace: Gets the OP race of a period.
@register.filter
def oprace(value):
    if value.dom_p > value.dom_t and value.dom_p > value.dom_z:
        return 'P'
    elif value.dom_t > value.dom_p and value.dom_t > value.dom_z:
        return 'T'
    else:
        return 'Z'

# uprace: Gets the UP race of a period.
@register.filter
def uprace(value):
    if value.dom_p < value.dom_t and value.dom_p < value.dom_z:
        return 'P'
    elif value.dom_t < value.dom_p and value.dom_t < value.dom_z:
        return 'T'
    else:
        return 'Z'

# oppctg: Gets the percentage of OP-ness of a period.
@register.filter
def oppctg(value):
    return int(round(100*(max([value.dom_p, value.dom_t, value.dom_z]) - 1.)))

# uppctg: Gets the percentage of UP-ness of a period.
@register.filter
def uppctg(value):
    return int(round(100*(1. - min([value.dom_p, value.dom_t, value.dom_z]))))

# Date filters

# tomorrow: Gets the next day.
@register.filter
def tomorrow(value):
    return value + timedelta(1)

# yesterday: Gets the previous day.
@register.filter
def yesterday(value):
    return value - timedelta(1)

# nextmonth: Skips one month forward.
@register.filter
def nextmonth(value):
    return value + relativedelta(months=1)

# prevmonth: Skips one month back.
@register.filter
def prevmonth(value):
    return value - relativedelta(months=1)

# datemax: Finds the latest of two dates.
@register.filter
def datemax(value, arg):
    if value - arg > timedelta(0):
        return value
    else:
        return arg

# datemin: Finds the earliest of two dates.
@register.filter
def datemin(value, arg):
    if value - arg < timedelta(0):
        return value
    else:
        return arg

# cdate: Custom translate-friendly date formatting.
@register.filter
def cdate(value, arg):
    temp = (djangodate(value, arg)
        .replace('January',    ugettext('January'))
        .replace('February',   ugettext('February'))
        .replace('March',      ugettext('March'))
        .replace('April',      ugettext('April'))
        .replace('May',        ugettext('May'))
        .replace('June',       ugettext('June'))
        .replace('July',       ugettext('July'))
        .replace('August',     ugettext('August'))
        .replace('September',  ugettext('September'))
        .replace('October',    ugettext('October'))
        .replace('November',   ugettext('November'))
        .replace('December',   ugettext('December'))
        .replace('Jan.',       ugettext('Jan.'))
        .replace('Feb.',       ugettext('Feb.'))
        .replace('Aug.',       ugettext('Aug.'))
        .replace('Sept.',      ugettext('Sept.'))
        .replace('Oct.',       ugettext('Oct.'))
        .replace('Nov.',       ugettext('Nov.'))
        .replace('Dec.',       ugettext('Dec.'))
        .replace('jan',        ugettext('jan'))
        .replace('feb',        ugettext('feb'))
        .replace('mar',        ugettext('mar'))
        .replace('apr',        ugettext('apr'))
        .replace('may',        ugettext('may'))
        .replace('jun',        ugettext('jun'))
        .replace('jul',        ugettext('jul'))
        .replace('aug',        ugettext('aug'))
        .replace('sep',        ugettext('sep'))
        .replace('oct',        ugettext('oct'))
        .replace('nov',        ugettext('nov'))
        .replace('dec',        ugettext('dec'))
        .replace('Monday',     ugettext('Monday'))
        .replace('Tuesday',    ugettext('Tuesday'))
        .replace('Wednesday',  ugettext('Wednesday'))
        .replace('Thursday',   ugettext('Thursday'))
        .replace('Friday',     ugettext('Friday'))
        .replace('Saturday',   ugettext('Saturday'))
        .replace('Sunday',     ugettext('Sunday'))
        .replace('mon',        ugettext('mon'))
        .replace('tue',        ugettext('tue'))
        .replace('wed',        ugettext('wed'))
        .replace('thu',        ugettext('thu'))
        .replace('fri',        ugettext('fri'))
        .replace('sat',        ugettext('sat'))
        .replace('sun',        ugettext('sun'))
    )
    return temp

# Event-related filters

# unfold: Returns -value times </div>. (Just... read the code.)
@register.filter
def unfold(value):
    value = -int(value)
    q = ''
    for i in range(0,value):
        q += '</div>'
    return q

# indent: Returns 4 x value times &nbsp;
@register.filter
def indent(value):
    value = int(value) - 1
    if value < 1:
        return ''
    q = ''
    for i in range(0,int(value)):
        q += '&nbsp;&nbsp;&nbsp;&nbsp;'
    return q

# getN: Takes a list of strings and finds the maximal N so that the concatenation of the last N elements
# (interspersed with commas) has length less than 60.
@register.filter
def getN(lst):
    N = 1
    K = 60
    while N < len(lst) and sum([2+len(x.name) for x in lst[-N-1::]]) < K:
        N += 1
    return N 

# eventliststart: Returns the first part of a list split by the strategy described by getN.
@register.filter
def eventliststart(value, N=None):
    if N == None:
        N = getN(list(value))
    return list(value)[0:-N]

# eventlistend: Returns the last part of a list split by the strategy described by getN.
@register.filter
def eventlistend(value, N=None):
    if N == None:
        N = getN(list(value))
    return list(value)[-N:]

# Model display filters

@register.filter
def player(value):
    if not isinstance(value, Player):
        return value

    flag = ""
    if value.country is not None:
        flag = "<img src='{flag}' />".format(
            flag=img("flags/" + value.country.lower()))

    return mark_safe((
        "<span class='player'>"
        "<a href='/players/{id}-{safetag}/'>"
        "{flag}<img src='{race}' />{tag}"
        "</a>"
        "</span>"
        ).format(
            tag=value.tag,
            safetag=urlfilter(value.tag),
            id=value.id,
            flag=flag,
            race=img(value.race)))

@register.filter
def player_no_race(value):
    if not isinstance(value, Player):
        return value

    flag = ""
    if value.country is not None:
        flag = "<img src='{flag}' />".format(
            flag=img("flags/" + value.country.lower()))

    return mark_safe((
        "<span class='player'>"
        "<a href='/players/{id}-{safetag}/'>"
        "{flag}{tag}"
        "</a>"
        "</span>"
        ).format(
            tag=value.tag,
            safetag=urlfilter(value.tag),
            id=value.id,
            flag=flag))

@register.filter
def event(value):
    if not isinstance(value, Event):
        return value

    return mark_safe((
        "<a href='/results/events/{id}-{safename}/'>"
        "{name}"
        "</a>").format(id=value.id,
                       name=value.fullname,
                       safename=urlfilter(value.fullname)))
