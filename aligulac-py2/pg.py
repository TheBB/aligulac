#!/usr/bin/python

import os
import sys

# Required for Django imports to work correctly.
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "aligulac.settings")

from django.contrib.auth.models import User
from ratings.models import Alias, BalanceEntry, Earnings, Event, Group, GroupMembership, Match, Message,\
                           Period, Player, PreMatch, PreMatchGroup, Rating, Story
from blog.models import Post as BPost
from faq.models import Post as FPost
from miniURL.models import MiniURL

fixer = 'WITH mx AS (SELECT MAX (id) AS id FROM public.%s) SELECT setval(\'public.%s_id_seq\', mx.id) '\
      + 'AS curseq FROM mx;'

def san(s):
    return s.replace("'", "''")

def inull(i):
    return str(i) if i is not None else 'NULL'

def snull(s):
    return "'%s'" % san(s) if s is not None else 'NULL'

def senull(s):
    return "'%s'" % san(s) if (s is not None and s != '') else 'NULL'

def bnull(b):
    return '%s' % b if b is not None else 'NULL'

def dnull(d):
    return "'%s'" % str(d) if d is not None else 'NULL'

def fnull(f):
    return "%.20f" % f if f is not None else 'NULL'

print "BEGIN;"
print "SET CONSTRAINTS ALL DEFERRED;"

print "DELETE FROM auth_user;"
tbl = []
for u in User.objects.all():
    tbl.append("(%i,'%s','%s',%s,'%s','%s','%s','%s',%s,%s,'%s')" %\
               (u.id, 
                san(u.password), 
                u.last_login, 
                u.is_superuser, 
                san(u.username),
                san(u.first_name), 
                san(u.last_name), 
                san(u.email), 
                u.is_staff, 
                u.is_active,
                u.date_joined))
s = 'INSERT INTO auth_user VALUES ' + ', '.join(tbl) + ';'
print s.encode('utf-8')
print (fixer % ('auth_user','auth_user')).encode('utf-8')

print "DELETE FROM auth_user_groups;"
tbl = []
for u in User.objects.all():
    tbl.append("(%i,1)" % u.id)
s = 'INSERT INTO auth_user_groups (user_id, group_id) VALUES ' + ', '.join(tbl) + ';'
print s.encode('utf-8');
print (fixer % ('auth_user_groups','auth_user_groups')).encode('utf-8')

print "DELETE FROM alias;"
tbl = []
for a in Alias.objects.all():
    tbl.append("(%i,'%s',%s,%s)" % (a.id, san(a.name), inull(a.player_id), inull(a.group_id)))
s = 'INSERT INTO alias VALUES ' + ', '.join(tbl) + ';'
print s.encode('utf-8');
print (fixer % ('alias','alias')).encode('utf-8')

print "DELETE FROM balanceentry;"
tbl = []
for b in BalanceEntry.objects.all():
    tbl.append("(%i,'%s',%i,%i,%i,%i,%i,%i,%.20f,%.20f,%.20f)" %\
               (b.id,
                b.date,
                b.pvt_wins,
                b.pvt_losses,
                b.pvz_wins,
                b.pvz_losses,
                b.tvz_wins,
                b.tvz_losses,
                b.p_gains,
                b.t_gains,
                b.z_gains))
s = 'INSERT INTO balanceentry VALUES ' + ', '.join(tbl) + ';'
print s.encode('utf-8');
print (fixer % ('balanceentry','balanceentry')).encode('utf-8')

print "DELETE FROM blog_post;"
tbl = []
for p in BPost.objects.all():
    tbl.append("(%i,'%s','%s','%s','%s')" % (p.id, p.date, san(p.author), san(p.title), san(p.text)))
s = 'INSERT INTO blog_post VALUES ' + ', '.join(tbl) + ';'
print s.encode('utf-8');
print (fixer % ('blog_post','blog_post')).encode('utf-8')

print "DELETE FROM earnings;"
tbl = []
for e in Earnings.objects.all():
    tbl.append("(%i,%i,%i,%s,%i,'%s',%i)" %\
               (e.id,
                e.event_id,
                e.player_id,
                inull(e.earnings),
                e.origearnings,
                san(e.currency),
                e.placement))
s = 'INSERT INTO earnings VALUES ' + ', '.join(tbl) + ';'
print s.encode('utf-8');
print (fixer % ('earnings','earnings')).encode('utf-8')

print "DELETE FROM event;"
tbl = []
for e in Event.objects.all():
    tbl.append("(%i,'%s',%s,%i,%i,%s,%s,%s,'%s',%s,%s,%s,%s,%s,%s,%s,%s,%s,'%s')" %\
               (e.id,
                san(e.name),
                inull(e.parent_id),
                e.lft,
                e.rgt,
                e.closed,
                e.big,
                e.noprint,
                san(e.fullname),
                snull(e.homepage),
                snull(e.lp_name),
                inull(e.tlpd_id),
                inull(e.tlpd_db),
                inull(e.tl_thread),
                bnull(e.prizepool),
                dnull(e.earliest),
                dnull(e.latest),
                snull(e.category),
                san(e.type)))
s = 'INSERT INTO event VALUES ' + ', '.join(tbl) + ';'
print s.encode('utf-8');
print (fixer % ('event','event')).encode('utf-8')

print "DELETE FROM faq_post;"
tbl = []
for p in FPost.objects.all():
    tbl.append("(%i,'%s','%s',%i)" % (p.id, san(p.title), san(p.text), p.index))
s = 'INSERT INTO faq_post VALUES ' + ', '.join(tbl) + ';'
print s.encode('utf-8');
print (fixer % ('faq_post','faq_post')).encode('utf-8')

print 'DELETE FROM "group";'
tbl = []
for g in Group.objects.all():
    tbl.append("(%i,'%s',%s,%.20f,%.20f,%s,%s,%s,%s,%s,%s,%s)" %\
               (g.id,
                san(g.name),
                snull(g.shortname),
                g.scoreak,
                g.scorepl,
                dnull(g.founded),
                dnull(g.disbanded),
                g.active,
                snull(g.homepage),
                snull(g.lp_name),
                g.is_team,
                g.is_manual))
s = 'INSERT INTO "group" VALUES ' + ', '.join(tbl) + ';'
print s.encode('utf-8');
print (fixer % ('group','group')).encode('utf-8')

print 'DELETE FROM groupmembership;'
tbl = []
for g in GroupMembership.objects.all():
    tbl.append("(%i,%i,%i,%s,%s,%s,%s)" %\
               (g.id,
                g.player_id,
                g.group_id,
                dnull(g.start),
                dnull(g.end),
                g.current,
                g.playing))
s = 'INSERT INTO "groupmembership" VALUES ' + ', '.join(tbl) + ';'
print s.encode('utf-8');
print (fixer % ('groupmembership','groupmembership')).encode('utf-8')

print 'DELETE FROM match;'
tbl = []
for m in Match.objects.all():
    tbl.append("(%i,%i,'%s',%i,%i,%i,%i,'%s','%s',%s,'%s',%s,%s,'%s',%s)" %\
               (m.id,
                m.period_id,
                str(m.date),
                m.pla_id,
                m.plb_id,
                m.sca,
                m.scb,
                m.rca,
                m.rcb,
                m.treated,
                san(m.event),
                inull(m.eventobj_id),
                inull(m.submitter_id),
                san(m.game),
                m.offline))
s = 'INSERT INTO "match" VALUES ' + ', '.join(tbl) + ';'
print s.encode('utf-8');
print (fixer % ('match','match')).encode('utf-8')

print 'DELETE FROM message;'
tbl = []
for m in Message.objects.all():
    tbl.append("(%i,'%s',%s,'%s',%s,%s,%s,%s)" %\
               (m.id,
                san(m.type),
                snull(m.title),
                san(m.text),
                inull(m.player_id),
                inull(m.event_id),
                inull(m.group_id),
                inull(m.match_id)))
s = 'INSERT INTO "message" VALUES ' + ', '.join(tbl) + ';'
print s.encode('utf-8');
print (fixer % ('message','message')).encode('utf-8')

print 'DELETE FROM miniurl;'
tbl = []
for m in MiniURL.objects.all():
    tbl.append("('%s','%s','%s',%s,%i)" %\
               (san(m.code),
                san(m.longURL),
                str(m.date),
                inull(m.submitter_id),
                m.nb_access))
s = 'INSERT INTO "miniurl" VALUES ' + ', '.join(tbl) + ';'
print s.encode('utf-8');
#print (fixer % ('miniurl','miniurl')).encode('utf-8')

print 'DELETE FROM period;'
tbl = []
for p in Period.objects.all():
    tbl.append("(%i,'%s','%s',%s,%s,%i,%i,%i,%s,%s,%s)" %\
               (p.id,
                str(p.start),
                str(p.end),
                p.computed,
                p.needs_recompute,
                p.num_retplayers,
                p.num_newplayers,
                p.num_games,
                fnull(p.dom_p),
                fnull(p.dom_t),
                fnull(p.dom_z)))
s = 'INSERT INTO "period" VALUES ' + ', '.join(tbl) + ';'
print s.encode('utf-8');
print (fixer % ('period','period')).encode('utf-8')

print 'DELETE FROM player;'
tbl = []
for p in Player.objects.all():
    tbl.append("(%i,'%s',%s,%s,%s,%s,%s,%s,%s,%s,%s,'%s',%s,%s,%s)" %\
               (p.id,
                san(p.tag),
                snull(p.name),
                dnull(p.birthday),
                inull(p.goodynum),
                inull(p.tlpd_id),
                inull(p.tlpd_db),
                snull(p.lp_name),
                inull(p.sc2c_id),
                inull(p.sc2e_id),
                senull(p.country),
                p.race,
                fnull(p.dom_val),
                inull(p.dom_start_id),
                inull(p.dom_end_id)))
s = 'INSERT INTO "player" VALUES ' + ', '.join(tbl) + ';'
print s.encode('utf-8');
print (fixer % ('player','player')).encode('utf-8')

print 'DELETE FROM prematch;'
tbl = []
for p in PreMatch.objects.all():
    tbl.append("(%i,%i,%s,%s,%s,%s,%i,%i,'%s',%s,%s)" %\
               (p.id,
                p.group_id,
                inull(p.pla_id),
                inull(p.plb_id),
                snull(p.pla_string),
                snull(p.plb_string),
                p.sca,
                p.scb,
                str(p.date),
                snull(p.rca),
                snull(p.rcb)))
s = 'INSERT INTO "prematch" VALUES ' + ', '.join(tbl) + ';'
print s.encode('utf-8');
print (fixer % ('prematch','prematch')).encode('utf-8')

print 'DELETE FROM prematchgroup;'
tbl = []
for p in PreMatchGroup.objects.all():
    tbl.append("(%i,'%s','%s',%s,%s,%s,'%s',%s)" %\
               (p.id,
                str(p.date),
                san(p.event),
                snull(p.source),
                snull(p.contact),
                snull(p.notes),
                p.game,
                p.offline))
s = 'INSERT INTO "prematchgroup" VALUES ' + ', '.join(tbl) + ';'
print s.encode('utf-8');
print (fixer % ('prematchgroup','prematchgroup')).encode('utf-8')

print 'DELETE FROM rating;'
tbl = []
for r in Rating.objects.all():
    tbl.append(("(%i,%i,%i,%.20f,%.20f,%.20f,%.20f,%.20f,%.20f,%.20f,%.20f,%s,%s,%s,%s,%s,%s,%s,%s,"\
             + "%.20f,%.20f,%.20f,%.20f,%s,%s,%s,%s,%s,%s,%s,%s,%i,%s)") %\
               (r.id,
                r.period_id,
                r.player_id,
                r.rating,
                r.rating_vp,
                r.rating_vt,
                r.rating_vz,
                r.dev,
                r.dev_vp,
                r.dev_vt,
                r.dev_vz,
                fnull(r.comp_rat),
                fnull(r.comp_rat_vp),
                fnull(r.comp_rat_vt),
                fnull(r.comp_rat_vz),
                fnull(r.comp_dev),
                fnull(r.comp_dev_vp),
                fnull(r.comp_dev_vt),
                fnull(r.comp_dev_vz),
                r.bf_rating,
                r.bf_rating_vp,
                r.bf_rating_vt,
                r.bf_rating_vz,
                fnull(r.bf_dev),
                fnull(r.bf_dev_vp),
                fnull(r.bf_dev_vt),
                fnull(r.bf_dev_vz),
                inull(r.position),
                inull(r.position_vp),
                inull(r.position_vt),
                inull(r.position_vz),
                r.decay,
                fnull(r.domination)))
    if len(tbl) == 10000:
        print ('INSERT INTO "rating" VALUES ' + ', '.join(tbl) + ';').encode('utf-8')
        tbl = []
s = 'INSERT INTO "rating" VALUES ' + ', '.join(tbl) + ';'
print s.encode('utf-8');
print (fixer % ('rating','rating')).encode('utf-8')

print 'DELETE FROM story;'
tbl = []
for s in Story.objects.all():
    tbl.append("(%i,%i,'%s','%s',%s)" %\
               (s.id,
                s.player_id,
                san(s.text),
                str(s.date),
                inull(s.event_id)))
s = 'INSERT INTO "story" VALUES ' + ', '.join(tbl) + ';'
print s.encode('utf-8');
print (fixer % ('story','story')).encode('utf-8')

print('''UPDATE match
    SET rta_id = (SELECT id
                      FROM rating
                      WHERE rating.player_id = match.pla_id
                        AND rating.period_id = match.period_id-1)
    WHERE EXISTS (SELECT id
                      FROM rating
                      WHERE rating.player_id = match.pla_id
                        AND rating.period_id = match.period_id-1);''')
print('''UPDATE match
    SET rtb_id = (SELECT id
                      FROM rating
                      WHERE rating.player_id = match.plb_id
                        AND rating.period_id = match.period_id-1)
    WHERE EXISTS (SELECT id
                      FROM rating
                      WHERE rating.player_id = match.plb_id
                        AND rating.period_id = match.period_id-1);''')
print('''UPDATE rating
    SET prev_id = (SELECT id
                       FROM rating AS rt
                       WHERE rt.player_id = rating.player_id
                         AND rt.period_id = rating.period_id-1)
    WHERE EXISTS (SELECT id
                      FROM rating AS rt
                      WHERE rt.player_id = rating.player_id
                        AND rt.period_id = rating.period_id-1);''')

print "END;"
