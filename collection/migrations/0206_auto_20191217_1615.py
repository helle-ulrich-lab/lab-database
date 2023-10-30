# Generated by Django 2.2.7 on 2019-12-17 15:15

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('collection', '0205_auto_20191127_1435'),
    ]

    operations = [
        migrations.AlterField(
            model_name='historicalplasmid',
            name='map',
            field=models.TextField(blank=True, help_text='only .dna files, max. 2 MB', max_length=100, verbose_name='plasmid map (.dna)'),
        ),
        migrations.AlterField(
            model_name='historicalplasmid',
            name='map_gbk',
            field=models.TextField(blank=True, help_text='only .dna files, max. 2 MB', max_length=100, verbose_name='plasmid map (.gbk)'),
        ),
        migrations.AlterField(
            model_name='plasmid',
            name='map',
            field=models.FileField(blank=True, help_text='only .dna files, max. 2 MB', upload_to='collection/plasmid/dna/', verbose_name='plasmid map (.dna)'),
        ),
        migrations.AlterField(
            model_name='plasmid',
            name='map_gbk',
            field=models.FileField(blank=True, help_text='only .dna files, max. 2 MB', upload_to='collection/plasmid/gbk/', verbose_name='plasmid map (.gbk)'),
        ),
    ]