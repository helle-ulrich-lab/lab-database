# Generated by Django 2.1.8 on 2019-07-18 08:44

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('collection', '0150_auto_20190716_1759'),
    ]

    operations = [
        migrations.AlterField(
            model_name='historicalsacerevisiaestrain',
            name='mating_type',
            field=models.CharField(blank=True, choices=[('a', 'a'), ('alpha', 'alpha'), ('unknown', 'unknown'), ('a/a', 'a/a'), ('alpha/alpha', 'alpha/alpha'), ('a/alpha', 'a/alpha'), ('other', 'other')], max_length=20, verbose_name='mating type'),
        ),
        migrations.AlterField(
            model_name='mammalianlinedoc',
            name='typ_e',
            field=models.CharField(choices=[('virus', 'Virus test'), ('mycoplasma', 'Mycoplasma test'), ('fingerprint', 'Fingerprinting'), ('other', 'Other')], max_length=255, verbose_name='doc type'),
        ),
        migrations.AlterField(
            model_name='sacerevisiaestrain',
            name='mating_type',
            field=models.CharField(blank=True, choices=[('a', 'a'), ('alpha', 'alpha'), ('unknown', 'unknown'), ('a/a', 'a/a'), ('alpha/alpha', 'alpha/alpha'), ('a/alpha', 'a/alpha'), ('other', 'other')], max_length=20, verbose_name='mating type'),
        ),
    ]
