# -*- coding: utf-8 -*-
# Generated by Django 1.11 on 2019-04-12 15:55
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('collection', '0065_auto_20190412_1751'),
    ]

    operations = [
        migrations.AddField(
            model_name='mammalianlinedoc',
            name='comment',
            field=models.CharField(blank=True, max_length=150, verbose_name='comment'),
        ),
    ]