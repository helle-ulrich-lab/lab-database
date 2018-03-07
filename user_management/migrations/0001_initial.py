# -*- coding: utf-8 -*-
# Generated by Django 1.11.2 on 2018-03-04 16:08
from __future__ import unicode_literals

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='LabUser',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('personal_order_list_url', models.URLField(max_length=255, unique=True, verbose_name='Personal order list URL')),
                ('abbreviation_code', models.CharField(max_length=4, unique=True, verbose_name='User code (Max. 4 letters)')),
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
        ),
    ]