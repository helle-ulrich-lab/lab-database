from ..models.si_rna import SiRna
from ordering.models import Order
from formz.models import Species
from .admin import FieldLastChanged
from .admin import FieldCreated
from common.shared_elements import SearchFieldOptLastname
from common.shared_elements import SearchFieldOptUsername
from common.shared_elements import AdminChangeFormWithNavigation
from common.shared_elements import SimpleHistoryWithSummaryAdmin
from django.http import HttpResponse
from django.utils.safestring import mark_safe
from django.forms import TextInput
from django.db.models import CharField
from django.contrib.auth.models import User

from djangoql.schema import DjangoQLSchema
from djangoql.admin import DjangoQLSearchMixin
from import_export import resources
from django_better_admin_arrayfield.admin.mixins import DynamicArrayMixin
from import_export.fields import Field

import xlrd
import csv
import os
from datetime import datetime

from django.conf import settings
MEDIA_ROOT = settings.MEDIA_ROOT
LAB_ABBREVIATION_FOR_FILES = getattr(
    settings, 'LAB_ABBREVIATION_FOR_FILES', '')


class SearchFieldOptUsernameSiRna(SearchFieldOptUsername):

    id_list = SiRna.objects.all().values_list('created_by', flat=True).distinct()


class SearchFieldOptLastnameSiRna(SearchFieldOptLastname):

    id_list = SiRna.objects.all().values_list('created_by', flat=True).distinct()


class SiRnaQLSchema(DjangoQLSchema):
    '''Customize search functionality'''

    def get_fields(self, model):
        '''Define fields that can be searched'''

        if model == SiRna:
            return ['id', 'name', 'sequence', 'supplier', 'supplier_part_no',
                    'supplier_si_rna_id', 'species', 'target_genes', 'locus_ids',
                    'description_comment', 'info_sheet', 'created_by', FieldCreated(),
                    FieldLastChanged(),]
        elif model == User:
            return [SearchFieldOptUsernameSiRna(), SearchFieldOptLastnameSiRna()]
        return super(SiRnaQLSchema, self).get_fields(model)


class SiRnaExportResource(resources.ModelResource):
    """Defines a custom export resource class for SiRna"""

    species_name = Field()

    def dehydrate_species_name(self, si_rna):

        return str(si_rna.species)

    class Meta:
        model = SiRna
        fields = ('id', 'name', 'sequence', 'supplier', 'supplier_part_no',
                  'supplier_si_rna_id', 'species_name', 'target_genes', 'locus_ids',
                  'description_comment', 'info_sheet', 'orders', 'created_date_time',
                  'created_by__username',)
        export_order = ('id', 'name', 'sequence', 'supplier', 'supplier_part_no',
                        'supplier_si_rna_id', 'species_name', 'target_genes', 'locus_ids',
                        'description_comment', 'info_sheet', 'orders', 'created_date_time',
                        'created_by__username',)


def export_si_rna(modeladmin, request, queryset):
    """Export SiRna"""

    export_data = SiRnaExportResource().export(queryset)

    file_format = request.POST.get('format', default='xlsx')

    if file_format == 'xlsx':
        response = HttpResponse(
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        response['Content-Disposition'] = f'attachment; filename="{queryset.model.__name__}_' + \
                                          f'{datetime.now().strftime("%Y%m%d")}_' + \
                                          f'{datetime.now().strftime("%H%M%S")}.xlsx'
        response.write(export_data.xlsx)
    elif file_format == 'tsv':
        response = HttpResponse(content_type='text/tab-separated-values')
        response['Content-Disposition'] = f'attachment; filename="{queryset.model.__name__}_' + \
                                          f'{datetime.now().strftime("%Y%m%d")}_' + \
                                          f'{datetime.now().strftime("%H%M%S")}.tsv'
        xlsx_file = xlrd.open_workbook(file_contents=export_data.xlsx)
        sheet = xlsx_file.sheet_by_index(0)
        wr = csv.writer(response, delimiter="\t")
        for rownum in range(sheet.nrows):
            row_values = [str(i).replace("\n", "").replace('\r', '').replace(
                "\t", "") for i in sheet.row_values(rownum)]
            wr.writerow(row_values)
    return response
export_si_rna.short_description = "Export selected siRNAs"


class SiRnaPage(DjangoQLSearchMixin, SimpleHistoryWithSummaryAdmin, AdminChangeFormWithNavigation, DynamicArrayMixin):

    list_display = ('id', 'name', 'sequence', 'supplier',
                    'supplier_part_no', 'target_genes', 'get_sheet_short_name')
    list_display_links = ('id',)
    list_per_page = 25
    formfield_overrides = {CharField: {
        'widget': TextInput(attrs={'size': '93'})}, }
    djangoql_schema = SiRnaQLSchema
    djangoql_completion_enabled_by_default = False
    actions = [export_si_rna]
    search_fields = ['id', 'name']
    autocomplete_fields = ['created_by', 'orders']

    def save_model(self, request, obj, form, change):
        '''Override default save_model to limit a user's ability to save a record
        Superusers and lab managers can change all records
        Regular users can change only their own records
        Guests cannot change any record
        Also automatically renames info_sheet
        '''

        rename_doc = False
        new_obj = False

        if obj.pk == None:
            obj.id = SiRna.objects.order_by(
                '-id').first().id + 1 if SiRna.objects.exists() else 1

            try:
                obj.created_by
            except:
                obj.created_by = request.user

            if obj.info_sheet:
                rename_doc = True
                new_obj = True
            obj.save()
        else:
            saved_obj = SiRna.objects.get(pk=obj.pk)
            if obj.info_sheet and obj.info_sheet != saved_obj.info_sheet:
                rename_doc = True
                obj.save_without_historical_record()
            else:
                obj.save()

        # Rename info_sheet
        if rename_doc:
            doc_dir_path = os.path.join(MEDIA_ROOT, 'collection/sirna/')
            old_file_name_abs_path = os.path.join(
                MEDIA_ROOT, obj.info_sheet.name)
            old_file_name, ext = os.path.splitext(
                os.path.basename(old_file_name_abs_path))
            new_file_name = os.path.join(
                'collection/sirna/',
                f'sirna{LAB_ABBREVIATION_FOR_FILES}{obj.id}_'
                f'{datetime.now().strftime("%Y%m%d")}_'
                f'{datetime.now().strftime("%H%M%S")}_'
                f'{datetime.now().strftime("%H%M%S")}'
                f'{ext.lower()}')
            new_file_name_abs_path = os.path.join(MEDIA_ROOT, new_file_name)

            if not os.path.exists(doc_dir_path):
                os.makedirs(doc_dir_path)

            os.rename(
                old_file_name_abs_path,
                new_file_name_abs_path)

            obj.info_sheet.name = new_file_name
            obj.save()

            # For new records, delete first history record, which contains the unformatted info_sheet name, and change
            # the newer history record's history_type from changed (~) to created (+). This gets rid of a duplicate
            # history record created when automatically generating a info_sheet name
            if new_obj:
                obj.history.last().delete()
                history_obj = obj.history.first()
                history_obj.history_type = "+"
                history_obj.save()

    def save_related(self, request, form, formsets, change):

        super(SiRnaPage, self).save_related(request, form, formsets, change)

        # Keep a record of the IDs of linked M2M fields in the main strain record
        # Not pretty, but it works

        obj = SiRna.objects.get(pk=form.instance.id)

        obj.history_orders = list(obj.orders.order_by('id').distinct(
            'id').values_list('id', flat=True)) if obj.orders.exists() else []

        obj.save_without_historical_record()

        history_obj = obj.history.latest()
        history_obj.history_orders = obj.history_orders
        history_obj.save()

    def get_readonly_fields(self, request, obj=None):
        '''Override default get_readonly_fields to define user-specific read-only fields
        If a user is not a superuser, lab manager or the user who created a record
        return all fields as read-only 
        'created_date_time' and 'last_changed_date_time' fields must always be read-only
        because their set by Django itself'''

        if obj:
            return ['created_date_time', 'last_changed_date_time', 'created_by']
        else:
            return []

    def add_view(self, request, extra_context=None):
        '''Override default add_view to show only desired fields'''

        self.fields = ('name', 'sequence', 'supplier', 'supplier_part_no',
                       'supplier_si_rna_id', 'species', 'target_genes', 'locus_ids',
                       'description_comment', 'info_sheet', 'orders', 'created_by')
        return super(SiRnaPage, self).add_view(request, extra_context=extra_context)

    def change_view(self, request, object_id, extra_context=None):
        '''Override default change_view to show only desired fields'''

        self.fields = ('name', 'sequence', 'supplier', 'supplier_part_no',
                       'supplier_si_rna_id', 'species', 'target_genes', 'locus_ids',
                       'description_comment', 'info_sheet', 'orders', 'created_date_time',
                       'last_changed_date_time', 'created_by',)
        return super(SiRnaPage, self).change_view(request, object_id, extra_context=extra_context)

    def formfield_for_foreignkey(self, db_field, request, **kwargs):

        try:
            request.resolver_match.args[0]
        except:

            # Exclude certain users from the 'Created by' field in the order form

            if db_field.name == 'created_by':
                if request.user.is_superuser or request.user.groups.filter(name='Lab manager').exists():
                    kwargs["queryset"] = User.objects.exclude(
                        username__in=['admin', 'guest', 'AnonymousUser']).order_by('last_name')
                kwargs['initial'] = request.user.id

            if db_field.name == 'species':
                kwargs["queryset"] = Species.objects.filter(
                    show_in_cell_line_collection=True)

        return super(SiRnaPage, self).formfield_for_foreignkey(db_field, request, **kwargs)

    def get_sheet_short_name(self, instance):
        '''Create custom column for information sheet
        It formats a html element a for the information sheet
        such that the text shown for a link is always View'''

        if instance.info_sheet:
            return mark_safe(f'<a class="magnific-popup-iframe-pdflink" href="{instance.info_sheet.url}">View</a>')
        else:
            return ''
    get_sheet_short_name.short_description = 'Info Sheet'

    def get_history_array_fields(self):

        return {**super(SiRnaPage, self).get_history_array_fields(),
                'history_orders': Order,
                }
