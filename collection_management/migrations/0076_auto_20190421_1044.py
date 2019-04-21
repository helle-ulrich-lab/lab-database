# Generated by Django 2.1.8 on 2019-04-21 08:44

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('collection_management', '0075_auto_20190421_1044'),
    ]

    operations = [
        migrations.AlterField(
            model_name='sacerevisiaestrain',
            name='cassette_plasmids',
            field=models.ManyToManyField(blank=True, help_text='Tagging and knock out plasmids', related_name='cassette_pl', to='collection_management.HuPlasmid'),
        ),
    ]
