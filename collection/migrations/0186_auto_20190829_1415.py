# Generated by Django 2.1.8 on 2019-08-29 12:15

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('collection', '0185_auto_20190828_1400'),
    ]

    operations = [
        migrations.AlterField(
            model_name='huplasmid',
            name='formz_ecoli_strains',
            field=models.ManyToManyField(blank=True, default=14, related_name='plasmid_ecoli_strains', to='collection.EColiStrain', verbose_name='e. coli strains'),
        ),
    ]
