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
                ('id', models.AutoField(auto_created=True, serialize=False, verbose_name='ID', primary_key=True)),
                ('name', models.CharField(max_length=255)),
                ('config_json', models.TextField()),
            ],
        ),
        migrations.CreateModel(
            name='Trigger',
            fields=[
                ('id', models.AutoField(auto_created=True, serialize=False, verbose_name='ID', primary_key=True)),
                ('name', models.CharField(max_length=255)),
                ('start_date', models.DateTimeField(default=django.utils.timezone.now)),
                ('end_date', models.DateTimeField(default=dynamic_logging.models.now_plus_2hours)),
                ('config', models.ForeignKey(related_name='triggers', to='dynamic_logging.Config')),
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
