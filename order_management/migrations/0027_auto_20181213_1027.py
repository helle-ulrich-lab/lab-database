# -*- coding: utf-8 -*-
# Generated by Django 1.11 on 2018-12-13 09:27
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('order_management', '0026_auto_20181209_1531'),
    ]

    operations = [
        migrations.AddField(
            model_name='costunit',
            name='status',
            field=models.BooleanField(default=False, verbose_name='Deactivate?'),
        ),
        migrations.AddField(
            model_name='location',
            name='status',
            field=models.BooleanField(default=False, verbose_name='Deactivate?'),
        ),
    ]