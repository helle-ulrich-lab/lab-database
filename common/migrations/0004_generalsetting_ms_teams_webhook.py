# Generated by Django 2.2.13 on 2020-10-03 09:53

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('common', '0003_auto_20200129_1333'),
    ]

    operations = [
        migrations.AddField(
            model_name='generalsetting',
            name='ms_teams_webhook',
            field=models.URLField(blank=True, max_length=500, verbose_name='MS Teams webhook'),
        ),
    ]
