# Generated by Django 2.1.8 on 2019-05-22 13:21

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('collection_management', '0115_auto_20190522_1520'),
    ]

    operations = [
        migrations.AlterField(
            model_name='historicalsacerevisiaestrain',
            name='name',
            field=models.CharField(max_length=255, verbose_name='name'),
        ),
        migrations.AlterField(
            model_name='sacerevisiaestrain',
            name='name',
            field=models.CharField(max_length=255, verbose_name='name'),
        ),
    ]
