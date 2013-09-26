# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Removing index on 'Event', fields ['rgt']
        db.delete_index('event', ['rgt'])

        # Adding index on 'Event', fields ['prizepool']
        db.create_index('event', ['prizepool'])

        # Adding index on 'Event', fields ['category']
        db.create_index('event', ['category'])

        # Removing index on 'Event', fields ['lft']
        db.delete_index('event', ['lft'])

        # Adding index on 'Event', fields ['closed']
        db.create_index('event', ['closed'])

        # Adding index on 'Event', fields ['noprint']
        db.create_index('event', ['noprint'])

        # Adding index on 'Event', fields ['latest']
        db.create_index('event', ['latest'])

        # Adding index on 'Event', fields ['type']
        db.create_index('event', ['type'])

        # Adding index on 'Event', fields ['earliest']
        db.create_index('event', ['earliest'])

        # Adding index on 'Group', fields ['active']
        db.create_index('group', ['active'])

        # Adding index on 'Group', fields ['is_team']
        db.create_index('group', ['is_team'])

        # Adding index on 'Period', fields ['end']
        db.create_index('period', ['end'])

        # Adding index on 'Period', fields ['computed']
        db.create_index('period', ['computed'])

        # Adding index on 'Period', fields ['start']
        db.create_index('period', ['start'])

        # Adding index on 'Period', fields ['needs_recompute']
        db.create_index('period', ['needs_recompute'])

        # Removing index on 'Player', fields ['name']
        db.delete_index('player', ['name'])

        # Adding index on 'Player', fields ['tag']
        db.create_index('player', ['tag'])


    def backwards(self, orm):
        # Removing index on 'Player', fields ['tag']
        db.delete_index('player', ['tag'])

        # Adding index on 'Player', fields ['name']
        db.create_index('player', ['name'])

        # Removing index on 'Period', fields ['needs_recompute']
        db.delete_index('period', ['needs_recompute'])

        # Removing index on 'Period', fields ['start']
        db.delete_index('period', ['start'])

        # Removing index on 'Period', fields ['computed']
        db.delete_index('period', ['computed'])

        # Removing index on 'Period', fields ['end']
        db.delete_index('period', ['end'])

        # Removing index on 'Group', fields ['is_team']
        db.delete_index('group', ['is_team'])

        # Removing index on 'Group', fields ['active']
        db.delete_index('group', ['active'])

        # Removing index on 'Event', fields ['earliest']
        db.delete_index('event', ['earliest'])

        # Removing index on 'Event', fields ['type']
        db.delete_index('event', ['type'])

        # Removing index on 'Event', fields ['latest']
        db.delete_index('event', ['latest'])

        # Removing index on 'Event', fields ['noprint']
        db.delete_index('event', ['noprint'])

        # Removing index on 'Event', fields ['closed']
        db.delete_index('event', ['closed'])

        # Adding index on 'Event', fields ['lft']
        db.create_index('event', ['lft'])

        # Removing index on 'Event', fields ['category']
        db.delete_index('event', ['category'])

        # Removing index on 'Event', fields ['prizepool']
        db.delete_index('event', ['prizepool'])

        # Adding index on 'Event', fields ['rgt']
        db.create_index('event', ['rgt'])


    models = {
        'auth.group': {
            'Meta': {'object_name': 'Group'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'blank': 'True', 'symmetrical': 'False', 'to': "orm['auth.Permission']"})
        },
        'auth.permission': {
            'Meta': {'object_name': 'Permission', 'ordering': "('content_type__app_label', 'content_type__model', 'codename')", 'unique_together': "(('content_type', 'codename'),)"},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'blank': 'True', 'max_length': '75'}),
            'first_name': ('django.db.models.fields.CharField', [], {'blank': 'True', 'max_length': '30'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'blank': 'True', 'to': "orm['auth.Group']", 'symmetrical': 'False', 'related_name': "'user_set'"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'blank': 'True', 'max_length': '30'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'blank': 'True', 'to': "orm['auth.Permission']", 'symmetrical': 'False', 'related_name': "'user_set'"}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        'contenttypes.contenttype': {
            'Meta': {'object_name': 'ContentType', 'db_table': "'django_content_type'", 'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'ratings.alias': {
            'Meta': {'object_name': 'Alias', 'db_table': "'alias'"},
            'group': ('django.db.models.fields.related.ForeignKey', [], {'null': 'True', 'to': "orm['ratings.Group']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'player': ('django.db.models.fields.related.ForeignKey', [], {'null': 'True', 'to': "orm['ratings.Player']"})
        },
        'ratings.balanceentry': {
            'Meta': {'object_name': 'BalanceEntry', 'db_table': "'balanceentry'"},
            'date': ('django.db.models.fields.DateField', [], {}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'p_gains': ('django.db.models.fields.FloatField', [], {}),
            'pvt_losses': ('django.db.models.fields.IntegerField', [], {}),
            'pvt_wins': ('django.db.models.fields.IntegerField', [], {}),
            'pvz_losses': ('django.db.models.fields.IntegerField', [], {}),
            'pvz_wins': ('django.db.models.fields.IntegerField', [], {}),
            't_gains': ('django.db.models.fields.FloatField', [], {}),
            'tvz_losses': ('django.db.models.fields.IntegerField', [], {}),
            'tvz_wins': ('django.db.models.fields.IntegerField', [], {}),
            'z_gains': ('django.db.models.fields.FloatField', [], {})
        },
        'ratings.earnings': {
            'Meta': {'object_name': 'Earnings', 'db_table': "'earnings'"},
            'currency': ('django.db.models.fields.CharField', [], {'max_length': '30'}),
            'earnings': ('django.db.models.fields.IntegerField', [], {'blank': 'True', 'null': 'True'}),
            'event': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['ratings.Event']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'origearnings': ('django.db.models.fields.IntegerField', [], {}),
            'placement': ('django.db.models.fields.IntegerField', [], {}),
            'player': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['ratings.Player']"})
        },
        'ratings.event': {
            'Meta': {'object_name': 'Event', 'db_table': "'event'", 'ordering': "['latest', 'fullname']"},
            'big': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'category': ('django.db.models.fields.CharField', [], {'blank': 'True', 'max_length': '50', 'null': 'True', 'db_index': 'True'}),
            'closed': ('django.db.models.fields.BooleanField', [], {'db_index': 'True', 'default': 'False'}),
            'earliest': ('django.db.models.fields.DateField', [], {'blank': 'True', 'null': 'True', 'db_index': 'True'}),
            'family': ('django.db.models.fields.related.ManyToManyField', [], {'through': "orm['ratings.EventAdjacency']", 'symmetrical': 'False', 'to': "orm['ratings.Event']"}),
            'fullname': ('django.db.models.fields.CharField', [], {'max_length': '500', 'default': "''"}),
            'homepage': ('django.db.models.fields.CharField', [], {'blank': 'True', 'max_length': '200', 'null': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'latest': ('django.db.models.fields.DateField', [], {'blank': 'True', 'null': 'True', 'db_index': 'True'}),
            'lft': ('django.db.models.fields.IntegerField', [], {}),
            'lp_name': ('django.db.models.fields.CharField', [], {'blank': 'True', 'max_length': '200', 'null': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'noprint': ('django.db.models.fields.BooleanField', [], {'db_index': 'True', 'default': 'False'}),
            'parent': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'to': "orm['ratings.Event']", 'null': 'True', 'related_name': "'parent_event'"}),
            'prizepool': ('django.db.models.fields.NullBooleanField', [], {'blank': 'True', 'null': 'True', 'db_index': 'True'}),
            'rgt': ('django.db.models.fields.IntegerField', [], {}),
            'tl_thread': ('django.db.models.fields.IntegerField', [], {'blank': 'True', 'null': 'True'}),
            'tlpd_db': ('django.db.models.fields.IntegerField', [], {'blank': 'True', 'null': 'True'}),
            'tlpd_id': ('django.db.models.fields.IntegerField', [], {'blank': 'True', 'null': 'True'}),
            'type': ('django.db.models.fields.CharField', [], {'db_index': 'True', 'max_length': '50'})
        },
        'ratings.eventadjacency': {
            'Meta': {'object_name': 'EventAdjacency', 'db_table': "'eventadjacency'"},
            'child': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['ratings.Event']", 'related_name': "'uplink'"}),
            'distance': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'default': 'None'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'parent': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['ratings.Event']", 'related_name': "'downlink'"})
        },
        'ratings.group': {
            'Meta': {'object_name': 'Group', 'db_table': "'group'"},
            'active': ('django.db.models.fields.BooleanField', [], {'db_index': 'True', 'default': 'True'}),
            'disbanded': ('django.db.models.fields.DateField', [], {'blank': 'True', 'null': 'True'}),
            'founded': ('django.db.models.fields.DateField', [], {'blank': 'True', 'null': 'True'}),
            'homepage': ('django.db.models.fields.CharField', [], {'blank': 'True', 'max_length': '200', 'null': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_manual': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_team': ('django.db.models.fields.BooleanField', [], {'db_index': 'True', 'default': 'True'}),
            'lp_name': ('django.db.models.fields.CharField', [], {'blank': 'True', 'max_length': '200', 'null': 'True'}),
            'meanrating': ('django.db.models.fields.FloatField', [], {'null': 'True', 'default': '0.0'}),
            'members': ('django.db.models.fields.related.ManyToManyField', [], {'through': "orm['ratings.GroupMembership']", 'symmetrical': 'False', 'to': "orm['ratings.Player']"}),
            'name': ('django.db.models.fields.CharField', [], {'db_index': 'True', 'max_length': '100'}),
            'scoreak': ('django.db.models.fields.FloatField', [], {'null': 'True', 'default': '0.0'}),
            'scorepl': ('django.db.models.fields.FloatField', [], {'null': 'True', 'default': '0.0'}),
            'shortname': ('django.db.models.fields.CharField', [], {'blank': 'True', 'max_length': '25', 'null': 'True'})
        },
        'ratings.groupmembership': {
            'Meta': {'object_name': 'GroupMembership', 'db_table': "'groupmembership'"},
            'current': ('django.db.models.fields.BooleanField', [], {'db_index': 'True', 'default': 'True'}),
            'end': ('django.db.models.fields.DateField', [], {'blank': 'True', 'null': 'True'}),
            'group': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['ratings.Group']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'player': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['ratings.Player']"}),
            'playing': ('django.db.models.fields.BooleanField', [], {'db_index': 'True', 'default': 'True'}),
            'start': ('django.db.models.fields.DateField', [], {'blank': 'True', 'null': 'True'})
        },
        'ratings.match': {
            'Meta': {'object_name': 'Match', 'db_table': "'match'"},
            'date': ('django.db.models.fields.DateField', [], {}),
            'event': ('django.db.models.fields.CharField', [], {'blank': 'True', 'max_length': '200', 'default': "''"}),
            'eventobj': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'null': 'True', 'to': "orm['ratings.Event']"}),
            'game': ('django.db.models.fields.CharField', [], {'db_index': 'True', 'max_length': '10', 'default': "'WoL'"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'offline': ('django.db.models.fields.BooleanField', [], {'db_index': 'True', 'default': 'False'}),
            'period': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['ratings.Period']"}),
            'pla': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['ratings.Player']", 'related_name': "'match_pla'"}),
            'plb': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['ratings.Player']", 'related_name': "'match_plb'"}),
            'rca': ('django.db.models.fields.CharField', [], {'db_index': 'True', 'max_length': '1'}),
            'rcb': ('django.db.models.fields.CharField', [], {'db_index': 'True', 'max_length': '1'}),
            'rta': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['ratings.Rating']", 'null': 'True', 'related_name': "'rta'"}),
            'rtb': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['ratings.Rating']", 'null': 'True', 'related_name': "'rtb'"}),
            'sca': ('django.db.models.fields.SmallIntegerField', [], {'db_index': 'True'}),
            'scb': ('django.db.models.fields.SmallIntegerField', [], {'db_index': 'True'}),
            'submitter': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'null': 'True', 'to': "orm['auth.User']"}),
            'treated': ('django.db.models.fields.BooleanField', [], {'default': 'False'})
        },
        'ratings.message': {
            'Meta': {'object_name': 'Message', 'db_table': "'message'"},
            'event': ('django.db.models.fields.related.ForeignKey', [], {'null': 'True', 'to': "orm['ratings.Event']"}),
            'group': ('django.db.models.fields.related.ForeignKey', [], {'null': 'True', 'to': "orm['ratings.Group']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'match': ('django.db.models.fields.related.ForeignKey', [], {'null': 'True', 'to': "orm['ratings.Match']"}),
            'player': ('django.db.models.fields.related.ForeignKey', [], {'null': 'True', 'to': "orm['ratings.Player']"}),
            'text': ('django.db.models.fields.TextField', [], {}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True'}),
            'type': ('django.db.models.fields.CharField', [], {'max_length': '10'})
        },
        'ratings.period': {
            'Meta': {'object_name': 'Period', 'db_table': "'period'"},
            'computed': ('django.db.models.fields.BooleanField', [], {'db_index': 'True', 'default': 'False'}),
            'dom_p': ('django.db.models.fields.FloatField', [], {'null': 'True'}),
            'dom_t': ('django.db.models.fields.FloatField', [], {'null': 'True'}),
            'dom_z': ('django.db.models.fields.FloatField', [], {'null': 'True'}),
            'end': ('django.db.models.fields.DateField', [], {'db_index': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'needs_recompute': ('django.db.models.fields.BooleanField', [], {'db_index': 'True', 'default': 'False'}),
            'num_games': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'num_newplayers': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'num_retplayers': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'start': ('django.db.models.fields.DateField', [], {'db_index': 'True'})
        },
        'ratings.player': {
            'Meta': {'object_name': 'Player', 'db_table': "'player'", 'ordering': "['tag']"},
            'birthday': ('django.db.models.fields.DateField', [], {'blank': 'True', 'null': 'True'}),
            'country': ('django.db.models.fields.CharField', [], {'blank': 'True', 'max_length': '2', 'null': 'True', 'db_index': 'True'}),
            'dom_end': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'to': "orm['ratings.Period']", 'null': 'True', 'related_name': "'player_dom_end'"}),
            'dom_start': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'to': "orm['ratings.Period']", 'null': 'True', 'related_name': "'player_dom_start'"}),
            'dom_val': ('django.db.models.fields.FloatField', [], {'blank': 'True', 'null': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'lp_name': ('django.db.models.fields.CharField', [], {'blank': 'True', 'max_length': '200', 'null': 'True'}),
            'mcnum': ('django.db.models.fields.IntegerField', [], {'blank': 'True', 'null': 'True', 'default': 'None'}),
            'name': ('django.db.models.fields.CharField', [], {'blank': 'True', 'max_length': '100', 'null': 'True'}),
            'race': ('django.db.models.fields.CharField', [], {'db_index': 'True', 'max_length': '1'}),
            'sc2c_id': ('django.db.models.fields.IntegerField', [], {'blank': 'True', 'null': 'True'}),
            'sc2e_id': ('django.db.models.fields.IntegerField', [], {'blank': 'True', 'null': 'True'}),
            'tag': ('django.db.models.fields.CharField', [], {'db_index': 'True', 'max_length': '30'}),
            'tlpd_db': ('django.db.models.fields.IntegerField', [], {'blank': 'True', 'null': 'True'}),
            'tlpd_id': ('django.db.models.fields.IntegerField', [], {'blank': 'True', 'null': 'True'})
        },
        'ratings.prematch': {
            'Meta': {'object_name': 'PreMatch', 'db_table': "'prematch'"},
            'date': ('django.db.models.fields.DateField', [], {}),
            'group': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['ratings.PreMatchGroup']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'pla': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'to': "orm['ratings.Player']", 'null': 'True', 'related_name': "'prematch_pla'"}),
            'pla_string': ('django.db.models.fields.CharField', [], {'blank': 'True', 'max_length': '200', 'default': "''", 'null': 'True'}),
            'plb': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'to': "orm['ratings.Player']", 'null': 'True', 'related_name': "'prematch_plb'"}),
            'plb_string': ('django.db.models.fields.CharField', [], {'blank': 'True', 'max_length': '200', 'default': "''", 'null': 'True'}),
            'rca': ('django.db.models.fields.CharField', [], {'max_length': '1', 'null': 'True'}),
            'rcb': ('django.db.models.fields.CharField', [], {'max_length': '1', 'null': 'True'}),
            'sca': ('django.db.models.fields.SmallIntegerField', [], {}),
            'scb': ('django.db.models.fields.SmallIntegerField', [], {})
        },
        'ratings.prematchgroup': {
            'Meta': {'object_name': 'PreMatchGroup', 'db_table': "'prematchgroup'"},
            'contact': ('django.db.models.fields.CharField', [], {'blank': 'True', 'max_length': '200', 'default': "''", 'null': 'True'}),
            'date': ('django.db.models.fields.DateField', [], {}),
            'event': ('django.db.models.fields.CharField', [], {'blank': 'True', 'max_length': '200', 'default': "''"}),
            'game': ('django.db.models.fields.CharField', [], {'max_length': '10', 'default': "'wol'"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'notes': ('django.db.models.fields.TextField', [], {'blank': 'True', 'null': 'True', 'default': "''"}),
            'offline': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'source': ('django.db.models.fields.CharField', [], {'blank': 'True', 'max_length': '500', 'default': "''", 'null': 'True'})
        },
        'ratings.rating': {
            'Meta': {'object_name': 'Rating', 'db_table': "'rating'", 'ordering': "['period']"},
            'bf_dev': ('django.db.models.fields.FloatField', [], {'blank': 'True', 'null': 'True', 'default': '1'}),
            'bf_dev_vp': ('django.db.models.fields.FloatField', [], {'blank': 'True', 'null': 'True', 'default': '1'}),
            'bf_dev_vt': ('django.db.models.fields.FloatField', [], {'blank': 'True', 'null': 'True', 'default': '1'}),
            'bf_dev_vz': ('django.db.models.fields.FloatField', [], {'blank': 'True', 'null': 'True', 'default': '1'}),
            'bf_rating': ('django.db.models.fields.FloatField', [], {'default': '0'}),
            'bf_rating_vp': ('django.db.models.fields.FloatField', [], {'default': '0'}),
            'bf_rating_vt': ('django.db.models.fields.FloatField', [], {'default': '0'}),
            'bf_rating_vz': ('django.db.models.fields.FloatField', [], {'default': '0'}),
            'comp_rat': ('django.db.models.fields.FloatField', [], {'blank': 'True', 'null': 'True'}),
            'comp_rat_vp': ('django.db.models.fields.FloatField', [], {'blank': 'True', 'null': 'True'}),
            'comp_rat_vt': ('django.db.models.fields.FloatField', [], {'blank': 'True', 'null': 'True'}),
            'comp_rat_vz': ('django.db.models.fields.FloatField', [], {'blank': 'True', 'null': 'True'}),
            'decay': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'dev': ('django.db.models.fields.FloatField', [], {}),
            'dev_vp': ('django.db.models.fields.FloatField', [], {}),
            'dev_vt': ('django.db.models.fields.FloatField', [], {}),
            'dev_vz': ('django.db.models.fields.FloatField', [], {}),
            'domination': ('django.db.models.fields.FloatField', [], {'blank': 'True', 'null': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'period': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['ratings.Period']"}),
            'player': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['ratings.Player']"}),
            'position': ('django.db.models.fields.IntegerField', [], {'null': 'True'}),
            'position_vp': ('django.db.models.fields.IntegerField', [], {'null': 'True'}),
            'position_vt': ('django.db.models.fields.IntegerField', [], {'null': 'True'}),
            'position_vz': ('django.db.models.fields.IntegerField', [], {'null': 'True'}),
            'prev': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['ratings.Rating']", 'null': 'True', 'related_name': "'prevrating'"}),
            'rating': ('django.db.models.fields.FloatField', [], {}),
            'rating_vp': ('django.db.models.fields.FloatField', [], {}),
            'rating_vt': ('django.db.models.fields.FloatField', [], {}),
            'rating_vz': ('django.db.models.fields.FloatField', [], {})
        },
        'ratings.story': {
            'Meta': {'object_name': 'Story', 'db_table': "'story'"},
            'date': ('django.db.models.fields.DateField', [], {}),
            'event': ('django.db.models.fields.related.ForeignKey', [], {'null': 'True', 'to': "orm['ratings.Event']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'player': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['ratings.Player']"}),
            'text': ('django.db.models.fields.CharField', [], {'max_length': '200'})
        }
    }

    complete_apps = ['ratings']