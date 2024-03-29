# Generated by Django 4.2.4 on 2024-02-11 18:44

from django.db import migrations, models
from django.contrib.postgres.operations import CreateCollation


class Migration(migrations.Migration):

    dependencies = [
        ('collection', '0221_historicaloligo_info_sheet_oligo_info_sheet'),
    ]

    operations = [
        migrations.AlterField(
            model_name='oligo',
            name='sequence',
            field=models.CharField(max_length=255, verbose_name='sequence'),
        ),
        CreateCollation(
            "case_insensitive",
            provider="icu",
            locale="und-u-ks-level2",
            deterministic=False,
        ),
        migrations.AlterField(
            model_name='oligo',
            name='sequence',
            field=models.CharField(db_collation='case_insensitive', max_length=255, unique=True, verbose_name='name'),
        ),
    ]
