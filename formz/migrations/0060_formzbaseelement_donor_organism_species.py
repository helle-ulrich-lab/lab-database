# Generated by Django 2.1.8 on 2019-10-03 13:14

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('formz', '0059_species'),
    ]

    operations = [
        migrations.AddField(
            model_name='formzbaseelement',
            name='donor_organism_species',
            field=models.ManyToManyField(to='formz.Species'),
        ),
    ]