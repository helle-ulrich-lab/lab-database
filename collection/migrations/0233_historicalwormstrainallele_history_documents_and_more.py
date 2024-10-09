# Generated by Django 4.2.4 on 2024-10-07 09:34

import django.contrib.postgres.fields
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("collection", "0232_alter_cellline_organism"),
    ]

    operations = [
        migrations.AddField(
            model_name="historicalwormstrainallele",
            name="history_documents",
            field=django.contrib.postgres.fields.ArrayField(
                base_field=models.PositiveIntegerField(),
                blank=True,
                default=list,
                null=True,
                size=None,
                verbose_name="documents",
            ),
        ),
        migrations.AddField(
            model_name="wormstrainallele",
            name="history_documents",
            field=django.contrib.postgres.fields.ArrayField(
                base_field=models.PositiveIntegerField(),
                blank=True,
                default=list,
                null=True,
                size=None,
                verbose_name="documents",
            ),
        ),
        migrations.CreateModel(
            name="WormStrainAlleleDoc",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "name",
                    models.FileField(
                        null=True, upload_to="temp/", verbose_name="file name"
                    ),
                ),
                (
                    "description",
                    models.CharField(max_length=50, verbose_name="description"),
                ),
                (
                    "comment",
                    models.CharField(
                        blank=True, max_length=150, verbose_name="comment"
                    ),
                ),
                (
                    "created_date_time",
                    models.DateTimeField(auto_now_add=True, verbose_name="created"),
                ),
                (
                    "last_changed_date_time",
                    models.DateTimeField(auto_now=True, verbose_name="last changed"),
                ),
                (
                    "worm_strain_allele",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        to="collection.wormstrainallele",
                    ),
                ),
            ],
            options={
                "verbose_name": "worm strain allele document",
            },
        ),
    ]
