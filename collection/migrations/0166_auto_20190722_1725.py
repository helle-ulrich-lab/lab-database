# Generated by Django 2.1.8 on 2019-07-22 15:25

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('collection', '0165_auto_20190722_1648'),
    ]

    operations = [
        migrations.AddField(
            model_name='mammalianlineepisomalplasmid',
            name='s2_work',
            field=models.BooleanField(default=False, verbose_name='Used for S2 work?'),
        ),
        migrations.AlterField(
            model_name='historicalmammalianline',
            name='history_documents',
            field=models.TextField(blank=True, verbose_name='documents'),
        ),
        migrations.AlterField(
            model_name='mammalianline',
            name='history_documents',
            field=models.TextField(blank=True, verbose_name='documents'),
        ),
    ]
