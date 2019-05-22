# Generated by Django 2.1.8 on 2019-05-22 14:21

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('collection_management', '0127_auto_20190522_1621'),
    ]

    operations = [
        migrations.AlterField(
            model_name='historicalscpombestrain',
            name='auxotrophic_marker',
            field=models.CharField(blank=True, max_length=255, verbose_name='auxotrophic markers'),
        ),
        migrations.AlterField(
            model_name='historicalscpombestrain',
            name='box_number',
            field=models.SmallIntegerField(verbose_name='box number'),
        ),
        migrations.AlterField(
            model_name='historicalscpombestrain',
            name='comment',
            field=models.CharField(blank=True, max_length=300, verbose_name='comments'),
        ),
        migrations.AlterField(
            model_name='historicalscpombestrain',
            name='mating_type',
            field=models.CharField(blank=True, max_length=20, verbose_name='mating type'),
        ),
        migrations.AlterField(
            model_name='historicalscpombestrain',
            name='name',
            field=models.TextField(verbose_name='genotype'),
        ),
        migrations.AlterField(
            model_name='historicalscpombestrain',
            name='parental_strain',
            field=models.CharField(blank=True, max_length=255, verbose_name='parental strains'),
        ),
        migrations.AlterField(
            model_name='historicalscpombestrain',
            name='phenotype',
            field=models.CharField(blank=True, max_length=255, verbose_name='phenotype'),
        ),
        migrations.AlterField(
            model_name='historicalscpombestrain',
            name='received_from',
            field=models.CharField(blank=True, max_length=255, verbose_name='received from'),
        ),
        migrations.AlterField(
            model_name='scpombestrain',
            name='auxotrophic_marker',
            field=models.CharField(blank=True, max_length=255, verbose_name='auxotrophic markers'),
        ),
        migrations.AlterField(
            model_name='scpombestrain',
            name='box_number',
            field=models.SmallIntegerField(verbose_name='box number'),
        ),
        migrations.AlterField(
            model_name='scpombestrain',
            name='comment',
            field=models.CharField(blank=True, max_length=300, verbose_name='comments'),
        ),
        migrations.AlterField(
            model_name='scpombestrain',
            name='mating_type',
            field=models.CharField(blank=True, max_length=20, verbose_name='mating type'),
        ),
        migrations.AlterField(
            model_name='scpombestrain',
            name='name',
            field=models.TextField(verbose_name='genotype'),
        ),
        migrations.AlterField(
            model_name='scpombestrain',
            name='parental_strain',
            field=models.CharField(blank=True, max_length=255, verbose_name='parental strains'),
        ),
        migrations.AlterField(
            model_name='scpombestrain',
            name='phenotype',
            field=models.CharField(blank=True, max_length=255, verbose_name='phenotype'),
        ),
        migrations.AlterField(
            model_name='scpombestrain',
            name='received_from',
            field=models.CharField(blank=True, max_length=255, verbose_name='received from'),
        ),
    ]
