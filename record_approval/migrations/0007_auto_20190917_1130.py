# Generated by Django 2.1.8 on 2019-09-17 09:30

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('record_approval', '0006_auto_20190917_1129'),
    ]

    operations = [
        migrations.AlterField(
            model_name='recordtobeapproved',
            name='message',
            field=models.TextField(blank=True, help_text='Max. 255 characters', max_length=255, verbose_name='message'),
        ),
    ]
