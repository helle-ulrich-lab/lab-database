from django.contrib import admin
from django.http import HttpResponse
from django.forms import TextInput
from django.db.models import CharField
from django.contrib.auth.models import User
from django.urls import reverse
from django.utils import timezone
from django.http import HttpResponseRedirect
from django.utils.html import format_html
from django.contrib import messages
from django.utils.translation import gettext_lazy as _
from django import forms
from django.core.exceptions import PermissionDenied

from djangoql.schema import DjangoQLSchema
from djangoql.admin import DjangoQLSearchMixin
from import_export import resources
from import_export.fields import Field

import xlrd
import csv
import time
from urllib.parse import quote as urlquote

from common.shared import SimpleHistoryWithSummaryAdmin
from common.shared import AdminChangeFormWithNavigation
from common.shared import SearchFieldOptUsername
from common.shared import SearchFieldOptLastname
from collection.admin.shared import FieldUse
from collection.admin.shared import FieldCreated
from collection.admin.shared import FieldLastChanged
from collection.admin.shared import FieldFormZProject
from collection.admin.shared import FieldParent1
from collection.admin.shared import FieldParent2
from collection.admin.shared import formz_as_html
from collection.admin.shared import CustomGuardedModelAdmin
from collection.admin.shared import Approval
from collection.admin.shared import SortAutocompleteResultsId
from common.shared import DocFileInlineMixin
from common.shared import AddDocFileInlineMixin
from common.shared import ToggleDocInlineMixin

from .oligo import Oligo
from .plasmid import Plasmid
from formz.models import FormZProject
from formz.models import FormZBaseElement
from formz.models import GenTechMethod

from collection.models.worm_strain import WormStrain
from collection.models.worm_strain import WormStrainGenotypingAssay
from collection.models.worm_strain import WormStrainDoc


class SearchFieldOptUsernameWormStrain(SearchFieldOptUsername):

    id_list = WormStrain.objects.all().values_list('created_by', flat=True).distinct()

class SearchFieldOptLastnameWormStrain(SearchFieldOptLastname):

    id_list = WormStrain.objects.all().values_list('created_by', flat=True).distinct()

class WormStrainQLSchema(DjangoQLSchema):
    '''Customize search functionality'''

    include = (WormStrain, User) # Include only the relevant models to be searched

    def get_fields(self, model):
        ''' Define fields that can be searched'''
        
        if model == WormStrain:
            return ['id', 'name', 'chromosomal_genotype', FieldParent1(), FieldParent2(),
                    'construction', 'outcrossed', 'growth_conditions', 'organism', 
                    'selection', 'phenotype',
                    'received_from', FieldUse(), 'note', 'reference', 'created_by', 
                    FieldCreated(), FieldLastChanged(), FieldFormZProject()]
        elif model == User:
            return [SearchFieldOptUsernameWormStrain(), SearchFieldOptLastnameWormStrain()]
        return super(WormStrainQLSchema, self).get_fields(model)

class WormStrainExportResource(resources.ModelResource):
    """Defines a custom export resource class for WormStrain"""

    primers_for_genotyping = Field()
    
    def dehydrate_primers_for_genotyping(self, strain):
                
        return str(strain.history_genotyping_oligos)[1:-1]

    class Meta:
        model = WormStrain
        fields = ('id', 'name', 'chromosomal_genotype', 'parent_1', 'parent_2',
        'construction', 'outcrossed', 'growth_conditions', 'organism', 'integrated_dna_plasmids', 
        'integrated_dna_oligos', 'selection', 'phenotype', 'received_from', 
        'us_e', 'note', 'reference', 'location_freezer1', 'location_freezer2', 'location_backup',
        'primers_for_genotyping', 'created_date_time', 'created_by__username',)
        export_order = fields

def export_wormstrain(modeladmin, request, queryset):
    """Export WormStrain"""

    export_data = WormStrainExportResource().export(queryset)

    file_format = request.POST.get('format', default='xlsx')

    if file_format == 'xlsx':
        response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        response['Content-Disposition'] = 'attachment; filename="{}_{}_{}.xlsx'.format('WormStrain', time.strftime("%Y%m%d"), time.strftime("%H%M%S"))
        response.write(export_data.xlsx)
    elif file_format == 'tsv':
        response = HttpResponse(content_type='text/tab-separated-values')
        response['Content-Disposition'] = 'attachment; filename="{}_{}_{}.tsv'.format('WormStrain', time.strftime("%Y%m%d"), time.strftime("%H%M%S"))
        xlsx_file = xlrd.open_workbook(file_contents=export_data.xlsx)
        sheet = xlsx_file.sheet_by_index(0)
        wr = csv.writer(response, delimiter="\t")
        for rownum in range(sheet.nrows):
            row_values = [str(i).replace("\n", "").replace('\r', '').replace("\t", "") for i in sheet.row_values(rownum)]
            wr.writerow(row_values)
    return response
export_wormstrain.short_description = "Export selected strains"

class WormStrainForm(forms.ModelForm):
    
    class Meta:
        model = WormStrain
        fields = '__all__'

    def clean_name(self):
        """Check if name is unique before saving"""
        
        if not self.instance.pk:
            qs = WormStrain.objects.filter(name=self.cleaned_data["name"])
            if qs.exists():
                raise forms.ValidationError('Strain with this name already exists.')
            else:
                return self.cleaned_data["name"]
        else:
            return self.cleaned_data["name"]

class WormStrainGenotypingAssayInline(admin.TabularInline):
    """Inline to view existing worm genotyping assay"""

    model = WormStrainGenotypingAssay
    verbose_name = "genotyping assay"
    verbose_name_plural = "existing genotyping assays"
    extra = 0
    readonly_fields = ['locus_allele', 'oligos']

    def has_add_permission(self, request, obj):
        return False

class AddWormStrainGenotypingAssayInline(admin.TabularInline):
    """Inline to add new worm genotyping assays"""
    
    model = WormStrainGenotypingAssay
    verbose_name = "genotyping assay"
    verbose_name_plural = "new genotyping assays"
    extra = 0
    autocomplete_fields = ['oligos']

    def has_change_permission(self, request, obj=None):
        return False

    def get_queryset(self, request):
        return self.model.objects.none()

class WormStrainDocInline(DocFileInlineMixin):
    """Inline to view existing worm strain documents"""

    model = WormStrainDoc

class WormStrainAddDocInline(AddDocFileInlineMixin):
    """Inline to add new worm strain documents"""
    
    model = WormStrainDoc

class WormStrainPage(ToggleDocInlineMixin, DjangoQLSearchMixin,
                     SimpleHistoryWithSummaryAdmin, CustomGuardedModelAdmin,
                     Approval, AdminChangeFormWithNavigation,
                     SortAutocompleteResultsId):
    
    list_display = ('id', 'name', 'chromosomal_genotype', 'created_by', 'approval')
    list_display_links = ('id', )
    list_per_page = 25
    djangoql_schema = WormStrainQLSchema
    djangoql_completion_enabled_by_default = False
    actions = [export_wormstrain, formz_as_html]
    form = WormStrainForm
    formfield_overrides = {CharField: {'widget': TextInput(attrs={'size':'93'})},} # Make TextInput fields wider
    search_fields = ['id', 'name']
    autocomplete_fields = ['parent_1', 'parent_2', 'formz_projects', 'formz_gentech_methods', 'formz_elements',
                           'integrated_dna_plasmids', 'integrated_dna_oligos']
    inlines = [WormStrainGenotypingAssayInline, AddWormStrainGenotypingAssayInline,
               WormStrainDocInline, WormStrainAddDocInline]
    
    def save_model(self, request, obj, form, change):
        '''Override default save_model to limit a user's ability to save a record
        Superusers and lab managers can change all records
        Regular users can change only their own records
        Guests cannot change any record'''

        if obj.pk == None:
            
            obj.id = WormStrain.objects.order_by('-id').first().id + 1 if WormStrain.objects.exists() else 1 # Don't rely on autoincrement value in DB table
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
                WormStrain.objects.filter(id=obj.pk).update(last_changed_date_time=original_last_changed_date_time)
            else:
                obj.approval.create(activity_type='created', activity_user=request.user)

        else:
            
            # Check if the disapprove button was clicked. If so, and no approval
            # record for the object exists, create one
            if "_disapprove_record" in request.POST:
                if not obj.approval.all().exists():
                    original_last_changed_date_time = obj.last_changed_date_time
                    obj.approval.create(activity_type='changed', activity_user=obj.created_by)
                    obj.last_changed_approval_by_pi = False
                    obj.save_without_historical_record()
                    WormStrain.objects.filter(id=obj.pk).update(last_changed_date_time=original_last_changed_date_time)
                return

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

    def save_related(self, request, form, formsets, change):
        
        super(WormStrainPage, self).save_related(request, form, formsets, change)

        # Keep a record of the IDs of linked M2M fields in the main strain record
        # Not pretty, but it works

        obj = WormStrain.objects.get(pk=form.instance.id)

        obj.history_integrated_plasmids = list(obj.integrated_dna_plasmids.order_by('id').distinct('id').values_list('id', flat=True)) if obj.integrated_dna_plasmids.exists() else []
        obj.history_integrated_oligos = list(obj.integrated_dna_oligos.order_by('id').distinct('id').values_list('id', flat=True)) if obj.integrated_dna_oligos.exists() else []
        obj.history_formz_projects = list(obj.formz_projects.order_by('id').distinct('id').values_list('id', flat=True)) if obj.formz_projects.exists() else []
        obj.history_formz_gentech_methods = list(obj.formz_gentech_methods.order_by('id').distinct('id').values_list('id', flat=True)) if obj.formz_gentech_methods.exists() else []
        obj.history_formz_elements = list(obj.formz_elements.order_by('id').distinct('id').values_list('id', flat=True)) if obj.formz_elements.exists() else []
        obj.history_genotyping_oligos = list(Oligo.objects.filter(wormstrain_genotypingassay_oligo=obj.id).order_by('id').distinct('id').values_list('id', flat=True)) if obj.wormstraingenotypingassay_set.exists() else []
        obj.history_documents = list(obj.wormstraindoc_set.order_by('id').distinct('id').values_list('id', flat=True)) if obj.wormstraindoc_set.exists() else []

        obj.save_without_historical_record()

        history_obj = obj.history.latest()
        history_obj.history_integrated_plasmids = obj.history_integrated_plasmids
        history_obj.history_integrated_oligos = obj.history_integrated_oligos
        history_obj.history_formz_projects = obj.history_formz_projects
        history_obj.history_formz_gentech_methods = obj.history_formz_gentech_methods
        history_obj.history_formz_elements = obj.history_formz_elements
        history_obj.history_genotyping_oligos = obj.history_genotyping_oligos
        history_obj.history_documents = obj.history_documents

        history_obj.save()

    def get_readonly_fields(self, request, obj=None):
        '''Override default get_readonly_fields to define user-specific read-only fields
        If a user is not a superuser, lab manager or the user who created a record
        return all fields as read-only
        'created_date_time' and 'last_changed_date_time' fields must always be read-only
        because their set by Django itself'''
        
        if obj:
            if (request.user.is_superuser or request.user.groups.filter(name='Lab manager').exists() or request.user == obj.created_by):
                return ['created_date_time', 'created_approval_by_pi', 'last_changed_date_time', 'last_changed_approval_by_pi', 'created_by',]
            else:
                if request.user.has_perm('collection.change_wormstrain', obj):
                    return ['created_date_time', 'created_approval_by_pi', 'last_changed_date_time', 'last_changed_approval_by_pi', 'created_by',]
                if obj.created_by.groups.filter(name='Past member') or obj.created_by.labuser.is_principal_investigator:
                    return ['name', 'chromosomal_genotype', 'parent_1', 'parent_2', 'construction',
                            'outcrossed', 'growth_conditions', 'organism', 'selection', 'phenotype', 
                            'received_from', 'us_e', 'reference', 'location_freezer1', 'location_freezer2',
                            'location_backup', 'created_date_time', 'created_approval_by_pi', 'last_changed_date_time', 
                            'last_changed_approval_by_pi', 'created_by', 'formz_projects', 'formz_risk_group',
                            'formz_gentech_methods', 'formz_elements', 'destroyed_date', 'integrated_dna_plasmids',
                            'integrated_dna_oligos']
                else:
                    return ['name', 'chromosomal_genotype', 'parent_1', 'parent_2', 'construction',
                            'outcrossed', 'growth_conditions', 'organism', 'selection', 'phenotype', 
                            'received_from', 'us_e', 'note', 'reference', 'location_freezer1', 'location_freezer2',
                            'location_backup', 'created_date_time', 'created_approval_by_pi', 'last_changed_date_time', 
                            'last_changed_approval_by_pi', 'created_by', 'formz_projects', 'formz_risk_group',
                            'formz_gentech_methods', 'formz_elements', 'destroyed_date', 'integrated_dna_plasmids',
                            'integrated_dna_oligos']
        else:
            return ['created_date_time', 'created_approval_by_pi', 'last_changed_date_time', 'last_changed_approval_by_pi',]

    def add_view(self,request,extra_context=None):
        '''Override default add_view to show desired fields'''

        self.fieldsets = (
        (None, {
            'fields': ('name', 'chromosomal_genotype', 'parent_1', 'parent_2', 
        'construction', 'outcrossed', 'growth_conditions', 
        'organism',  'selection', 'phenotype', 'received_from', 
        'us_e', 'note', 'reference',)
        }),
        ("Integrated DNA", {"fields": (tuple(['integrated_dna_plasmids','integrated_dna_oligos']),),}),
        ('Location', {
            'fields': ('location_freezer1', 'location_freezer2', 'location_backup',)
        }),
        ('FormZ', {
            'fields': ('formz_projects', 'formz_risk_group', 'formz_gentech_methods', 
                       'formz_elements', 'destroyed_date')
        }),
        )

        return super(WormStrainPage,self).add_view(request)

    def change_view(self,request,object_id,extra_context=None):
        '''Override default change_view to show desired fields'''

        self.can_change = False

        extra_context = extra_context or {}
        extra_context['show_disapprove'] = False
        extra_context['show_formz'] = False

        if object_id:

            obj = WormStrain.objects.get(pk=object_id)

            if obj.history_integrated_plasmids:
                extra_context['plasmid_id_list'] = tuple(obj.history_integrated_plasmids)

            if request.user == obj.created_by or request.user.groups.filter(name='Lab manager').exists() or \
                request.user.labuser.is_principal_investigator or obj.created_by.labuser.is_principal_investigator or \
                obj.created_by.groups.filter(name='Past member') or request.user.is_superuser or \
                request.user.has_perm('collection.change_wormstrain', obj):
                
                self.can_change = True

                    
                extra_context.update({'show_close': True,
                                'show_save_and_add_another': False,
                                'show_save_and_continue': True,
                                'show_save_as_new': False,
                                'show_save': True,
                                'show_obj_permission': False,})
            
            else:

                extra_context.update({'show_close': True,
                    'show_save_and_add_another': True,
                    'show_save_and_continue': True,
                    'show_save_as_new': False,
                    'show_save': True,
                    'show_obj_permission': False})

            extra_context['show_disapprove'] = True if request.user.groups.filter(name='Approval manager').exists() else False
            extra_context['show_formz'] = True

        if '_saveasnew' in request.POST:
            
            self.fieldsets = (
            (None, {
                'fields': ('name', 'chromosomal_genotype', 'parent_1', 'parent_2', 
                           'construction', 'outcrossed', 'growth_conditions', 'organism', 
                           'selection', 'phenotype', 'received_from', 'us_e', 'note',
                           'reference',)
            }),
            ("Integrated DNA", {"fields": (tuple(['integrated_dna_plasmids','integrated_dna_oligos']),),}),
            ('Location', {
                'fields': ('location_freezer1', 'location_freezer2', 'location_backup',)
            }),
            ('FormZ', {
                'fields': ('formz_projects', 'formz_risk_group', 'formz_gentech_methods',
                           'formz_elements', 'destroyed_date')
            }),
            )

            extra_context.update({'show_save_and_continue': False,
                                 'show_save': False,
                                 'show_save_and_add_another': False,
                                 'show_disapprove': False,
                                 'show_formz': False,
                                 'show_obj_permission': False
                                 })

        else:

            if request.user == obj.created_by or not obj.created_by.groups.filter(name='Past member').exists():
                self.fieldsets = (
                (None, {
                    'fields': ('name', 'chromosomal_genotype', 'parent_1', 'parent_2',
                               'construction', 'outcrossed', 'growth_conditions',
                               'organism', 'selection', 'phenotype', 'received_from','us_e', 'note',
                               'reference', 'created_date_time', 'created_approval_by_pi',
                               'last_changed_date_time', 'last_changed_approval_by_pi',
                               'created_by',)
                }),
                ("Integrated DNA", {"fields": (tuple(['integrated_dna_plasmids','integrated_dna_oligos']),),}),
                ('Location', {
                    'fields': ('location_freezer1', 'location_freezer2', 'location_backup',)
                }),
                ('FormZ', {
                    'classes': ('collapse',) if not request.GET.get('_approval', '') else tuple(),
                    'fields': ('formz_projects', 'formz_risk_group', 'formz_gentech_methods', 'formz_elements','destroyed_date')
                }),
                )
            else:
                self.fieldsets = (
                (None, {
                    'fields': ('name', 'chromosomal_genotype', 'parent_1', 'parent_2',
                    'parental_strain', 'construction', 'outcrossed', 'growth_conditions',
                    'organism',  'selection', 'phenotype', 'received_from','us_e', 'note',
                    'reference', 'created_date_time', 'created_approval_by_pi',
                    'last_changed_date_time', 'last_changed_approval_by_pi', 'created_by')
                }),
                ("Integrated DNA", {"fields": (tuple(['integrated_dna_plasmids','integrated_dna_oligos']),),}),
                ('Location', {
                    'fields': ('location_freezer1', 'location_freezer2', 'location_backup',)
                }),
                ('FormZ', {
                    'classes': ('collapse',) if not request.GET.get('_approval', '') else tuple(),
                    'fields': ('formz_projects', 'formz_risk_group', 'formz_gentech_methods', 'formz_elements', 'destroyed_date')
                }),
                )

        return super(WormStrainPage,self).change_view(request,object_id,extra_context=extra_context)

    def get_formsets_with_inlines(self, request, obj=None):
        """Remove AddCellLineDocInline from add/change form if user who
        created a CellLine object is not the request user a lab manager
        or a superuser"""
        
        if obj:
            for inline in self.get_inline_instances(request, obj):
                if inline.verbose_name_plural == 'existing genotyping assays':
                    yield inline.get_formset(request, obj), inline
                else:
                    if not request.user.groups.filter(name='Guest').exists():
                        yield inline.get_formset(request, obj), inline
        else:
            for inline in self.get_inline_instances(request, obj):
                if inline.verbose_name_plural == 'existing genotyping assays':
                    continue
                else:
                    yield inline.get_formset(request, obj), inline
   
    def obj_perms_manage_view(self, request, object_pk):
        """
        Main object Guardian permissions view. 

        Customized to allow only record owner to change permissions
        """
        obj = WormStrain.objects.get(pk=object_pk)
        
        if obj:
            if not (request.user.is_superuser or request.user.groups.filter(name='Lab manager').exists() or \
                request.user == obj.created_by or request.user.labuser.is_principal_investigator):
                messages.error(request, 'Nice try, you are allowed to change the permissions of your own records only.')
                return HttpResponseRedirect("..")
        return super(WormStrainPage,self).obj_perms_manage_view(request, object_pk)

    def response_change(self, request, obj):
        opts = self.model._meta
        preserved_filters = self.get_preserved_filters(request)

        msg_dict = {
            'name': opts.verbose_name,
            'obj': format_html('<a href="{}">{}</a>', urlquote(request.path), obj),
        }

        # If the disapprove button was clicked, redirect to the approval record change
        # page
        if "_disapprove_record" in request.POST:
            msg = format_html(
                _('The {name} "{obj}" was disapproved.'),
                **msg_dict)
            self.message_user(request, msg, messages.SUCCESS)
            return HttpResponseRedirect(reverse("admin:approval_recordtobeapproved_change", args=(obj.approval.latest('created_date_time').id,)))
        
        return super(WormStrainPage,self).response_change(request,obj)
    
    def get_history_array_fields(self):

        return {**super(WormStrainPage, self).get_history_array_fields(),
                'history_integrated_plasmids': Plasmid,
                'history_integrated_oligos': Oligo,
                'history_formz_projects': FormZProject,
                'history_formz_gentech_methods': GenTechMethod,
                'history_formz_elements': FormZBaseElement,
                'history_genotyping_oligos': Oligo,
                'history_documents': WormStrainDoc
                }