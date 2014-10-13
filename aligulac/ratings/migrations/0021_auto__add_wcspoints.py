# -*- coding: utf-8 -*-
from south.utils import datetime_utils as datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'WCSPoints'
        db.create_table('wcspoints', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('event', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['ratings.Event'])),
            ('player', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['ratings.Player'])),
            ('points', self.gf('django.db.models.fields.IntegerField')()),
            ('placement', self.gf('django.db.models.fields.IntegerField')()),
        ))
        db.send_create_signal('ratings', ['WCSPoints'])


    def backwards(self, orm):
        # Deleting model 'WCSPoints'
        db.delete_table('wcspoints')


    models = {
        'auth.group': {
            'Meta': {'object_name': 'Group'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '80', 'unique': 'True'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'blank': 'True', 'symmetrical': 'False'})
        },
        'auth.permission': {
            'Meta': {'ordering': "('content_type__app_label', 'content_type__model', 'codename')", 'object_name': 'Permission', 'unique_together': "(('content_type', 'codename'),)"},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Group']", 'related_name': "'user_set'", 'blank': 'True', 'symmetrical': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'related_name': "'user_set'", 'blank': 'True', 'symmetrical': 'False'}),
            'username': ('django.db.models.fields.CharField', [], {'max_length': '30', 'unique': 'True'})
        },
        'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'db_table': "'django_content_type'", 'object_name': 'ContentType', 'unique_together': "(('app_label', 'model'),)"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'ratings.alias': {
            'Meta': {'db_table': "'alias'", 'object_name': 'Alias'},
            'group': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['ratings.Group']", 'null': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'player': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['ratings.Player']", 'null': 'True'})
        },
        'ratings.apikey': {
            'Meta': {'db_table': "'apikey'", 'object_name': 'APIKey'},
            'contact': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'date_opened': ('django.db.models.fields.DateField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'key': ('django.db.models.fields.CharField', [], {'primary_key': 'True', 'max_length': '20', 'db_index': 'True'}),
            'organization': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'requests': ('django.db.models.fields.IntegerField', [], {})
        },
        'ratings.balanceentry': {
            'Meta': {'db_table': "'balanceentry'", 'object_name': 'BalanceEntry'},
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
            'Meta': {'ordering': "['-earnings']", 'db_table': "'earnings'", 'object_name': 'Earnings'},
            'currency': ('django.db.models.fields.CharField', [], {'max_length': '30'}),
            'earnings': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'event': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['ratings.Event']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'origearnings': ('django.db.models.fields.DecimalField', [], {'decimal_places': '8', 'max_digits': '20'}),
            'placement': ('django.db.models.fields.IntegerField', [], {}),
            'player': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['ratings.Player']"})
        },
        'ratings.event': {
            'Meta': {'ordering': "['idx', 'latest', 'fullname']", 'db_table': "'event'", 'object_name': 'Event'},
            'big': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'category': ('django.db.models.fields.CharField', [], {'null': 'True', 'max_length': '50', 'blank': 'True', 'db_index': 'True'}),
            'closed': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'db_index': 'True'}),
            'earliest': ('django.db.models.fields.DateField', [], {'null': 'True', 'db_index': 'True', 'blank': 'True'}),
            'family': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['ratings.Event']", 'through': "orm['ratings.EventAdjacency']", 'symmetrical': 'False'}),
            'fullname': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '500'}),
            'homepage': ('django.db.models.fields.CharField', [], {'null': 'True', 'max_length': '200', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'idx': ('django.db.models.fields.IntegerField', [], {'db_index': 'True'}),
            'latest': ('django.db.models.fields.DateField', [], {'null': 'True', 'db_index': 'True', 'blank': 'True'}),
            'lft': ('django.db.models.fields.IntegerField', [], {'default': 'None', 'null': 'True', 'blank': 'True'}),
            'lp_name': ('django.db.models.fields.CharField', [], {'null': 'True', 'max_length': '200', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'noprint': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'db_index': 'True'}),
            'parent': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['ratings.Event']", 'related_name': "'parent_event'", 'null': 'True', 'blank': 'True'}),
            'prizepool': ('django.db.models.fields.NullBooleanField', [], {'null': 'True', 'db_index': 'True', 'blank': 'True'}),
            'rgt': ('django.db.models.fields.IntegerField', [], {'default': 'None', 'null': 'True', 'blank': 'True'}),
            'tl_thread': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'tlpd_db': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'tlpd_id': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'type': ('django.db.models.fields.CharField', [], {'max_length': '50', 'db_index': 'True'}),
            'wcs_tier': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'wcs_year': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'})
        },
        'ratings.eventadjacency': {
            'Meta': {'db_table': "'eventadjacency'", 'object_name': 'EventAdjacency'},
            'child': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['ratings.Event']", 'related_name': "'uplink'"}),
            'distance': ('django.db.models.fields.IntegerField', [], {'default': 'None', 'null': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'parent': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['ratings.Event']", 'related_name': "'downlink'"})
        },
        'ratings.group': {
            'Meta': {'db_table': "'group'", 'object_name': 'Group'},
            'active': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'db_index': 'True'}),
            'disbanded': ('django.db.models.fields.DateField', [], {'null': 'True', 'blank': 'True'}),
            'founded': ('django.db.models.fields.DateField', [], {'null': 'True', 'blank': 'True'}),
            'homepage': ('django.db.models.fields.CharField', [], {'null': 'True', 'max_length': '200', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_manual': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_team': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'db_index': 'True'}),
            'lp_name': ('django.db.models.fields.CharField', [], {'null': 'True', 'max_length': '200', 'blank': 'True'}),
            'meanrating': ('django.db.models.fields.FloatField', [], {'default': '0.0', 'null': 'True'}),
            'members': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['ratings.Player']", 'through': "orm['ratings.GroupMembership']", 'symmetrical': 'False'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100', 'db_index': 'True'}),
            'scoreak': ('django.db.models.fields.FloatField', [], {'default': '0.0', 'null': 'True'}),
            'scorepl': ('django.db.models.fields.FloatField', [], {'default': '0.0', 'null': 'True'}),
            'shortname': ('django.db.models.fields.CharField', [], {'null': 'True', 'max_length': '25', 'blank': 'True'})
        },
        'ratings.groupmembership': {
            'Meta': {'db_table': "'groupmembership'", 'object_name': 'GroupMembership'},
            'current': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'db_index': 'True'}),
            'end': ('django.db.models.fields.DateField', [], {'null': 'True', 'blank': 'True'}),
            'group': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['ratings.Group']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'player': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['ratings.Player']"}),
            'playing': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'db_index': 'True'}),
            'start': ('django.db.models.fields.DateField', [], {'null': 'True', 'blank': 'True'})
        },
        'ratings.match': {
            'Meta': {'db_table': "'match'", 'object_name': 'Match'},
            'date': ('django.db.models.fields.DateField', [], {}),
            'event': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '200', 'blank': 'True'}),
            'eventobj': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['ratings.Event']", 'null': 'True', 'blank': 'True'}),
            'game': ('django.db.models.fields.CharField', [], {'default': "'WoL'", 'max_length': '10', 'db_index': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'offline': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'db_index': 'True'}),
            'period': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['ratings.Period']"}),
            'pla': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['ratings.Player']", 'related_name': "'match_pla'"}),
            'plb': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['ratings.Player']", 'related_name': "'match_plb'"}),
            'rca': ('django.db.models.fields.CharField', [], {'max_length': '1', 'db_index': 'True'}),
            'rcb': ('django.db.models.fields.CharField', [], {'max_length': '1', 'db_index': 'True'}),
            'rta': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['ratings.Rating']", 'related_name': "'rta'", 'null': 'True'}),
            'rtb': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['ratings.Rating']", 'related_name': "'rtb'", 'null': 'True'}),
            'sca': ('django.db.models.fields.SmallIntegerField', [], {'db_index': 'True'}),
            'scb': ('django.db.models.fields.SmallIntegerField', [], {'db_index': 'True'}),
            'submitter': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']", 'null': 'True', 'blank': 'True'}),
            'treated': ('django.db.models.fields.BooleanField', [], {'default': 'False'})
        },
        'ratings.message': {
            'Meta': {'db_table': "'message'", 'object_name': 'Message'},
            'event': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['ratings.Event']", 'null': 'True'}),
            'group': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['ratings.Group']", 'null': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'match': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['ratings.Match']", 'null': 'True'}),
            'message': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '1000'}),
            'params': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '1000'}),
            'player': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['ratings.Player']", 'null': 'True'}),
            'type': ('django.db.models.fields.CharField', [], {'max_length': '10'})
        },
        'ratings.period': {
            'Meta': {'db_table': "'period'", 'object_name': 'Period'},
            'computed': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'db_index': 'True'}),
            'dom_p': ('django.db.models.fields.FloatField', [], {'null': 'True'}),
            'dom_t': ('django.db.models.fields.FloatField', [], {'null': 'True'}),
            'dom_z': ('django.db.models.fields.FloatField', [], {'null': 'True'}),
            'end': ('django.db.models.fields.DateField', [], {'db_index': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'needs_recompute': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'db_index': 'True'}),
            'num_games': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'num_newplayers': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'num_retplayers': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'start': ('django.db.models.fields.DateField', [], {'db_index': 'True'})
        },
        'ratings.player': {
            'Meta': {'ordering': "['tag']", 'db_table': "'player'", 'object_name': 'Player'},
            'birthday': ('django.db.models.fields.DateField', [], {'null': 'True', 'blank': 'True'}),
            'country': ('django.db.models.fields.CharField', [], {'null': 'True', 'max_length': '2', 'blank': 'True', 'db_index': 'True'}),
            'current_rating': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['ratings.Rating']", 'related_name': "'current'", 'null': 'True', 'blank': 'True'}),
            'dom_end': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['ratings.Period']", 'related_name': "'player_dom_end'", 'null': 'True', 'blank': 'True'}),
            'dom_start': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['ratings.Period']", 'related_name': "'player_dom_start'", 'null': 'True', 'blank': 'True'}),
            'dom_val': ('django.db.models.fields.FloatField', [], {'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'lp_name': ('django.db.models.fields.CharField', [], {'null': 'True', 'max_length': '200', 'blank': 'True'}),
            'mcnum': ('django.db.models.fields.IntegerField', [], {'default': 'None', 'null': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'null': 'True', 'max_length': '100', 'blank': 'True'}),
            'race': ('django.db.models.fields.CharField', [], {'max_length': '1', 'db_index': 'True'}),
            'romanized_name': ('django.db.models.fields.CharField', [], {'null': 'True', 'max_length': '100', 'blank': 'True'}),
            'sc2e_id': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'tag': ('django.db.models.fields.CharField', [], {'max_length': '30', 'db_index': 'True'}),
            'tlpd_db': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'tlpd_id': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'})
        },
        'ratings.prematch': {
            'Meta': {'db_table': "'prematch'", 'object_name': 'PreMatch'},
            'date': ('django.db.models.fields.DateField', [], {}),
            'group': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['ratings.PreMatchGroup']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'pla': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['ratings.Player']", 'related_name': "'prematch_pla'", 'null': 'True', 'blank': 'True'}),
            'pla_string': ('django.db.models.fields.CharField', [], {'default': "''", 'null': 'True', 'max_length': '200', 'blank': 'True'}),
            'plb': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['ratings.Player']", 'related_name': "'prematch_plb'", 'null': 'True', 'blank': 'True'}),
            'plb_string': ('django.db.models.fields.CharField', [], {'default': "''", 'null': 'True', 'max_length': '200', 'blank': 'True'}),
            'rca': ('django.db.models.fields.CharField', [], {'null': 'True', 'max_length': '1'}),
            'rcb': ('django.db.models.fields.CharField', [], {'null': 'True', 'max_length': '1'}),
            'sca': ('django.db.models.fields.SmallIntegerField', [], {}),
            'scb': ('django.db.models.fields.SmallIntegerField', [], {})
        },
        'ratings.prematchgroup': {
            'Meta': {'db_table': "'prematchgroup'", 'object_name': 'PreMatchGroup'},
            'contact': ('django.db.models.fields.CharField', [], {'default': "''", 'null': 'True', 'max_length': '200', 'blank': 'True'}),
            'date': ('django.db.models.fields.DateField', [], {}),
            'event': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '200', 'blank': 'True'}),
            'game': ('django.db.models.fields.CharField', [], {'default': "'wol'", 'max_length': '10'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'notes': ('django.db.models.fields.TextField', [], {'default': "''", 'null': 'True', 'blank': 'True'}),
            'offline': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'source': ('django.db.models.fields.CharField', [], {'default': "''", 'null': 'True', 'max_length': '500', 'blank': 'True'})
        },
        'ratings.rating': {
            'Meta': {'ordering': "['period']", 'db_table': "'rating'", 'object_name': 'Rating'},
            'bf_dev': ('django.db.models.fields.FloatField', [], {'default': '1', 'null': 'True', 'blank': 'True'}),
            'bf_dev_vp': ('django.db.models.fields.FloatField', [], {'default': '1', 'null': 'True', 'blank': 'True'}),
            'bf_dev_vt': ('django.db.models.fields.FloatField', [], {'default': '1', 'null': 'True', 'blank': 'True'}),
            'bf_dev_vz': ('django.db.models.fields.FloatField', [], {'default': '1', 'null': 'True', 'blank': 'True'}),
            'bf_rating': ('django.db.models.fields.FloatField', [], {'default': '0'}),
            'bf_rating_vp': ('django.db.models.fields.FloatField', [], {'default': '0'}),
            'bf_rating_vt': ('django.db.models.fields.FloatField', [], {'default': '0'}),
            'bf_rating_vz': ('django.db.models.fields.FloatField', [], {'default': '0'}),
            'comp_rat': ('django.db.models.fields.FloatField', [], {'null': 'True', 'blank': 'True'}),
            'comp_rat_vp': ('django.db.models.fields.FloatField', [], {'null': 'True', 'blank': 'True'}),
            'comp_rat_vt': ('django.db.models.fields.FloatField', [], {'null': 'True', 'blank': 'True'}),
            'comp_rat_vz': ('django.db.models.fields.FloatField', [], {'null': 'True', 'blank': 'True'}),
            'decay': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'dev': ('django.db.models.fields.FloatField', [], {}),
            'dev_vp': ('django.db.models.fields.FloatField', [], {}),
            'dev_vt': ('django.db.models.fields.FloatField', [], {}),
            'dev_vz': ('django.db.models.fields.FloatField', [], {}),
            'domination': ('django.db.models.fields.FloatField', [], {'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'period': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['ratings.Period']"}),
            'player': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['ratings.Player']"}),
            'position': ('django.db.models.fields.IntegerField', [], {'null': 'True'}),
            'position_vp': ('django.db.models.fields.IntegerField', [], {'null': 'True'}),
            'position_vt': ('django.db.models.fields.IntegerField', [], {'null': 'True'}),
            'position_vz': ('django.db.models.fields.IntegerField', [], {'null': 'True'}),
            'prev': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['ratings.Rating']", 'related_name': "'prevrating'", 'null': 'True'}),
            'rating': ('django.db.models.fields.FloatField', [], {}),
            'rating_vp': ('django.db.models.fields.FloatField', [], {}),
            'rating_vt': ('django.db.models.fields.FloatField', [], {}),
            'rating_vz': ('django.db.models.fields.FloatField', [], {})
        },
        'ratings.story': {
            'Meta': {'ordering': "['date']", 'db_table': "'story'", 'object_name': 'Story'},
            'date': ('django.db.models.fields.DateField', [], {}),
            'event': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['ratings.Event']", 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'message': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '1000'}),
            'params': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '1000'}),
            'player': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['ratings.Player']"})
        },
        'ratings.wcspoints': {
            'Meta': {'ordering': "['-points']", 'db_table': "'wcspoints'", 'object_name': 'WCSPoints'},
            'event': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['ratings.Event']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'placement': ('django.db.models.fields.IntegerField', [], {}),
            'player': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['ratings.Player']"}),
            'points': ('django.db.models.fields.IntegerField', [], {})
        }
    }

    complete_apps = ['ratings']