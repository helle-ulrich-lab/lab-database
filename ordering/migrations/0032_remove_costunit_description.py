# -*- coding: utf-8 -*-
# Generated by Django 1.11 on 2019-01-13 07:44
from __future__ import unicode_literals

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('ordering', '0031_auto_20190113_0843'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='costunit',
            name='description',
        ),
    ]