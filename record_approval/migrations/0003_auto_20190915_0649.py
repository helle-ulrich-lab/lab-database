# Generated by Django 2.1.8 on 2019-09-15 04:49

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('record_approval', '0002_auto_20190914_1735'),
    ]

    operations = [
        migrations.AlterField(
            model_name='recordtobeapproved',
            name='message_date',
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
