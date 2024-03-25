from django.http import HttpResponse
from django.forms import TextInput
from django.db.models import CharField
from django.contrib.auth.models import User
from django.urls import reverse
from django.utils import timezone
from django.http import HttpResponseRedirect
from django.utils.html import format_html
from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.utils.translation import gettext_lazy as _

from djangoql.schema import DjangoQLSchema
from djangoql.admin import DjangoQLSearchMixin
from import_export import resources

import xlrd
import csv
import time
from urllib.parse import quote as urlquote

from common.shared import SimpleHistoryWithSummaryAdmin
from common.shared import AdminChangeFormWithNavigation
from common.shared import SearchFieldOptUsername
from common.shared import SearchFieldOptLastname
from common.shared import DocFileInlineMixin
from common.shared import AddDocFileInlineMixin
from collection.admin.shared import FieldCreated
from collection.admin.shared import FieldUse
from collection.admin.shared import FieldLastChanged
from collection.admin.shared import FieldFormZProject
from collection.admin.shared import formz_as_html
from collection.admin.shared import Approval

from formz.models import FormZProject
from formz.models import FormZBaseElement
from formz.models import GenTechMethod

from collection.models.e_coli_strain import EColiStrain
from collection.models.e_coli_strain import EColiStrainDoc
from common.shared import ToggleDocInlineMixin


class SearchFieldOptUsernameEColi(SearchFieldOptUsername):

    id_list = EColiStrain.objects.all().values_list('created_by', flat=True).distinct()

class SearchFieldOptLastnameEColi(SearchFieldOptLastname):

    id_list = EColiStrain.objects.all().values_list('created_by', flat=True).distinct()

class EColiStrainQLSchema(DjangoQLSchema):
    '''Customize search functionality'''
    
    include = (EColiStrain, User) # Include only the relevant models to be searched

    def get_fields(self, model):
        '''Define fields that can be searched'''
        
        if model == EColiStrain:
            return ['id', 'name', 'resistance', 'genotype', 'supplier', FieldUse(), 'purpose', 
            'note', 'created_by', FieldCreated(), FieldLastChanged(), FieldFormZProject(), ]
        elif model == User:
            return [SearchFieldOptUsernameEColi(), SearchFieldOptLastnameEColi()]
        return super(EColiStrainQLSchema, self).get_fields(model)

class EColiStrainExportResource(resources.ModelResource):
    """Defines a custom export resource class for EColiStrain"""
    
    class Meta:
        model = EColiStrain
        fields = ('id' ,'name', 'resistance', 'genotype', 'supplier', 'us_e', 'purpose', 'note',
                'created_date_time', 'created_by__username',)

def export_ecolistrain(modeladmin, request, queryset):
    """Export EColiStrain"""

    export_data = EColiStrainExportResource().export(queryset)

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
export_ecolistrain.short_description = "Export selected strains"

class EcoliStrainDocInline(DocFileInlineMixin):
    """Inline to view existing E. coli strain documents"""

    model = EColiStrainDoc

class EColiStrainAddDocInline(AddDocFileInlineMixin):
    """Inline to add new E. coli strain documents"""

    model = EColiStrainDoc

class EColiStrainPage(ToggleDocInlineMixin, DjangoQLSearchMixin,
                      SimpleHistoryWithSummaryAdmin, Approval,
                      AdminChangeFormWithNavigation):
    list_display = ('id', 'name', 'resistance', 'us_e','purpose', 'approval')
    list_display_links = ('id',)
    list_per_page = 25
    formfield_overrides = {CharField: {'widget': TextInput(attrs={'size':'93'})},}
    djangoql_schema = EColiStrainQLSchema
    djangoql_completion_enabled_by_default = False
    actions = [export_ecolistrain, formz_as_html]
    search_fields = ['id', 'name']
    autocomplete_fields = ['formz_projects', 'formz_elements']
    inlines = [EcoliStrainDocInline, EColiStrainAddDocInline]
    
    def save_model(self, request, obj, form, change):
        '''Override default save_model to limit a user's ability to save a record
        Superusers and lab managers can change all records
        Regular users can change only their own records
        Guests cannot change any record'''

        if obj.pk == None:
            
            obj.id = EColiStrain.objects.order_by('-id').first().id + 1 if EColiStrain.objects.exists() else 1
            obj.created_by = request.user
            obj.save()

            # If the request's user is the principal investigator, approve the record
            # right away. If not, create an approval record
            if request.user.labuser.is_principal_investigator and request.user.id in obj.formz_projects.all().values_list('project_leader__id', flat=True):
                original_last_changed_date_time = obj.last_changed_date_time
                obj.created_approval_by_pi = True
                obj.approval_user = request.user
                obj.approval_by_pi_date_time = timezone.now()
                obj.save_without_historical_record()
                EColiStrain.objects.filter(id=obj.pk).update(last_changed_date_time=original_last_changed_date_time)
            else:
                obj.approval.create(activity_type='created', activity_user=request.user)

        else:
            
            # Check if the disapprove button was clicked. If so, and no approval
            # record for the object exists, create one
            if "_disapprove_record" in request.POST:
                if not obj.approval.all():
                    original_last_changed_date_time = obj.last_changed_date_time
                    obj.approval.create(activity_type='changed', activity_user=obj.created_by)
                    obj.last_changed_approval_by_pi = False
                    obj.approval_user = None
                    obj.save_without_historical_record()
                    EColiStrain.objects.filter(id=obj.pk).update(last_changed_date_time=original_last_changed_date_time)
                return

            # if self.can_change:

            # Approve right away if the request's user is the principal investigator. If not,
            # create an approval record
            if request.user.labuser.is_principal_investigator and request.user.id in obj.formz_projects.all().values_list('project_leader__id', flat=True):
                obj.last_changed_approval_by_pi = True
                if not obj.created_approval_by_pi: obj.created_approval_by_pi = True # Set created_approval_by_pi to True, should it still be None or False
                obj.approval_user = request.user
                obj.approval_by_pi_date_time = timezone.now()
                obj.save()

                if obj.approval.all().exists():
                    approval_records = obj.approval.all()
                    approval_records.delete()
            else:
                obj.last_changed_approval_by_pi = False
                obj.approval_user = None
                obj.save()

                # If an approval record for this object does not exist, create one
                if not obj.approval.all().exists():
                    obj.approval.create(activity_type='changed', activity_user=request.user)
                else:
                    # If an approval record for this object exists, check if a message was 
                    # sent. If so, update the approval record's edited field
                    approval_obj = obj.approval.all().latest('message_date_time')
                    if approval_obj.message_date_time:
                        if obj.last_changed_date_time > approval_obj.message_date_time:
                            approval_obj.edited = True
                            approval_obj.save()
                
            # else:
            #     raise PermissionDenied

    def save_related(self, request, form, formsets, change):
        
        super(EColiStrainPage, self).save_related(request, form, formsets, change)

        # Keep a record of the IDs of linked M2M fields in the main strain record
        # Not pretty, but it works

        obj = EColiStrain.objects.get(pk=form.instance.id)

        obj.history_formz_projects = list(obj.formz_projects.order_by('id').distinct('id').values_list('id', flat=True)) if obj.formz_projects.exists() else []
        obj.history_formz_elements = list(obj.formz_elements.order_by('id').distinct('id').values_list('id', flat=True)) if obj.formz_elements.exists() else []
        obj.history_documents = list(obj.ecolistraindoc_set.order_by('id').distinct('id').values_list('id', flat=True)) if obj.ecolistraindoc_set.exists() else []

        obj.save_without_historical_record()

        history_obj = obj.history.latest()
        history_obj.history_formz_projects = obj.history_formz_projects
        history_obj.history_formz_elements = obj.history_formz_elements
        history_obj.history_documents = obj.history_documents
        history_obj.save()

    def get_readonly_fields(self, request, obj=None):
        '''Override default get_readonly_fields to define user-specific read-only fields
        If a user is not a superuser, lab manager or the user who created a record
        return all fields as read-only 
        'created_date_time' and 'last_changed_date_time' fields must always be read-only
        because their set by Django itself'''

        if obj:
            if self.can_change:
                return ['created_date_time', 'created_approval_by_pi', 'last_changed_date_time', 'last_changed_approval_by_pi',]
            else:
                
                return ['name', 'resistance', 'genotype', 'background', 'supplier', 'us_e', 'purpose', 'note',
                'created_date_time', 'created_approval_by_pi', 'last_changed_date_time', 'last_changed_approval_by_pi', 'created_by', 'formz_risk_group',
                'formz_projects', 'formz_elements', 'destroyed_date']
        else:
            return ['created_date_time', 'created_approval_by_pi', 'last_changed_date_time', 'last_changed_approval_by_pi',]
    
    def add_view(self,request,extra_context=None):
        '''Override default add_view to show only desired fields'''

        self.fieldsets = (
        (None, {
            'fields': ('name', 'resistance', 'genotype', 'background', 'supplier', 'us_e', 'purpose', 'note',)
        }),
        ('FormZ', {
            'fields': ('formz_projects', 'formz_risk_group', 'formz_elements', 'destroyed_date')
        }),
        )

        return super(EColiStrainPage,self).add_view(request)

    def change_view(self,request,object_id,extra_context=None):
        '''Override default change_view to show only desired fields'''

        extra_context = extra_context or {}
        extra_context['show_disapprove'] = False
        extra_context['show_formz'] = False
        
        self.can_change = False

        if object_id:
            
            obj = EColiStrain.objects.get(pk=object_id)

            if request.user == obj.created_by or request.user.groups.filter(name='Lab manager').exists() or \
                request.user.labuser.is_principal_investigator or request.user.is_superuser:
                
                self.can_change = True
                
                extra_context.update({'show_close': True,
                                'show_save_and_add_another': True,
                                'show_save_and_continue': True,
                                'show_save_as_new': True,
                                'show_save': True,
                                'show_obj_permission': True})

            else:

                extra_context.update({'show_close': True,
                                'show_save_and_add_another': True,
                                'show_save_and_continue': True,
                                'show_save_as_new': True,
                                'show_save': True,
                                 'show_obj_permission': False})
            
            extra_context['show_disapprove'] = True if request.user.groups.filter(name='Approval manager').exists() else False
            extra_context['show_formz'] = True

        self.fieldsets = (
            (None, {
                'fields': ('name', 'resistance', 'genotype', 'background', 'supplier', 'us_e', 'purpose', 'note', 'created_date_time', 
                'created_approval_by_pi', 'last_changed_date_time', 'last_changed_approval_by_pi', 'created_by',)
            }),
            ('FormZ', {
                'classes': ('collapse',) if not request.GET.get('_approval', '') else tuple(),
                'fields': ('formz_projects', 'formz_risk_group', 'formz_elements', 'destroyed_date')
            }),
            )

        if '_saveasnew' in request.POST:
            extra_context.update({'show_save_and_continue': False,
                                 'show_save': False,
                                 'show_save_and_add_another': False,
                                 'show_disapprove': False,
                                 'show_formz': False,
                                 'show_obj_permission': False
                                 })

        return super(EColiStrainPage,self).change_view(request,object_id, extra_context=extra_context)
    
    def response_change(self, request, obj):
        opts = self.model._meta
        preserved_filters = self.get_preserved_filters(request)

        msg_dict = {
            'name': opts.verbose_name,
            'obj': format_html('<a href="{}">{}</a>', urlquote(request.path), obj),
        }

        if "_disapprove_record" in request.POST:
            msg = format_html(
                _('The {name} "{obj}" was disapproved.'),
                **msg_dict)
            self.message_user(request, msg, messages.SUCCESS)
            return HttpResponseRedirect(reverse("admin:approval_recordtobeapproved_change", args=(obj.approval.latest('created_date_time').id,)))
        
        return super(EColiStrainPage,self).response_change(request,obj)

    def get_history_array_fields(self):

        return {**super(EColiStrainPage, self).get_history_array_fields(),
                'history_formz_projects': FormZProject,
                'history_formz_gentech_methods': GenTechMethod,
                'history_formz_elements': FormZBaseElement,
                'history_documents': EColiStrainDoc
                }