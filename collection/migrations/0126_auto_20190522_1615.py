# Generated by Django 2.1.8 on 2019-05-22 14:15

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('collection', '0125_auto_20190522_1614'),
    ]

    operations = [
        migrations.AlterField(
            model_name='historicaloligo',
            name='comment',
            field=models.CharField(blank=True, max_length=255, verbose_name='comments'),
        ),
        migrations.AlterField(
            model_name='historicaloligo',
            name='description',
            field=models.TextField(blank=True, verbose_name='description'),
        ),
        migrations.AlterField(
            model_name='historicaloligo',
            name='gene',
            field=models.CharField(blank=True, max_length=255, verbose_name='gene'),
        ),
        migrations.AlterField(
            model_name='historicaloligo',
            name='length',
            field=models.SmallIntegerField(null=True, verbose_name='length'),
        ),
        migrations.AlterField(
            model_name='historicaloligo',
            name='name',
            field=models.CharField(db_index=True, max_length=255, verbose_name='name'),
        ),
        migrations.AlterField(
            model_name='historicaloligo',
            name='restriction_site',
            field=models.CharField(blank=True, max_length=255, verbose_name='restriction sites'),
        ),
        migrations.AlterField(
            model_name='historicaloligo',
            name='sequence',
            field=models.CharField(db_index=True, max_length=255, verbose_name='sequence'),
        ),
        migrations.AlterField(
            model_name='historicaloligo',
            name='us_e',
            field=models.CharField(blank=True, max_length=255, verbose_name='use'),
        ),
        migrations.AlterField(
            model_name='oligo',
            name='comment',
            field=models.CharField(blank=True, max_length=255, verbose_name='comments'),
        ),
        migrations.AlterField(
            model_name='oligo',
            name='description',
            field=models.TextField(blank=True, verbose_name='description'),
        ),
        migrations.AlterField(
            model_name='oligo',
            name='gene',
            field=models.CharField(blank=True, max_length=255, verbose_name='gene'),
        ),
        migrations.AlterField(
            model_name='oligo',
            name='length',
            field=models.SmallIntegerField(null=True, verbose_name='length'),
        ),
        migrations.AlterField(
            model_name='oligo',
            name='name',
            field=models.CharField(max_length=255, unique=True, verbose_name='name'),
        ),
        migrations.AlterField(
            model_name='oligo',
            name='restriction_site',
            field=models.CharField(blank=True, max_length=255, verbose_name='restriction sites'),
        ),
        migrations.AlterField(
            model_name='oligo',
            name='sequence',
            field=models.CharField(max_length=255, unique=True, verbose_name='sequence'),
        ),
        migrations.AlterField(
            model_name='oligo',
            name='us_e',
            field=models.CharField(blank=True, max_length=255, verbose_name='use'),
        ),
    ]