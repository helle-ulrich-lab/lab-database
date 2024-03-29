# Generated by Django 2.1.13 on 2019-11-17 15:21

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('formz', '0078_auto_20191117_1549'),
        ('collection', '0197_auto_20191031_1102'),
    ]

    operations = [
        migrations.AddField(
            model_name='ecolistrain',
            name='destroyed_date',
            field=models.DateField(blank=True, null=True, verbose_name='destroyed'),
        ),
        migrations.AddField(
            model_name='ecolistrain',
            name='formz_elements',
            field=models.ManyToManyField(blank=True, related_name='coli_formz_element', to='formz.FormZBaseElement', verbose_name='elements'),
        ),
        migrations.AddField(
            model_name='ecolistrain',
            name='history_formz_elements',
            field=models.TextField(blank=True, verbose_name='formz elements'),
        ),
        migrations.AddField(
            model_name='ecolistrain',
            name='history_formz_gentech_methods',
            field=models.TextField(blank=True, verbose_name='genTech methods'),
        ),
        migrations.AddField(
            model_name='ecolistrain',
            name='history_formz_projects',
            field=models.TextField(blank=True, verbose_name='formZ projects'),
        ),
        migrations.AddField(
            model_name='historicalecolistrain',
            name='destroyed_date',
            field=models.DateField(blank=True, null=True, verbose_name='destroyed'),
        ),
        migrations.AddField(
            model_name='historicalecolistrain',
            name='history_formz_elements',
            field=models.TextField(blank=True, verbose_name='formz elements'),
        ),
        migrations.AddField(
            model_name='historicalecolistrain',
            name='history_formz_gentech_methods',
            field=models.TextField(blank=True, verbose_name='genTech methods'),
        ),
        migrations.AddField(
            model_name='historicalecolistrain',
            name='history_formz_projects',
            field=models.TextField(blank=True, verbose_name='formZ projects'),
        ),
    ]
