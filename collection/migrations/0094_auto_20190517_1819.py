# Generated by Django 2.1.8 on 2019-05-17 16:19

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('collection', '0093_auto_20190517_1816'),
    ]

    operations = [
        migrations.AlterField(
            model_name='sacerevisiaestrainepisomalplasmid',
            name='created_date',
            field=models.DateField(),
        ),
        migrations.AlterField(
            model_name='sacerevisiaestrainepisomalplasmid',
            name='huplasmid',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='collection.HuPlasmid', verbose_name='Plasmid'),
        ),
    ]
