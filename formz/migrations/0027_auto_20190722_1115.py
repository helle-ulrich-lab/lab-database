# Generated by Django 2.1.8 on 2019-07-22 09:15

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('formz', '0026_auto_20190722_1114'),
    ]

    operations = [
        migrations.AlterField(
            model_name='formzproject',
            name='description',
            field=models.TextField(blank=True, help_text='Techniques, organisms, plasmids, etc. <i>Beschreibung der Durchführung</i>', verbose_name='Description of strategy/performance'),
        ),
    ]