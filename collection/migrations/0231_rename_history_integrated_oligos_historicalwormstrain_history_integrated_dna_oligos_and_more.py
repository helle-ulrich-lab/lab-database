# Generated by Django 4.2.4 on 2024-07-25 07:51

from django.conf import settings
import django.contrib.postgres.fields
from django.db import migrations, models
import django.db.models.deletion
import simple_history.models


class Migration(migrations.Migration):

    dependencies = [
        ('formz', '0082_auto_20230104_1520'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('collection', '0230_alter_historicalsirna_locus_ids_and_more'),
    ]

    operations = [
        migrations.RenameField(
            model_name='historicalwormstrain',
            old_name='history_integrated_oligos',
            new_name='history_integrated_dna_oligos',
        ),
        migrations.RenameField(
            model_name='historicalwormstrain',
            old_name='history_integrated_plasmids',
            new_name='history_integrated_dna_plasmids',
        ),
        migrations.RenameField(
            model_name='wormstrain',
            old_name='history_integrated_oligos',
            new_name='history_integrated_dna_oligos',
        ),
        migrations.RenameField(
            model_name='wormstrain',
            old_name='history_integrated_plasmids',
            new_name='history_integrated_dna_plasmids',
        ),
        migrations.AddField(
            model_name='historicalwormstrain',
            name='history_alleles',
            field=django.contrib.postgres.fields.ArrayField(base_field=models.PositiveIntegerField(), blank=True, default=list, null=True, size=None, verbose_name='alleles'),
        ),
        migrations.AddField(
            model_name='wormstrain',
            name='history_alleles',
            field=django.contrib.postgres.fields.ArrayField(base_field=models.PositiveIntegerField(), blank=True, default=list, null=True, size=None, verbose_name='alleles'),
        ),
        migrations.CreateModel(
            name='WormStrainAllele',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('lab_identifier', models.CharField(choices=[('xf', 'xf'), ('xfls', 'xfls')], default='xf', max_length=15, verbose_name='prefix/Lab identifier')),
                ('typ_e', models.CharField(choices=[('t', 'Transgene'), ('m', 'Mutation')], max_length=5, verbose_name='type')),
                ('transgene', models.CharField(blank=True, max_length=255, verbose_name='transgene')),
                ('transgene_position', models.CharField(blank=True, max_length=255, verbose_name='transgene position')),
                ('transgene_plasmids', models.CharField(blank=True, max_length=255, verbose_name='Transgene plasmids')),
                ('mutation', models.CharField(blank=True, max_length=255, verbose_name='mutation')),
                ('mutation_type', models.CharField(blank=True, max_length=255, verbose_name='mutation type')),
                ('mutation_position', models.CharField(blank=True, max_length=255, verbose_name='mutation position')),
                ('made_by_person', models.CharField(max_length=255, verbose_name='made by person')),
                ('note', models.CharField(blank=True, max_length=255, verbose_name='note')),
                ('map', models.FileField(blank=True, help_text='only SnapGene .dna files, max. 2 MB', upload_to='collection/wormstrainallele/dna/', verbose_name='map (.dna)')),
                ('map_png', models.ImageField(blank=True, upload_to='collection/wormstrainallele/png/', verbose_name='map (.png)')),
                ('map_gbk', models.FileField(blank=True, help_text='only .gbk or .gb files, max. 2 MB', upload_to='collection/wormstrainallele/gbk/', verbose_name='Map (.gbk)')),
                ('created_date_time', models.DateTimeField(auto_now_add=True, verbose_name='created')),
                ('last_changed_date_time', models.DateTimeField(auto_now=True, verbose_name='last changed')),
                ('history_formz_elements', django.contrib.postgres.fields.ArrayField(base_field=models.PositiveIntegerField(), blank=True, default=list, null=True, size=None, verbose_name='formz elements')),
                ('created_by', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='wormstrainallele_createdby_user', to=settings.AUTH_USER_MODEL)),
                ('formz_elements', models.ManyToManyField(blank=True, help_text='Searching against the aliases of an element is case-sensitive. <a href="/formz/formzbaseelement/" target="_blank">View all/Change</a>', to='formz.formzbaseelement', verbose_name='elements')),
                ('made_by_method', models.ForeignKey(help_text='The methods used to create the allele', on_delete=django.db.models.deletion.PROTECT, related_name='allele_worm_method', to='formz.gentechmethod', verbose_name='made by method')),
                ('reference_strain', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='allele_worm_reference_strain', to='collection.wormstrain', verbose_name='reference strain')),
            ],
            options={
                'verbose_name': 'allele - Worm',
                'verbose_name_plural': 'alleles - Worm',
            },
        ),
        migrations.CreateModel(
            name='HistoricalWormStrainAllele',
            fields=[
                ('id', models.IntegerField(auto_created=True, blank=True, db_index=True, verbose_name='ID')),
                ('lab_identifier', models.CharField(choices=[('xf', 'xf'), ('xfls', 'xfls')], default='xf', max_length=15, verbose_name='prefix/Lab identifier')),
                ('typ_e', models.CharField(choices=[('t', 'Transgene'), ('m', 'Mutation')], max_length=5, verbose_name='type')),
                ('transgene', models.CharField(blank=True, max_length=255, verbose_name='transgene')),
                ('transgene_position', models.CharField(blank=True, max_length=255, verbose_name='transgene position')),
                ('transgene_plasmids', models.CharField(blank=True, max_length=255, verbose_name='Transgene plasmids')),
                ('mutation', models.CharField(blank=True, max_length=255, verbose_name='mutation')),
                ('mutation_type', models.CharField(blank=True, max_length=255, verbose_name='mutation type')),
                ('mutation_position', models.CharField(blank=True, max_length=255, verbose_name='mutation position')),
                ('made_by_person', models.CharField(max_length=255, verbose_name='made by person')),
                ('note', models.CharField(blank=True, max_length=255, verbose_name='note')),
                ('map', models.TextField(blank=True, help_text='only SnapGene .dna files, max. 2 MB', max_length=100, verbose_name='map (.dna)')),
                ('map_png', models.TextField(blank=True, max_length=100, verbose_name='map (.png)')),
                ('map_gbk', models.TextField(blank=True, help_text='only .gbk or .gb files, max. 2 MB', max_length=100, verbose_name='Map (.gbk)')),
                ('created_date_time', models.DateTimeField(blank=True, editable=False, verbose_name='created')),
                ('last_changed_date_time', models.DateTimeField(blank=True, editable=False, verbose_name='last changed')),
                ('history_formz_elements', django.contrib.postgres.fields.ArrayField(base_field=models.PositiveIntegerField(), blank=True, default=list, null=True, size=None, verbose_name='formz elements')),
                ('history_id', models.AutoField(primary_key=True, serialize=False)),
                ('history_date', models.DateTimeField(db_index=True)),
                ('history_change_reason', models.CharField(max_length=100, null=True)),
                ('history_type', models.CharField(choices=[('+', 'Created'), ('~', 'Changed'), ('-', 'Deleted')], max_length=1)),
                ('created_by', models.ForeignKey(blank=True, db_constraint=False, null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='+', to=settings.AUTH_USER_MODEL)),
                ('history_user', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL)),
                ('made_by_method', models.ForeignKey(blank=True, db_constraint=False, help_text='The methods used to create the allele', null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='+', to='formz.gentechmethod', verbose_name='made by method')),
                ('reference_strain', models.ForeignKey(blank=True, db_constraint=False, null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='+', to='collection.wormstrain', verbose_name='reference strain')),
            ],
            options={
                'verbose_name': 'historical allele - Worm',
                'verbose_name_plural': 'historical alleles - Worm',
                'ordering': ('-history_date', '-history_id'),
                'get_latest_by': ('history_date', 'history_id'),
            },
            bases=(simple_history.models.HistoricalChanges, models.Model),
        ),
        migrations.AddField(
            model_name='wormstrain',
            name='alleles',
            field=models.ManyToManyField(blank=True, related_name='worm_alleles', to='collection.wormstrainallele', verbose_name='alleles'),
        ),
    ]