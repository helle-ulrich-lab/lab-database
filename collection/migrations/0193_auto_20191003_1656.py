# Generated by Django 2.1.8 on 2019-10-03 14:56

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('collection', '0192_auto_20191003_1636'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='historicalmammalianline',
            name='organism',
        ),
        migrations.RemoveField(
            model_name='mammalianline',
            name='organism',
        ),
    ]
