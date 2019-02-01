# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('ratings', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='ArchonMatch',
            fields=[
                ('id', models.AutoField(verbose_name='ID', auto_created=True, serialize=False, primary_key=True)),
                ('date', models.DateField(verbose_name='Date played', help_text='Date played')),
                ('sca', models.SmallIntegerField(verbose_name='Score for player A', help_text='Score for player A', db_index=True)),
                ('scb', models.SmallIntegerField(verbose_name='Score for player B', help_text='Score for player B', db_index=True)),
                ('rca', models.CharField(verbose_name='Race A', choices=[('P', 'Protoss'), ('T', 'Terran'), ('Z', 'Zerg'), ('R', 'Random')], help_text='Race for player A', max_length=1, db_index=True)),
                ('rcb', models.CharField(verbose_name='Race B', choices=[('P', 'Protoss'), ('T', 'Terran'), ('Z', 'Zerg'), ('R', 'Random')], help_text='Race for player B', max_length=1, db_index=True)),
                ('event', models.CharField(verbose_name='Event text (deprecated)', help_text='Event text (if no event object)', blank=True, max_length=200, default='')),
                ('offline', models.BooleanField(verbose_name='Offline', help_text='True if the match was played offline', default=False, db_index=True)),
                ('eventobj', models.ForeignKey(verbose_name='Event', help_text='Event object', null=True, to='ratings.Event', blank=True)),
                ('period', models.ForeignKey(help_text='Period in which the match was played', to='ratings.Period')),
                ('pla1', models.ForeignKey(verbose_name='Player A1', help_text='Player A1', related_name='archon_match_pla1', to='ratings.Player')),
                ('pla2', models.ForeignKey(verbose_name='Player A2', help_text='Player A2', related_name='archon_match_pla2', to='ratings.Player')),
                ('plb1', models.ForeignKey(verbose_name='Player B1', help_text='Player B1', related_name='archon_match_plb1', to='ratings.Player')),
                ('plb2', models.ForeignKey(verbose_name='Player B2', help_text='Player B2', related_name='archon_match_plb2', to='ratings.Player')),
                ('submitter', models.ForeignKey(verbose_name='Submitter', null=True, to=settings.AUTH_USER_MODEL, blank=True)),
            ],
            options={
                'verbose_name_plural': 'archonmatches',
                'db_table': 'archonmatch',
            },
        ),
        migrations.AddField(
            model_name='message',
            name='archon_match',
            field=models.ForeignKey(to='ratings.ArchonMatch', null=True),
        ),
    ]
