# Generated by Django 2.1.8 on 2019-09-14 15:35

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('record_approval', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='recordtobeapproved',
            name='edited',
            field=models.BooleanField(blank=True, default=False, verbose_name='edited?'),
        ),
    ]
