# Generated by Django 2.1.8 on 2019-09-14 14:48

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('formz', '0051_auto_20190914_1613'),
    ]

    operations = [
        migrations.RenameField(
            model_name='formzusers',
            old_name='start_work_date',
            new_name='beginning_work_date',
        ),
    ]