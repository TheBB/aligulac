from formats import match, mslgroup, sebracket, debracket, rrgroup

def get_strings(format, type):

    strings = dict()

    # Newline
    strings['nl'] = '\n'

    # Header and footer
    strings['header'] = ''
    strings['footer'] = ''

    if format == 'tls':
        strings['header'] = '[spoiler={title}][b]{title}[/b]'
        strings['footer'] = '[/spoiler]'
    elif format == 'tl':
        strings['header'] = '[b]{title}[/b]'
    elif format == 'reddit':
        strings['header'] = '**{title}**'
    elif format == 'term':
        strings['header'] = '{title}'

    if format == 'tl' or format == 'tls':
        strings['footer'] =\
        '\n[small][url=http://www.teamliquid.net/blogs/viewblog.php?id=380850]details[/url], ' +\
        '[url=http://aligulac.com/]data source[/url], ' +\
        '[url=https://github.com/TheBB/simul]code[/url][/small]' +\
        strings['footer']

    # Match-specific
    strings['outcomelist'] = '\n\n{player} wins ({prob:.2f}%):'
    if format == 'reddit':
        strings['outcomelist'] += '\n'
    strings['mlwinner'] = '\n\nMost likely winner: {player} ({prob:.2f}%)'
    if format == 'reddit':
        strings['mlwinner'] += '  '
    strings['mloutcome'] = '\nMedian outcome: {pa} {na}-{nb} {pb}'
    if format == 'term':
        strings['outcomei'] = '\n{winscore: >5}-{losescore: <1}: {prob: >6.2f}%'
    elif format == 'tl' or format == 'tls':
        strings['outcomei'] = '\n[indent]{winscore}-{losescore}: {prob:.2f}%'
    elif format == 'reddit':
        strings['outcomei'] = '\n* {winscore}-{losescore}: {prob:.2f}%'
    strings['mimage'] = ''
    if format == 'tl' or format == 'tls':
        strings['mimage'] = '\n\n[center][img]{url}[/img][/center]'
        strings['nomimage'] = '\n'
    elif format == 'reddit':
        strings['mimage'] = '\n\n[Visualization]({url})'
        strings['nomimage'] = ''
    else:
        strings['mimage'] = ''
        strings['nomimage'] = ''

    # Bracket-specific
    strings['mlwinnerlist'] = '\n\nMost likely winners:'
    strings['exroundslist'] = '\n\nLife expectancy:'
    if format == 'reddit':
        strings['mlwinnerlist'] += '\n'
        strings['exroundslist'] += '\n'
    if format == 'term':
        strings['mlwinneri'] = '\n{player:>14}: {prob: >6.2f}%'
        strings['exroundsi'] = '\n{player:>14}: {rounds: >4.2f} rounds ({expl})'
    elif format == 'tl' or format == 'tls':
        strings['mlwinneri'] = '\n[indent]{player}: {prob:.2f}%'
        strings['exroundsi'] = '\n[indent]{player}: {rounds:.2f} rounds ({expl})'
    elif format == 'reddit':
        strings['mlwinneri'] = '\n* {player}: {prob:.2f}%'
        strings['exroundsi'] = '\n* {player}: {rounds:.2f} rounds ({expl})'

    # Round robin-specific
    strings['gplayer'] = '\n\n{player}'
    if format == 'reddit':
        strings['gplayer'] += '\n'
    if format == 'term':
        strings['gpexpscore'] = '\n   Expected score: {mw:.2f}-{ml:.2f} (sets: {sw:.2f}-{sl:.2f})'
        strings['gpprobwin'] = '\n   Probability of winning: {prob:.2f}%'
        strings['gpprobthr'] = '\n   Probability of achieving top {thr}: {prob:.2f}%'
        strings['gpmlplace'] = '\n   Most likely place: {place} ({prob:.2f}%)'
    elif format == 'tl' or format == 'tls':
        strings['gpexpscore'] = '\n[indent]Expected score: {mw:.2f}-{ml:.2f} (sets: {sw:.2f}-{sl:.2f})'
        strings['gpprobwin'] = '\n[indent]Probability of winning: {prob:.2f}%'
        strings['gpprobthr'] = '\n[indent]Probability of achieving top {thr}: {prob:.2f}%'
        strings['gpmlplace'] = '\n[indent]Most likely place: {place} ({prob:.2f}%)'
    elif format == 'reddit':
        strings['gpexpscore'] = '\n* Expected score: {mw:.2f}-{ml:.2f} (sets: {sw:.2f}-{sl:.2f})'
        strings['gpprobwin'] = '\n* Probability of winning: {prob:.2f}%'
        strings['gpprobthr'] = '\n* Probability of achieving top {thr}: {prob:.2f}%'
        strings['gpmlplace'] = '\n* Most likely place: {place} ({prob:.2f}%)'

    # MSL group-specific
    if type == mslgroup.MSLGroup:
        strings['header'] += '\n'
    if format == 'term':
        strings['mslgplayer'] = '\n{player:>14}: {prob: >6.2f}%'
    elif format == 'tl' or format == 'tls':
        strings['mslgplayer'] = '\n[indent]{player}: {prob:.2f}%'
    elif format == 'reddit':
        strings['mslgplayer'] = '\n* {player}: {prob:.2f}%'

    # Probability table
    if format == 'term':
        strings['detailheader'] = ''
        strings['ptabletitle'] = '{title}\n'
        strings['ptableheader'] = '\n' + ' '*15
        strings['ptableheading'] = '{heading: >9}'
        strings['ptablename'] = '{player:>14}:'
        strings['ptableentry'] = '{prob: >8.2f}%'
        strings['ptableempty'] = '         '
        strings['ptabletextnum'] = '  {text:>10} ({prob:5.2f}%)'
        strings['ptablebetween'] = '\n\n'
        strings['detailfooter'] = ''
    elif format == 'tls' or format == 'tl':
        strings['detailheader'] = '[code]'
        strings['ptabletitle'] = '{title}\n'
        strings['ptableheader'] = '\n' + ' '*15
        strings['ptableheading'] = '{heading: >9}'
        strings['ptablename'] = '{player:>14}:'
        strings['ptableentry'] = '{prob: >8.2f}%'
        strings['ptableempty'] = '         '
        strings['ptabletextnum'] = '  {text:>10} ({prob:5.2f}%)'
        strings['ptablebetween'] = '\n\n'
        strings['detailfooter'] = '[/code]'
        if format == 'tls':
            strings['detailheader'] = '[spoiler=Details][code]'
            strings['detailfooter'] = '[/code][/spoiler]'
    elif format == 'reddit':
        strings['detailheader'] = ''
        strings['ptabletitle'] = '{title}\n'
        strings['ptableheader'] = '\n' + ' '*21
        strings['ptableheading'] = '{heading: >9}'
        strings['ptablename'] = '    {player:>16}:'
        strings['ptableentry'] = '{prob: >8.2f}%'
        strings['ptableempty'] = '         '
        strings['ptabletextnum'] = '  {text:>10} ({prob:5.2f}%)'
        strings['ptablebetween'] = '\n\n'
        strings['detailfooter'] = ''

    # Other
    strings['perf'] = 'Performance of {name}: badness {bprob:.2f}%, goodness {gprob:.2f}%'

    return strings
