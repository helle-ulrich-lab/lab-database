# -*- coding: utf-8 -*-
# Generated by Django 1.11 on 2019-04-09 10:15
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('collection', '0050_auto_20181209_1503'),
    ]

    operations = [
        migrations.AddField(
            model_name='historicalhuplasmid',
            name='plasmid_map_png',
            field=models.TextField(blank=True, max_length=100, verbose_name='Plasmid image'),
        ),
        migrations.AddField(
            model_name='huplasmid',
            name='plasmid_map_png',
            field=models.ImageField(blank=True, upload_to='collection/huplasmid/', verbose_name='Plasmid image'),
        ),
    ]
