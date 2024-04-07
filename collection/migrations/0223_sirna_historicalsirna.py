# Generated by Django 4.2.4 on 2024-02-18 08:46

import common.models
from django.conf import settings
import django.contrib.postgres.fields
from django.db import migrations, models
import django.db.models.deletion
import django_better_admin_arrayfield.models.fields
import simple_history.models


class Migration(migrations.Migration):

    dependencies = [
        ('formz', '0082_auto_20230104_1520'),
        ('ordering', '0057_alter_historicalorder_options_and_more'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('collection', '0222_alter_historicaloligo_sequence_alter_oligo_sequence'),
    ]

    operations = [
        migrations.CreateModel(
            name='SiRna',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=255, verbose_name='name')),
                ('sequence', models.CharField(max_length=50, verbose_name='sequence')),
                ('supplier', models.CharField(max_length=255, verbose_name='supplier')),
                ('supplier_part_no', models.CharField(max_length=255, verbose_name='supplier Part-No')),
                ('supplier_si_rna_id', models.CharField(max_length=255, verbose_name='supplier siRNA ID')),
                ('target_genes', django_better_admin_arrayfield.models.fields.ArrayField(base_field=models.CharField(max_length=15), null=True, size=None)),
                ('locus_ids', django_better_admin_arrayfield.models.fields.ArrayField(base_field=models.CharField(max_length=15), blank=True, null=True, size=None)),
                ('description_comment', models.TextField(blank=True, help_text='Include transfection conditions, etc. here', verbose_name='description/comments')),
                ('info_sheet', models.FileField(blank=True, help_text='only .pdf files, max. 2 MB', null=True, upload_to='collection/sirna/', verbose_name='info sheet')),
                ('history_orders', django.contrib.postgres.fields.ArrayField(base_field=models.PositiveIntegerField(), blank=True, null=True, size=None, verbose_name='order')),
                ('created_date_time', models.DateTimeField(auto_now_add=True, verbose_name='created')),
                ('last_changed_date_time', models.DateTimeField(auto_now=True, verbose_name='last changed')),
                ('created_by', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to=settings.AUTH_USER_MODEL)),
                ('orders', models.ManyToManyField(blank=True, related_name='si_rna_order', to='ordering.order', verbose_name='orders')),
                ('species', models.ForeignKey(null=True, on_delete=django.db.models.deletion.PROTECT, to='formz.species', verbose_name='organism')),
            ],
            options={
                'verbose_name': 'siRNA',
                'verbose_name_plural': 'siRNAs',
            },
            bases=(models.Model, common.models.SaveWithoutHistoricalRecord),
        ),
        migrations.CreateModel(
            name='HistoricalSiRna',
            fields=[
                ('id', models.IntegerField(auto_created=True, blank=True, db_index=True, verbose_name='ID')),
                ('name', models.CharField(max_length=255, verbose_name='name')),
                ('sequence', models.CharField(max_length=50, verbose_name='sequence')),
                ('supplier', models.CharField(max_length=255, verbose_name='supplier')),
                ('supplier_part_no', models.CharField(max_length=255, verbose_name='supplier Part-No')),
                ('supplier_si_rna_id', models.CharField(max_length=255, verbose_name='supplier siRNA ID')),
                ('target_genes', django_better_admin_arrayfield.models.fields.ArrayField(base_field=models.CharField(max_length=15), null=True, size=None)),
                ('locus_ids', django_better_admin_arrayfield.models.fields.ArrayField(base_field=models.CharField(max_length=15), blank=True, null=True, size=None)),
                ('description_comment', models.TextField(blank=True, help_text='Include transfection conditions, etc. here', verbose_name='description/comments')),
                ('info_sheet', models.TextField(blank=True, help_text='only .pdf files, max. 2 MB', max_length=100, null=True, verbose_name='info sheet')),
                ('history_orders', django.contrib.postgres.fields.ArrayField(base_field=models.PositiveIntegerField(), blank=True, null=True, size=None, verbose_name='order')),
                ('created_date_time', models.DateTimeField(blank=True, editable=False, verbose_name='created')),
                ('last_changed_date_time', models.DateTimeField(blank=True, editable=False, verbose_name='last changed')),
                ('history_id', models.AutoField(primary_key=True, serialize=False)),
                ('history_date', models.DateTimeField(db_index=True)),
                ('history_change_reason', models.CharField(max_length=100, null=True)),
                ('history_type', models.CharField(choices=[('+', 'Created'), ('~', 'Changed'), ('-', 'Deleted')], max_length=1)),
                ('created_by', models.ForeignKey(blank=True, db_constraint=False, null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='+', to=settings.AUTH_USER_MODEL)),
                ('history_user', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL)),
                ('species', models.ForeignKey(blank=True, db_constraint=False, null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='+', to='formz.species', verbose_name='organism')),
            ],
            options={
                'verbose_name': 'historical siRNA',
                'verbose_name_plural': 'historical siRNAs',
                'ordering': ('-history_date', '-history_id'),
                'get_latest_by': ('history_date', 'history_id'),
            },
            bases=(simple_history.models.HistoricalChanges, models.Model),
        ),
    ]