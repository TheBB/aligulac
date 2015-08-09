# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Post',
            fields=[
                ('id', models.AutoField(auto_created=True, verbose_name='ID', primary_key=True, serialize=False)),
                ('title', models.CharField(verbose_name='Title', max_length=100)),
                ('text', models.TextField(verbose_name='Text')),
                ('index', models.IntegerField(verbose_name='Index')),
            ],
            options={
                'ordering': ['index'],
            },
        ),
    ]
