# Generated by Django 2.1.8 on 2019-04-21 08:44

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('collection_management', '0074_auto_20190421_1044'),
    ]

    operations = [
        migrations.AlterField(
            model_name='sacerevisiaestrain',
            name='parent_2',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='parent_strain_2', to='collection_management.SaCerevisiaeStrain', verbose_name='Parent 2'),
        ),
    ]
