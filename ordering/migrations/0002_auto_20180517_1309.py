# -*- coding: utf-8 -*-
# Generated by Django 1.11.2 on 2018-05-17 11:09
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('ordering', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='order',
            name='cost_unit',
            field=models.ForeignKey(default=1, on_delete=django.db.models.deletion.CASCADE, to='ordering.CostUnit'),
        ),
    ]
