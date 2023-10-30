# Generated by Django 2.1.8 on 2019-07-23 14:19

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('collection', '0170_auto_20190722_1845'),
    ]

    operations = [
        migrations.AlterField(
            model_name='historicalhuplasmid',
            name='vector_zkbs',
            field=models.ForeignKey(blank=True, db_constraint=False, help_text='<a href="/formz/zkbsplasmid/" target="_blank">View</a>', null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='+', to='formz.ZkbsPlasmid', verbose_name='ZKBS database vector'),
        ),
        migrations.AlterField(
            model_name='historicalmammalianline',
            name='zkbs_cell_line',
            field=models.ForeignKey(blank=True, db_constraint=False, help_text='<a href="/formz/zkbscellline/" target="_blank">View</a>', null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='+', to='formz.ZkbsCellLine', verbose_name='ZKBS database cell line'),
        ),
        migrations.AlterField(
            model_name='huplasmid',
            name='vector_zkbs',
            field=models.ForeignKey(blank=True, help_text='<a href="/formz/zkbsplasmid/" target="_blank">View</a>', null=True, on_delete=django.db.models.deletion.PROTECT, to='formz.ZkbsPlasmid', verbose_name='ZKBS database vector'),
        ),
        migrations.AlterField(
            model_name='mammalianline',
            name='zkbs_cell_line',
            field=models.ForeignKey(blank=True, help_text='<a href="/formz/zkbscellline/" target="_blank">View</a>', null=True, on_delete=django.db.models.deletion.PROTECT, to='formz.ZkbsCellLine', verbose_name='ZKBS database cell line'),
        ),
    ]