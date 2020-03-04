# -*- coding: utf-8 -*-
import django.utils.timezone
from django.db import migrations, models
from django.db.models import CASCADE

import dynamic_logging.models


class Migration(migrations.Migration):

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Config',
            fields=[
                ('id', models.AutoField(auto_created=True, serialize=False, primary_key=True, verbose_name='ID')),
                ('name', models.CharField(max_length=255)),
                ('config_json', models.TextField(default='{}', validators=[dynamic_logging.models.json_value])),
                ('last_update', models.DateTimeField(auto_now=True)),
            ],
        ),
        migrations.CreateModel(
            name='Trigger',
            fields=[
                ('id', models.AutoField(auto_created=True, serialize=False, primary_key=True, verbose_name='ID')),
                ('name', models.CharField(max_length=255)),
                ('is_active', models.BooleanField(default=True)),
                ('start_date', models.DateTimeField(default=django.utils.timezone.now, null=True, blank=True)),
                ('end_date', models.DateTimeField(default=dynamic_logging.models.now_plus_2hours, null=True, blank=True)),
                ('last_update', models.DateTimeField(auto_now=True)),
                ('config', models.ForeignKey(related_name='triggers', to='dynamic_logging.Config', on_delete=CASCADE)),
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
