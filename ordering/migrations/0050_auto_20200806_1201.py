# Generated by Django 2.2.13 on 2020-08-06 10:01

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('ordering', '0049_auto_20200806_1051'),
    ]

    operations = [
        migrations.AlterField(
            model_name='historicalorder',
            name='msds_form',
            field=models.ForeignKey(blank=True, db_constraint=False, null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='+', to='ordering.MsdsForm', verbose_name='MSDS form'),
        ),
        migrations.AlterField(
            model_name='order',
            name='msds_form',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, to='ordering.MsdsForm', verbose_name='MSDS form'),
        ),
    ]