# Generated by Django 2.2.9 on 2020-01-19 15:00

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('collection_management', '0209_auto_20191220_0959'),
    ]

    operations = [
        migrations.AlterField(
            model_name='ecolistrain',
            name='formz_projects',
            field=models.ManyToManyField(related_name='coli_formz_project', to='formz.FormZProject', verbose_name='formZ projects'),
        ),
        migrations.AlterField(
            model_name='historicalplasmid',
            name='map_gbk',
            field=models.TextField(blank=True, help_text='only .gbk or .gb files, max. 2 MB', max_length=100, verbose_name='plasmid map (.gbk)'),
        ),
        migrations.AlterField(
            model_name='plasmid',
            name='map_gbk',
            field=models.FileField(blank=True, help_text='only .gbk or .gb files, max. 2 MB', upload_to='collection_management/plasmid/gbk/', verbose_name='plasmid map (.gbk)'),
        ),
    ]