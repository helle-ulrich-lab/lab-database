# Generated by Django 2.1.8 on 2019-07-18 12:46

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('formz', '0014_auto_20190718_1116'),
    ]

    operations = [
        migrations.AddField(
            model_name='formzbaseelement',
            name='common_feature',
            field=models.BooleanField(blank=True, default=True, verbose_name='is this a common plasmid feature?'),
            preserve_default=False,
        ),
    ]