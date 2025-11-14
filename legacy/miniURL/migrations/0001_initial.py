# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='MiniURL',
            fields=[
                ('code', models.CharField(max_length=16, verbose_name='Code', primary_key=True, serialize=False)),
                ('longURL', models.URLField(unique=True, verbose_name='URL')),
                ('date', models.DateTimeField(auto_now_add=True, verbose_name='Date')),
                ('nb_access', models.PositiveIntegerField(default=0, verbose_name='# accessed')),
                ('submitter', models.ForeignKey(blank=True, verbose_name='Submitter', to=settings.AUTH_USER_MODEL, null=True, on_delete=models.CASCADE)),
            ],
            options={
                'verbose_name_plural': 'Mini URLs',
                'verbose_name': 'Mini URL',
                'db_table': 'miniurl',
            },
        ),
    ]
