# Generated by Django 3.2.14 on 2022-07-21 11:39

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('extend_user', '0006_rename_identifier_labuser_oidc_identifier'),
    ]

    operations = [
        migrations.AlterField(
            model_name='labuser',
            name='oidc_identifier',
            field=models.CharField(blank=True, default=None, max_length=255, null=True, unique=True, verbose_name='OIDC identifier'),
        ),
    ]