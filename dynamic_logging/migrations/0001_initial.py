# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import django.utils.timezone
from django.db import migrations, models

import dynamic_logging.models


class Migration(migrations.Migration):

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Config',
            fields=[
                ('id', models.AutoField(verbose_name='ID', auto_created=True, primary_key=True, serialize=False)),
                ('name', models.CharField(max_length=255)),
                ('config_json', models.TextField()),
            ],
        ),
        migrations.CreateModel(
            name='Trigger',
            fields=[
                ('id', models.AutoField(verbose_name='ID', auto_created=True, primary_key=True, serialize=False)),
                ('name', models.CharField(max_length=255)),
                ('start_date', models.DateTimeField(null=True, default=django.utils.timezone.now)),
                ('end_date', models.DateTimeField(null=True, default=dynamic_logging.models.now_plus_2hours)),
                ('config', models.ForeignKey(to='dynamic_logging.Config', related_name='triggers')),
            ],
            options={
                'get_latest_by': 'start_date',
            },
        ),
        migrations.AlterIndexTogether(
            name='trigger',
            index_together=set([('start_date', 'end_date')]),
        ),
    ]
