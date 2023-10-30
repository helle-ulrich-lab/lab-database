# Generated by Django 2.1.8 on 2019-07-19 11:41

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('collection', '0152_auto_20190719_1237'),
    ]

    operations = [
        migrations.AlterField(
            model_name='historicalhuplasmid',
            name='history_formz_elements',
            field=models.TextField(blank=True, verbose_name='formZ elements'),
        ),
        migrations.AlterField(
            model_name='historicalhuplasmid',
            name='history_formz_projects',
            field=models.TextField(blank=True, verbose_name='formZ projects'),
        ),
        migrations.AlterField(
            model_name='historicalsacerevisiaestrain',
            name='history_all_plasmids_in_stocked_strain',
            field=models.TextField(blank=True, verbose_name='all plasmids in stock'),
        ),
        migrations.AlterField(
            model_name='historicalsacerevisiaestrain',
            name='history_cassette_plasmids',
            field=models.TextField(blank=True, verbose_name='cassette plasmids'),
        ),
        migrations.AlterField(
            model_name='historicalsacerevisiaestrain',
            name='history_episomal_plasmids',
            field=models.TextField(blank=True, verbose_name='episomal plasmids'),
        ),
        migrations.AlterField(
            model_name='historicalsacerevisiaestrain',
            name='history_formz_projects',
            field=models.TextField(blank=True, verbose_name='formZ projects'),
        ),
        migrations.AlterField(
            model_name='historicalsacerevisiaestrain',
            name='history_integrated_plasmids',
            field=models.TextField(blank=True, verbose_name='integrated plasmid'),
        ),
        migrations.AlterField(
            model_name='huplasmid',
            name='history_formz_elements',
            field=models.TextField(blank=True, verbose_name='formZ elements'),
        ),
        migrations.AlterField(
            model_name='huplasmid',
            name='history_formz_projects',
            field=models.TextField(blank=True, verbose_name='formZ projects'),
        ),
        migrations.AlterField(
            model_name='sacerevisiaestrain',
            name='history_all_plasmids_in_stocked_strain',
            field=models.TextField(blank=True, verbose_name='all plasmids in stock'),
        ),
        migrations.AlterField(
            model_name='sacerevisiaestrain',
            name='history_cassette_plasmids',
            field=models.TextField(blank=True, verbose_name='cassette plasmids'),
        ),
        migrations.AlterField(
            model_name='sacerevisiaestrain',
            name='history_episomal_plasmids',
            field=models.TextField(blank=True, verbose_name='episomal plasmids'),
        ),
        migrations.AlterField(
            model_name='sacerevisiaestrain',
            name='history_formz_projects',
            field=models.TextField(blank=True, verbose_name='formZ projects'),
        ),
        migrations.AlterField(
            model_name='sacerevisiaestrain',
            name='history_integrated_plasmids',
            field=models.TextField(blank=True, verbose_name='integrated plasmid'),
        ),
    ]