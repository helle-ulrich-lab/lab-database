# Generated by Django 2.1.8 on 2019-05-19 06:48

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('formz', '0008_auto_20190417_1854'),
        ('collection', '0094_auto_20190517_1819'),
    ]

    operations = [
        migrations.AddField(
            model_name='sacerevisiaestrainepisomalplasmid',
            name='form_project',
            field=models.ManyToManyField(blank=True, related_name='sc_epi_plasmid', to='formz.FormZProject'),
        ),
    ]
