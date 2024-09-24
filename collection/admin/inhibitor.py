from django.contrib import admin
from django.http import HttpResponse
from django.utils.safestring import mark_safe
from django.forms import TextInput
from django.db.models import CharField

from djangoql.schema import DjangoQLSchema
from djangoql.admin import DjangoQLSearchMixin
from import_export import resources
from common.model_clone import CustomClonableModelAdmin

import xlrd
import csv
import time
import os

from django.conf import settings
MEDIA_ROOT = settings.MEDIA_ROOT
LAB_ABBREVIATION_FOR_FILES = getattr(settings, 'LAB_ABBREVIATION_FOR_FILES', '')

from common.shared import SimpleHistoryWithSummaryAdmin
from collection.admin.shared import FieldLocation
from common.shared import DocFileInlineMixin
from common.shared import AddDocFileInlineMixin
from common.shared import ToggleDocInlineMixin
from common.model_clone import CustomClonableModelAdmin

from collection.models import Inhibitor
from collection.models import InhibitorDoc


class InhibitorQLSchema(DjangoQLSchema):
    '''Customize search functionality'''
    
    def get_fields(self, model):
        '''Define fields that can be searched'''
        
        if model == Inhibitor:
            return ['id', 'name', 'other_names', 'target', 'received_from', 'catalogue_number',
                FieldLocation(), 'description_comment','info_sheet', ]
        return super(InhibitorQLSchema, self).get_fields(model)

class InhibitorExportResource(resources.ModelResource):
    """Defines a custom export resource class for Inhibitor"""
    
    class Meta:
        model = Inhibitor
        fields = ('id', 'name', 'other_names', 'target', 'received_from', 'catalogue_number', 'l_ocation', 
                  'ic50', 'amount', 'stock_solution', 'description_comment','info_sheet',)

def export_inhibitor(modeladmin, request, queryset):
    """Export Inhibitor"""

    export_data = InhibitorExportResource().export(queryset)

    file_format = request.POST.get('format', default='none')

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
export_inhibitor.short_description = "Export selected inhibitors"

class InhibitorDocInline(DocFileInlineMixin):
    """Inline to view existing Inhibitor documents"""

    model = InhibitorDoc

class InhibitorAddDocInline(AddDocFileInlineMixin):
    """Inline to add new Inhibitor documents"""
    
    model = InhibitorDoc

class InhibitorPage(ToggleDocInlineMixin, CustomClonableModelAdmin, DjangoQLSearchMixin, 
                    SimpleHistoryWithSummaryAdmin, admin.ModelAdmin):

    list_display = ('id', 'name', 'target', 'catalogue_number', 'received_from', 'l_ocation', 'get_sheet_short_name')
    list_display_links = ('id', )
    list_per_page = 25
    formfield_overrides = {CharField: {'widget': TextInput(attrs={'size':'93'})},}
    djangoql_schema = InhibitorQLSchema
    djangoql_completion_enabled_by_default = False
    actions = [export_inhibitor]
    search_fields = ['id', 'name']
    inlines = [InhibitorDocInline, InhibitorAddDocInline]
    clone_ignore_fields = ['info_sheet']
    add_view_fields = ('name', 'other_names', 'target', 'received_from', 'catalogue_number', 'l_ocation', 
                  'ic50', 'amount', 'stock_solution', 'description_comment','info_sheet', )

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
            obj.created_by = request.user
            if obj.info_sheet:
                rename_doc = True
                new_obj = True
            obj.save()
        else:
            saved_obj = Inhibitor.objects.get(pk=obj.pk)
            if obj.info_sheet and obj.info_sheet != saved_obj.info_sheet:
                rename_doc = True
                obj.save_without_historical_record()
            else:
                obj.save()

        # Rename info_sheet
        if rename_doc:
            doc_dir_path = os.path.join(MEDIA_ROOT, 'collection/inhibitor/')
            old_file_name_abs_path = os.path.join(MEDIA_ROOT, obj.info_sheet.name)
            old_file_name, ext = os.path.splitext(os.path.basename(old_file_name_abs_path)) 
            new_file_name = os.path.join(
                'collection/inhibitor/',
                "ib{}{}{}".format(LAB_ABBREVIATION_FOR_FILES, obj.id, ext.lower()))
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
        
        super().save_related(request, form, formsets, change)

        # Keep a record of the IDs of linked M2M fields in the main strain record
        # Not pretty, but it works

        obj = Inhibitor.objects.get(pk=form.instance.id)

        obj.history_documents = list(obj.inhibitordoc_set.order_by('id').\
                                     distinct('id').values_list('id', flat=True)) \
                                    if obj.inhibitordoc_set.exists() else []

        obj.save_without_historical_record()

        history_obj = obj.history.latest()
        history_obj.history_documents = obj.history_documents
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

        self.fields = self.add_view_fields

        return super(InhibitorPage,self).add_view(request)
    
    def change_view(self, request, object_id, form_url="", extra_context=None):
        '''Override default change_view to show only desired fields'''

        self.fields = ('name', 'other_names', 'target', 'received_from', 'catalogue_number', 'l_ocation', 
                  'ic50', 'amount', 'stock_solution', 'description_comment','info_sheet', 'created_date_time','last_changed_date_time', )
        return super().change_view(request, object_id, form_url, extra_context)

    def get_sheet_short_name(self, instance):
        '''Create custom column for information sheet
        It formats a html element a for the information sheet
        such that the text shown for a link is always View'''

        if instance.info_sheet:
            return mark_safe('<a class="magnific-popup-iframe-pdflink" href="{}">View</a>'.format(str(instance.info_sheet.url)))
        else:
            return ''
    get_sheet_short_name.short_description = 'Info Sheet'

    def get_history_array_fields(self):

        return {**super().get_history_array_fields(),
                'history_documents': InhibitorDoc
                }