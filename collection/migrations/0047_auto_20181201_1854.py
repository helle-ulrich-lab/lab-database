# -*- coding: utf-8 -*-
# Generated by Django 1.11 on 2018-12-01 17:54
from __future__ import unicode_literals

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('collection', '0046_auto_20181201_1854'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='archenoahanimal',
            name='content_type',
        ),
        migrations.DeleteModel(
            name='ArcheNoahAnimal',
        ),
    ]
