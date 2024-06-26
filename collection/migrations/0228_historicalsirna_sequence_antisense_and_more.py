# Generated by Django 4.2.4 on 2024-04-07 20:07

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('collection', '0227_alter_antibody_history_documents_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='historicalsirna',
            name='sequence_antisense',
            field=models.CharField(default='', max_length=50, verbose_name='sequence - Antisense strand'),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='sirna',
            name='sequence_antisense',
            field=models.CharField(default='', max_length=50, verbose_name='sequence - Antisense strand'),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='historicalsirna',
            name='sequence',
            field=models.CharField(max_length=50, verbose_name='sequence - Sense strand'),
        ),
        migrations.AlterField(
            model_name='sirna',
            name='sequence',
            field=models.CharField(max_length=50, verbose_name='sequence - Sense strand'),
        ),
    ]
