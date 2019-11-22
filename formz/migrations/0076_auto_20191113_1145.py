# Generated by Django 2.1.13 on 2019-11-13 10:45

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('formz', '0075_auto_20191113_1122'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='formzbaseelement',
            name='displayed_name',
        ),
        migrations.AlterField(
            model_name='formzbaseelement',
            name='name',
            field=models.CharField(help_text='This is only the name displayed in the rendered FormZ form. It is NOT used for auto-detection of features in a plasmid map, only aliases (below) are used for that', max_length=255, verbose_name='name'),
        ),
    ]