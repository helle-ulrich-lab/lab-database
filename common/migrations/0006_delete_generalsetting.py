# Generated by Django 4.2.4 on 2023-10-26 09:46

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('common', '0005_remove_generalsetting_join_api_key'),
    ]

    operations = [
        migrations.DeleteModel(
            name='GeneralSetting',
        ),
    ]
