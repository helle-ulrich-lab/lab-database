from django.http import HttpResponse
from django.utils.safestring import mark_safe
from django.forms import TextInput
from django.db.models import CharField

from djangoql.schema import DjangoQLSchema
from djangoql.admin import DjangoQLSearchMixin
from import_export import resources

import xlrd
import csv
import time
import os

from django.conf import settings
MEDIA_ROOT = settings.MEDIA_ROOT
LAB_ABBREVIATION_FOR_FILES = getattr(settings, 'LAB_ABBREVIATION_FOR_FILES', '')

from common.shared_elements import SimpleHistoryWithSummaryAdmin
from common.shared_elements import AdminChangeFormWithNavigation
from .admin import FieldLocation
from .admin import FieldApplication

from ..models.antibody import Antibody


class AntibodyQLSchema(DjangoQLSchema):
    '''Customize search functionality'''
    
    def get_fields(self, model):
        '''Define fields that can be searched'''
        
        if model == Antibody:
            return ['id', 'name', 'species_isotype', 'clone', 'received_from', 'catalogue_number', 'info_sheet',
                FieldLocation(), FieldApplication(), 'description_comment','info_sheet', 'availability', ]
        return super(AntibodyQLSchema, self).get_fields(model)

class AntibodyExportResource(resources.ModelResource):
    """Defines a custom export resource class for Antibody"""
    
    class Meta:
        model = Antibody
        fields = ('id', 'name', 'species_isotype', 'clone', 'received_from', 'catalogue_number', 'l_ocation', 'a_pplication',
                'description_comment', 'info_sheet','availability', )

def export_antibody(modeladmin, request, queryset):
    """Export Antibody"""

    export_data = AntibodyExportResource().export(queryset)

    file_format = request.POST.get('format', default='xlsx')

    if file_format == 'xlsx':
        response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        response['Content-Disposition'] = 'attachment; filename="{}_{}_{}.xlsx'.format(queryset.model.__name__, time.strftime("%Y%m%d"), time.strftime("%H%M%S"))
        response.write(export_data.xlsx)
    elif file_format == 'tsv':
        response = HttpResponse(content_type='text/tab-separated-values')
        response['Content-Disposition'] = 'attachment; filename="{}_{}_{}.tsv'.format(queryset.model.__name__, time.strftime("%Y%m%d"), time.strftime("%H%M%S"))
        xlsx_file = xlrd.open_workbook(file_contents=export_data.xlsx)
        sheet = xlsx_file.sheet_by_index(0)
        wr = csv.writer(response, delimiter="\t")
        for rownum in range(sheet.nrows):
            row_values = [str(i).replace("\n", "").replace('\r', '').replace("\t", "") for i in sheet.row_values(rownum)]
            wr.writerow(row_values)
    return response
export_antibody.short_description = "Export selected antibodies"

class AntibodyPage(DjangoQLSearchMixin, SimpleHistoryWithSummaryAdmin, AdminChangeFormWithNavigation):
    
    list_display = ('id', 'name', 'catalogue_number', 'received_from', 'species_isotype', 'clone', 'l_ocation', 'get_sheet_short_name', 'availability',)
    list_display_links = ('id',)
    list_per_page = 25
    formfield_overrides = {CharField: {'widget': TextInput(attrs={'size':'93'})},}
    djangoql_schema = AntibodyQLSchema
    djangoql_completion_enabled_by_default = False
    actions = [export_antibody]
    search_fields = ['id', 'name']
    
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
            obj.id = Antibody.objects.order_by('-id').first().id + 1 if Antibody.objects.exists() else 1
            obj.created_by = request.user
            if obj.info_sheet:
                rename_doc = True
                new_obj = True
            obj.save()
        else:
            saved_obj = Antibody.objects.get(pk=obj.pk)
            if obj.info_sheet and obj.info_sheet != saved_obj.info_sheet:
                rename_doc = True
                obj.save_without_historical_record()
            else:
                obj.save()

        # Rename info_sheet
        if rename_doc:
            doc_dir_path = os.path.join(MEDIA_ROOT, 'collection/antibody/')
            old_file_name_abs_path = os.path.join(MEDIA_ROOT, obj.info_sheet.name)
            old_file_name, ext = os.path.splitext(os.path.basename(old_file_name_abs_path)) 
            new_file_name = os.path.join(
                'collection/antibody/',
                "ab{}{}{}".format(LAB_ABBREVIATION_FOR_FILES, obj.id, ext.lower()))
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
        
    def get_readonly_fields(self, request, obj=None):
        '''Override default get_readonly_fields to define user-specific read-only fields
        If a user is not a superuser, lab manager or the user who created a record
        return all fields as read-only 
        'created_date_time' and 'last_changed_date_time' fields must always be read-only
        because their set by Django itself'''

        if obj:
            return ['created_date_time', 'last_changed_date_time',]
        else:
            return []
    
    def add_view(self,request,extra_context=None):
        '''Override default add_view to show only desired fields'''

        self.fields = ('name', 'species_isotype', 'clone', 'received_from', 'catalogue_number', 'l_ocation', 'a_pplication',
                'description_comment', 'info_sheet', 'availability',)
        return super(AntibodyPage,self).add_view(request)
    
    def change_view(self,request,object_id,extra_context=None):
        '''Override default change_view to show only desired fields'''

        self.fields = ('name', 'species_isotype', 'clone', 'received_from', 'catalogue_number', 'l_ocation', 'a_pplication',
                'description_comment', 'info_sheet', 'availability', 'created_date_time','last_changed_date_time', )
        return super(AntibodyPage,self).change_view(request,object_id)

    def get_sheet_short_name(self, instance):
        '''Create custom column for information sheet
        It formats a html element a for the information sheet
        such that the text shown for a link is always View'''

        if instance.info_sheet:
            return mark_safe('<a class="magnific-popup-iframe-pdflink" href="{}">View</a>'.format(str(instance.info_sheet.url)))
        else:
            return ''
    get_sheet_short_name.short_description = 'Info Sheet'