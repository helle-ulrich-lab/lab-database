# -*- coding: utf-8 -*-
# Generated by Django 1.11.2 on 2018-07-06 13:16
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('collection', '0036_auto_20180706_1515'),
    ]

    operations = [
        migrations.AddField(
            model_name='historicalmammalianline',
            name='parental_line',
            field=models.CharField(default='', max_length=255, verbose_name='Box'),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='mammalianline',
            name='parental_line',
            field=models.CharField(default='-', max_length=255, verbose_name='Box'),
            preserve_default=False,
        ),
    ]
