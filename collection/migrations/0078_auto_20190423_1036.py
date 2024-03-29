# Generated by Django 2.1.8 on 2019-04-23 08:36

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('collection', '0077_auto_20190421_1050'),
    ]

    operations = [
        migrations.AlterField(
            model_name='historicalsacerevisiaestrain',
            name='parental_strain',
            field=models.CharField(blank=True, help_text="Use only when 'Parent 1' does not apply", max_length=255, verbose_name='parental strain'),
        ),
        migrations.AlterField(
            model_name='sacerevisiaestrain',
            name='parent_1',
            field=models.ForeignKey(blank=True, help_text='Main parental strain', null=True, on_delete=django.db.models.deletion.PROTECT, related_name='parent_strain_1', to='collection.SaCerevisiaeStrain', verbose_name='Parent 1'),
        ),
        migrations.AlterField(
            model_name='sacerevisiaestrain',
            name='parent_2',
            field=models.ForeignKey(blank=True, help_text='Only for crosses', null=True, on_delete=django.db.models.deletion.PROTECT, related_name='parent_strain_2', to='collection.SaCerevisiaeStrain', verbose_name='Parent 2'),
        ),
        migrations.AlterField(
            model_name='sacerevisiaestrain',
            name='parental_strain',
            field=models.CharField(blank=True, help_text="Use only when 'Parent 1' does not apply", max_length=255, verbose_name='parental strain'),
        ),
    ]
