# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('miniURL', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='miniurl',
            name='longURL',
            field=models.URLField(max_length=500, unique=True, verbose_name='URL'),
        ),
    ]
