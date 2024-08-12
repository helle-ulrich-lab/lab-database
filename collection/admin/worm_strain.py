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
from django.utils.safestring import mark_safe
from django.contrib.admin.utils import quote
from django.db.models import Q

from djangoql.schema import DjangoQLSchema
from djangoql.admin import DjangoQLSearchMixin
from import_export import resources
from import_export.fields import Field

from djangoql.schema import StrField, IntField

import xlrd
import csv
import time
from urllib.parse import quote as urlquote
import os

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
from collection.admin.shared import FieldFormZBaseElement
from collection.admin.shared import FormUniqueNameCheck
from collection.admin.shared import FormTwoMapChangeCheck
from collection.admin.shared import AdminOligosInMap
from collection.admin.shared import create_map_preview, get_map_features, convert_map_gbk_to_dna
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
from collection.models import WormStrainAllele
from common.model_clone import CustomClonableModelAdmin

from django.conf import settings
BASE_DIR = settings.BASE_DIR
MEDIA_ROOT = settings.MEDIA_ROOT
LAB_ABBREVIATION_FOR_FILES = getattr(settings, 'LAB_ABBREVIATION_FOR_FILES', '')

from django.contrib.admin.options import IS_POPUP_VAR
from django.contrib.admin.options import TO_FIELD_VAR
from django.template.response import TemplateResponse
from django.contrib.admin.templatetags.admin_urls import add_preserved_filters
import json


class SearchFieldOptUsernameWormStrain(SearchFieldOptUsername):

    id_list = WormStrain.objects.all().values_list('created_by', flat=True).distinct()

class SearchFieldOptLastnameWormStrain(SearchFieldOptLastname):

    id_list = WormStrain.objects.all().values_list('created_by', flat=True).distinct()

class FieldAlleleName(StrField):
    
    model = WormStrainAllele
    name = 'allele_name'
    suggest_options = True

    def get_options(self, search):
        
        if len(search) < 3:
            return ["Type 3 or more characters to see suggestions"]

        qs = self.model.objects.filter(Q(transgene__icontains=search) |
                                       Q(mutation__icontains=search))
        return [a.name for a in qs]

    def get_lookup(self, path, operator, value):

        op, invert = self.get_operator(operator)
        value = self.get_lookup_value(value)

        q = Q(**{f'alleles__transgene{op}': value}) | \
            Q(**{f'alleles__mutation{op}': value})

        return ~q if invert else q

class FieldAlleleId(IntField):
    
    model = WormStrainAllele
    name = 'allele_id'
    suggest_options = False

    def get_lookup_name(self):
        return 'alleles__id'

class WormStrainQLSchema(DjangoQLSchema):
    '''Customize search functionality'''

    include = (WormStrain, User) # Include only the relevant models to be searched

    def get_fields(self, model):
        ''' Define fields that can be searched'''
        
        if model == WormStrain:
            return ['id', 'name', 'chromosomal_genotype', FieldParent1(), FieldParent2(),
                    'construction', 'outcrossed', 'growth_conditions', 'organism', 
                    'selection', 'phenotype',
                    'received_from', FieldUse(), 'note', 'reference', FieldAlleleId(), 
                    FieldAlleleName(), 'created_by', 
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
                           'alleles', 'integrated_dna_plasmids', 'integrated_dna_oligos']
    inlines = [WormStrainGenotypingAssayInline, AddWormStrainGenotypingAssayInline,
               WormStrainDocInline, WormStrainAddDocInline]
    change_form_template = 'admin/collection/change_form.html'
    add_view_fieldsets = (
        (None, {
            'fields': ('name', 'chromosomal_genotype', 'parent_1', 'parent_2', 
        'construction', 'outcrossed', 'growth_conditions', 
        'organism',  'selection', 'phenotype', 'received_from', 
        'us_e', 'note', 'reference', 'alleles')
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

        obj.history_integrated_dna_plasmids = list(obj.integrated_dna_plasmids.order_by('id').distinct('id').values_list('id', flat=True)) if obj.integrated_dna_plasmids.exists() else []
        obj.history_integrated_dna_oligos = list(obj.integrated_dna_oligos.order_by('id').distinct('id').values_list('id', flat=True)) if obj.integrated_dna_oligos.exists() else []
        obj.history_formz_projects = list(obj.formz_projects.order_by('id').distinct('id').values_list('id', flat=True)) if obj.formz_projects.exists() else []
        obj.history_formz_gentech_methods = list(obj.formz_gentech_methods.order_by('id').distinct('id').values_list('id', flat=True)) if obj.formz_gentech_methods.exists() else []
        obj.history_formz_elements = list(obj.formz_elements.order_by('id').distinct('id').values_list('id', flat=True)) if obj.formz_elements.exists() else []
        obj.history_genotyping_oligos = list(Oligo.objects.filter(wormstrain_genotypingassay_oligo=obj.id).order_by('id').distinct('id').values_list('id', flat=True)) if obj.wormstraingenotypingassay_set.exists() else []
        obj.history_documents = list(obj.wormstraindoc_set.order_by('id').distinct('id').values_list('id', flat=True)) if obj.wormstraindoc_set.exists() else []
        obj.history_alleles = list(obj.alleles.order_by('id').distinct('id').values_list('id', flat=True)) if obj.wormstraindoc_set.exists() else []

        obj.save_without_historical_record()

        history_obj = obj.history.latest()
        history_obj.history_integrated_dna_plasmids = obj.history_integrated_dna_plasmids
        history_obj.history_integrated_dna_oligos = obj.history_integrated_dna_oligos
        history_obj.history_formz_projects = obj.history_formz_projects
        history_obj.history_formz_gentech_methods = obj.history_formz_gentech_methods
        history_obj.history_formz_elements = obj.history_formz_elements
        history_obj.history_genotyping_oligos = obj.history_genotyping_oligos
        history_obj.history_documents = obj.history_documents
        history_obj.history_alleles = obj.history_alleles

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
                            'integrated_dna_oligos', 'alleles']
                else:
                    return ['name', 'chromosomal_genotype', 'parent_1', 'parent_2', 'construction',
                            'outcrossed', 'growth_conditions', 'organism', 'selection', 'phenotype', 
                            'received_from', 'us_e', 'note', 'reference', 'location_freezer1', 'location_freezer2',
                            'location_backup', 'created_date_time', 'created_approval_by_pi', 'last_changed_date_time', 
                            'last_changed_approval_by_pi', 'created_by', 'formz_projects', 'formz_risk_group',
                            'formz_gentech_methods', 'formz_elements', 'destroyed_date', 'integrated_dna_plasmids',
                            'integrated_dna_oligos', 'alleles']
        else:
            return ['created_date_time', 'created_approval_by_pi', 'last_changed_date_time', 'last_changed_approval_by_pi',]

    def add_view(self,request,extra_context=None):
        '''Override default add_view to show desired fields'''

        self.fieldsets = self.add_view_fieldsets

        return super(WormStrainPage,self).add_view(request)

    def change_view(self,request,object_id,extra_context=None):
        '''Override default change_view to show desired fields'''

        self.can_change = False

        extra_context = extra_context or {}
        extra_context['show_disapprove'] = False
        extra_context['show_formz'] = False

        if object_id:

            obj = WormStrain.objects.get(pk=object_id)

            if obj.history_integrated_dna_plasmids:
                extra_context['plasmid_id_list'] = tuple(obj.history_integrated_dna_plasmids)

            if request.user == obj.created_by or request.user.groups.filter(name='Lab manager').exists() or \
                request.user.labuser.is_principal_investigator or obj.created_by.labuser.is_principal_investigator or \
                obj.created_by.groups.filter(name='Past member') or request.user.is_superuser or \
                request.user.has_perm('collection.change_wormstrain', obj):
                
                self.can_change = True

                extra_context.update({'show_close': True,
                                'show_save_and_add_another': False,
                                'show_save_and_continue': True,
                                'show_save': True,
                                'show_obj_permission': False,})
            
            else:

                extra_context.update({'show_close': True,
                    'show_save_and_add_another': True,
                    'show_save_and_continue': True,
                    'show_duplicate': False,
                    'show_save': True,
                    'show_obj_permission': False})

            extra_context['show_disapprove'] = True if request.user.groups.filter(name='Approval manager').exists() else False
            extra_context['show_formz'] = True

        if request.user == obj.created_by or not obj.created_by.groups.filter(name='Past member').exists():
            self.fieldsets = (
            (None, {
                'fields': ('name', 'chromosomal_genotype', 'parent_1', 'parent_2',
                            'construction', 'outcrossed', 'growth_conditions',
                            'organism', 'selection', 'phenotype', 'received_from','us_e', 'note',
                            'reference', 'alleles', 'created_date_time', 'created_approval_by_pi',
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
                'reference', 'alleles', 'created_date_time', 'created_approval_by_pi',
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

    def get_inline_instances(self, request, obj=None):
        inline_instances = super().get_inline_instances(request, obj)
        filtered_inline_instances = []

        # New objects
        if not obj:
            for inline in inline_instances:
                if inline.verbose_name_plural == 'existing genotyping assays':
                    filtered_inline_instances.append(inline)
                else:
                    if not request.user.groups.filter(name='Guest').exists():
                        filtered_inline_instances.append(inline)

        # Existing objects
        else:
            for inline in inline_instances:
                # Always show existing docs
                if inline.verbose_name_plural == 'Existing docs':
                    filtered_inline_instances.append(inline)
                else:
                    # Do not allow guests to add docs, ever
                    if not request.user.groups.filter(name='Guest').exists():
                        filtered_inline_instances.append(inline)

        return filtered_inline_instances
   
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
                'history_integrated_dna_plasmids': Plasmid,
                'history_integrated_dna_oligos': Oligo,
                'history_formz_projects': FormZProject,
                'history_formz_gentech_methods': GenTechMethod,
                'history_formz_elements': FormZBaseElement,
                'history_genotyping_oligos': Oligo,
                'history_documents': WormStrainDoc,
                'history_alleles': WormStrainAllele
                }

class SearchFieldOptUsernameWormStrainAllele(SearchFieldOptUsername):

    id_list = WormStrainAllele.objects.all(). \
                               values_list('created_by', flat=True). \
                               distinct()

class SearchFieldOptLastnameWormStrainAllele(SearchFieldOptLastname):

    id_list = WormStrainAllele.objects.all(). \
                               values_list('created_by', flat=True). \
                               distinct()

class FieldFormZBaseElementWormStrainAllele(FieldFormZBaseElement):
    
    model = WormStrainAllele

class WormStrainAlleleQLSchema(DjangoQLSchema):
    '''Customize search functionality'''
    
    include = (WormStrainAllele, User) # Include only the relevant models to be searched

    def get_fields(self, model):
        '''Define fields that can be searched'''
        
        if model == self.include[0]:
            return ['id', 'lab_identifier', 'typ_e', 'transgene', 'transgene_position',
                    'transgene_plasmids', 'mutation', 'mutation_type', 'mutation_position',
                    'reference_strain', 'made_by_method', 'note', 'created_by', FieldCreated(),
                    FieldLastChanged(), FieldFormZBaseElement(), ]
        elif model == self.include[1]:
            return [SearchFieldOptUsernameWormStrainAllele(), SearchFieldOptLastnameWormStrainAllele()]
        return super().get_fields(model)

class WormStrainAlleleExportResource(resources.ModelResource):
    """Defines a custom export resource class for WormStrainAllele"""
    made_by_method = Field()
    type = Field()

    def dehydrate_made_by_method(self, strain):

        return strain.made_by_method.english_name

    def dehydrate_type(self, strain):
                
        return strain.get_typ_e_display()
    
    class Meta:
        model = WormStrainAllele
        fields = ('id', 'lab_identifier','type', 'transgene', 'transgene_position',
                  'transgene_plasmids', 'mutation', 'mutation_type', 'mutation_position',
                  'reference_strain', 'made_by_method', 'made_by_person', 
                  'note', 'created_date_time', 'created_by__username',)
        export_order = fields

def export_wormstrainallele(modeladmin, request, queryset):
    """Export WormStrainAllele"""

    export_data = WormStrainAlleleExportResource().export(queryset)

    file_format = request.POST.get('format', default='xlsx')
    model_name = queryset.model.__name__
    timestamp = timezone.now().strftime('%Y%m%d_%H%M%S_%f')

    if file_format == 'xlsx':
        response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        response['Content-Disposition'] = f'attachment; filename="{model_name}_{timestamp}.xlsx'
        response.write(export_data.xlsx)
    elif file_format == 'tsv':
        response = HttpResponse(content_type='text/tab-separated-values')
        response['Content-Disposition'] = f'attachment; filename="{model_name}_{timestamp}.tsv'
        xlsx_file = xlrd.open_workbook(file_contents=export_data.xlsx)
        sheet = xlsx_file.sheet_by_index(0)
        wr = csv.writer(response, delimiter="\t")
        for rownum in range(sheet.nrows):
            row_values = [str(i).replace("\n", "").replace('\r', '').replace("\t", "") for i in sheet.row_values(rownum)]
            wr.writerow(row_values)
    return response
export_wormstrainallele.short_description = "Export selected worm strain alleles"

class WormStrainAlleleForm(FormTwoMapChangeCheck,
                           forms.ModelForm):
    
    class Meta:
        model = WormStrainAllele
        fields = '__all__'

class WormStrainAllelePage(DjangoQLSearchMixin,
                  SimpleHistoryWithSummaryAdmin, CustomGuardedModelAdmin,
                  AdminChangeFormWithNavigation,
                  AdminOligosInMap, SortAutocompleteResultsId):
    
    list_display = ('id', 'lab_identifier', 'typ_e', 'name', 'get_map_short_name', 'created_by',)
    list_display_links = ('id',)
    list_per_page = 25
    formfield_overrides = {CharField: {'widget': TextInput(attrs={'size':'93'})},} # Make TextInput fields wider
    djangoql_schema = WormStrainAlleleQLSchema
    djangoql_completion_enabled_by_default = False
    actions = [export_wormstrainallele]
    search_fields = ['id', 'mutation', 'transgene']
    autocomplete_fields = ['formz_elements', 'made_by_method', 'reference_strain']
    redirect_to_obj_page = False
    form = WormStrainAlleleForm
    allele_type = ''

    add_form_template = "admin/collection/wormstrainallele/add_form.html"
    change_form_template = "admin/collection/wormstrainallele/change_form.html"

    def has_module_permission(self, request):
        return False

    def save_model(self, request, obj, form, change):
        '''Override default save_model to limit a user's ability to save a record
        Superusers and lab managers can change all records
        Regular users can change only their own records
        Guests cannot change any record.
        It also renames a plasmid map to pNZ{obj.id}_{date_created}_{time_created}.ext
        and whenever possible creates a plasmid map preview with snapegene server'''
        
        rename_and_preview = False
        self.rename_and_preview = False
        new_obj = False
        self.new_obj = False
        self.clear_formz_elements = False
        convert_map_to_dna = False

        if obj.pk == None:

            obj.id = self.model.objects.order_by('-id').first().id + 1 if self.model.objects.exists() else 1
            obj.created_by = request.user
            obj.save()
            new_obj = True
            self.new_obj = True

            # If an object is 'Saved as new', clear all form Z elements
            if "_saveasnew" in request.POST and (obj.map or obj.map_gbk):
                self.clear_formz_elements = True
            
            # Check if a map is present and if so trigger functions to create a
            # map preview and delete the resulting duplicate history record
            if obj.map:
                rename_and_preview = True
                self.rename_and_preview = True
            elif obj.map_gbk:
                rename_and_preview = True
                self.rename_and_preview = True
                convert_map_to_dna = True

        else:

            # Check if the request's user can change the object, if not raise PermissionDenied

            saved_obj = self.model.objects.get(pk=obj.pk)

            if obj.map != saved_obj.map or obj.map_gbk != saved_obj.map_gbk:

                if (obj.map and obj.map_gbk) or (not saved_obj.map and not saved_obj.map_gbk): 
                    rename_and_preview = True
                    self.rename_and_preview = True
                    obj.save_without_historical_record()
                    
                    if obj.map_gbk != saved_obj.map_gbk:
                        convert_map_to_dna = True

                else:
                    obj.map.name = ''
                    obj.map_png.name = ''
                    obj.map_gbk.name = ''
                    self.clear_formz_elements = True
                    obj.save()
            
            else:
                obj.save()

        # Rename map
        if rename_and_preview:

            timestamp = timezone.now().strftime('%Y%m%d_%H%M%S_%f')
            new_file_name = f"{self.model._model_abbreviation}{LAB_ABBREVIATION_FOR_FILES}{obj.id}_{timestamp}"
            
            new_dna_file_name = os.path.join(self.model._model_upload_to, 'dna/', new_file_name + '.dna')
            new_gbk_file_name = os.path.join(self.model._model_upload_to, 'gbk/', new_file_name + '.gbk')
            new_png_file_name = os.path.join(self.model._model_upload_to, 'png/', new_file_name + '.png')
            
            new_dna_file_path = os.path.join(MEDIA_ROOT, new_dna_file_name)
            new_gbk_file_path = os.path.join(MEDIA_ROOT, new_gbk_file_name)

            if convert_map_to_dna:
                old_gbk_file_path = obj.map_gbk.path
                os.rename(
                    old_gbk_file_path, 
                    new_gbk_file_path)
                try:
                    convert_map_gbk_to_dna(new_gbk_file_path, new_dna_file_path)
                except:
                    messages.error(request, 'There was an error with converting your plasmid map to .gbk.')
            else:
                old_dna_file_path = obj.map.path
                os.rename(
                    old_dna_file_path,
                    new_dna_file_path)
            
            obj.map.name = new_dna_file_name
            obj.map_png.name = new_png_file_name 
            obj.map_gbk.name = new_gbk_file_name
            obj.save()

            # For new records, delete first history record, which contains the unformatted map name, and change 
            # the newer history record's history_type from changed (~) to created (+). This gets rid of a duplicate
            # history record created when automatically generating a map name
            if new_obj:
                obj.history.last().delete()
                history_obj = obj.history.first()
                history_obj.history_type = "+"
                history_obj.save()
            
            # For plasmid map, detect common features and save as png using snapgene server
            try:
                detect_common_features_map_dna = request.POST.get("detect_common_features_map", False)
                detect_common_features_map_gbk = request.POST.get("detect_common_features_map_gbk", False)
                detect_common_features = True if (detect_common_features_map_dna or detect_common_features_map_gbk) else False
                create_map_preview(obj, detect_common_features, prefix=obj.lab_identifier)
            except:
                messages.error(request, 'There was an error detecting common features and/or saving the map preview')


    def save_related(self, request, form, formsets, change):
        
        super().save_related(request, form, formsets, change)

        obj = self.model.objects.get(pk=form.instance.id)

        # If a plasmid map is provided, automatically add those
        # for which a corresponding FormZ base element is present
        # in the database

        if self.clear_formz_elements:
            obj.formz_elements.clear()

        if self.rename_and_preview or "_redetect_formz_elements" in request.POST:
            
            unknown_feat_name_list = []
            
            try:
                feature_names = get_map_features(obj)
            except:
                messages.error(request, 'There was an error getting features from the map.')
                feature_names = []
            
            if not self.new_obj:
                obj.formz_elements.clear()
            
            if feature_names:
            
                formz_base_elems = FormZBaseElement.objects.filter(extra_label__label__in = feature_names).distinct()
                aliases = list(formz_base_elems.values_list('extra_label__label', flat=True))
                obj.formz_elements.add(*list(formz_base_elems))

                unknown_feat_name_list = [feat for feat in feature_names if feat not in aliases]

                if unknown_feat_name_list:
                    self.redirect_to_obj_page = True
                    unknown_feat_name_list = str(unknown_feat_name_list)[1:-1].replace("'", "")
                    messages.warning(request, mark_safe("The features were not added to <span style='background-color:rgba(0,0,0,0.1);'>FormZ Elements</span>,"
                                        " because they cannot be found in the database: <span class='missing-formz-features' style='background-color:rgba(255,0,0,0.2)'>{}</span>. You may want to add them manually "
                                        "yourself below.".format(unknown_feat_name_list)))
            else:
                self.redirect_to_obj_page = False

        # Keep a record of the IDs of linked M2M fields in the main strain record
        # Not pretty, but it works

        obj.history_formz_elements = list(obj.formz_elements.order_by('id').distinct('id').values_list('id', flat=True)) if obj.formz_elements.exists() else []

        # For new records without map preview, delete first history record, which contains the unformatted map name, and change 
        # the newer history record's history_type from changed (~) to created (+). This gets rid of a duplicate
        # history record created when automatically generating a map name
        if self.new_obj and not self.rename_and_preview:
            obj.save()
            obj.history.last().delete()
            history_obj = obj.history.first()
            history_obj.history_type = "+"
            history_obj.save()
        else:
            obj.save_without_historical_record()

        history_obj = obj.history.latest()
        history_obj.history_formz_elements = obj.history_formz_elements
        history_obj.save()

    def response_add(self, request, obj, post_url_continue=None):
        """
        Determine the HttpResponse for the add_view stage.
        """

        opts = obj._meta
        preserved_filters = self.get_preserved_filters(request)
        obj_url = reverse(
            'admin:%s_%s_change' % (opts.app_label, opts.model_name),
            args=(quote(obj.pk),),
            current_app=self.admin_site.name,
        )
        # Add a link to the object's change form if the user can edit the obj.
        if self.has_change_permission(request, obj):
            obj_repr = format_html('<a href="{}">{}</a>', urlquote(obj_url), obj)
        else:
            obj_repr = str(obj)
        msg_dict = {
            'name': opts.verbose_name,
            'obj': obj_repr,
        }
        # Here, we distinguish between different save types by checking for
        # the presence of keys in request.POST.

        if IS_POPUP_VAR in request.POST:
            to_field = request.POST.get(TO_FIELD_VAR)
            if to_field:
                attr = str(to_field)
            else:
                attr = obj._meta.pk.attname
            value = obj.serializable_value(attr)
            popup_response_data = json.dumps({
                'value': str(value),
                'obj': str(obj),
            })
            return TemplateResponse(request, self.popup_response_template or [
                'admin/%s/%s/popup_response.html' % (opts.app_label, opts.model_name),
                'admin/%s/popup_response.html' % opts.app_label,
                'admin/popup_response.html',
            ], {
                'popup_response_data': popup_response_data,
            })

        elif "_continue" in request.POST or (
                # Redirecting after "Save as new".
                "_saveasnew" in request.POST and self.save_as_continue and
                self.has_change_permission(request, obj)
        ) or self.redirect_to_obj_page: # Check if obj has unidentified FormZ Elements
            msg = _('The {name} "{obj}" was added successfully.')
            if self.has_change_permission(request, obj):
                msg += ' ' + _('You may edit it again below.')
            self.message_user(request, format_html(msg, **msg_dict), messages.SUCCESS)
            if post_url_continue is None:
                post_url_continue = obj_url
            post_url_continue = add_preserved_filters(
                {'preserved_filters': preserved_filters, 'opts': opts},
                post_url_continue
            )
            return HttpResponseRedirect(post_url_continue)

        elif "_addanother" in request.POST:
            msg = format_html(
                _('The {name} "{obj}" was added successfully. You may add another {name} below.'),
                **msg_dict
            )
            self.message_user(request, msg, messages.SUCCESS)
            redirect_url = request.path
            redirect_url = add_preserved_filters({'preserved_filters': preserved_filters, 'opts': opts}, redirect_url)
            return HttpResponseRedirect(redirect_url)

        else:
            msg = format_html(
                _('The {name} "{obj}" was added successfully.'),
                **msg_dict
            )
            self.message_user(request, msg, messages.SUCCESS)
            return self.response_post_save_add(request, obj)

    def response_change(self, request, obj):
        """
        Determine the HttpResponse for the change_view stage.
        """

        if IS_POPUP_VAR in request.POST:
            opts = obj._meta
            to_field = request.POST.get(TO_FIELD_VAR)
            attr = str(to_field) if to_field else opts.pk.attname
            value = request.resolver_match.kwargs['object_id']
            new_value = obj.serializable_value(attr)
            popup_response_data = json.dumps({
                'action': 'change',
                'value': str(value),
                'obj': str(obj),
                'new_value': str(new_value),
            })
            return TemplateResponse(request, self.popup_response_template or [
                'admin/%s/%s/popup_response.html' % (opts.app_label, opts.model_name),
                'admin/%s/popup_response.html' % opts.app_label,
                'admin/popup_response.html',
            ], {
                'popup_response_data': popup_response_data,
            })

        opts = self.model._meta
        preserved_filters = self.get_preserved_filters(request)

        msg_dict = {
            'name': opts.verbose_name,
            'obj': format_html('<a href="{}">{}</a>', urlquote(request.path), obj),
        }

        if "_disapprove_record" in request.POST:
            msg = format_html(
                _('The {name} "{obj}" was disapproved.'),
                **msg_dict
            )
            self.message_user(request, msg, messages.SUCCESS)
            return HttpResponseRedirect(reverse("admin:approval_recordtobeapproved_change", args=(obj.approval.latest('created_date_time').id,)))

        if "_continue" in request.POST or self.redirect_to_obj_page: # Check if obj has unidentified FormZ Elements:
            msg = format_html(
                _('The {name} "{obj}" was changed successfully. You may edit it again below.'),
                **msg_dict
            )
            self.message_user(request, msg, messages.SUCCESS)
            redirect_url = request.path
            redirect_url = add_preserved_filters({'preserved_filters': preserved_filters, 'opts': opts}, redirect_url)
            return HttpResponseRedirect(redirect_url)

        elif "_saveasnew" in request.POST:
            msg = format_html(
                _('The {name} "{obj}" was added successfully. You may edit it again below.'),
                **msg_dict
            )
            self.message_user(request, msg, messages.SUCCESS)
            redirect_url = reverse('admin:%s_%s_change' %
                                   (opts.app_label, opts.model_name),
                                   args=(obj.pk,),
                                   current_app=self.admin_site.name)
            redirect_url = add_preserved_filters({'preserved_filters': preserved_filters, 'opts': opts}, redirect_url)
            return HttpResponseRedirect(redirect_url)

        elif "_addanother" in request.POST:
            msg = format_html(
                _('The {name} "{obj}" was changed successfully. You may add another {name} below.'),
                **msg_dict
            )
            self.message_user(request, msg, messages.SUCCESS)
            redirect_url = reverse('admin:%s_%s_add' %
                                   (opts.app_label, opts.model_name),
                                   current_app=self.admin_site.name)
            redirect_url = add_preserved_filters({'preserved_filters': preserved_filters, 'opts': opts}, redirect_url)
            return HttpResponseRedirect(redirect_url)

        else:
            msg = format_html(
                _('The {name} "{obj}" was changed successfully.'),
                **msg_dict
            )
            self.message_user(request, msg, messages.SUCCESS)
            return self.response_post_save_change(request, obj)

    specific_fields = ['lab_identifier', 'typ_e',
                     'transgene', 'transgene_position', 'transgene_plasmids',
                     'mutation', 'mutation_type', 'mutation_position',
                     'reference_strain', 'made_by_method', 'made_by_person', 'formz_elements']
    ownership_fields = ['created_date_time', 'last_changed_date_time', 'created_by']

    def get_form(self, request, obj=None, **kwargs):

        form = super().get_form(request, obj, **kwargs)

        if (obj and obj.typ_e == 't') or self.allele_type == 't':
            if "typ_e" in form.base_fields:
                form.base_fields["typ_e"].initial = 't'
                form.base_fields["typ_e"].disabled = True
            required_fields = ['transgene', 'transgene_position', 'transgene_plasmids']
            [setattr(form.base_fields[f], 'required', True) for f in required_fields]

        elif (obj and obj.typ_e == 'm') or self.allele_type == 'm':
            if "typ_e" in form.base_fields:
                form.base_fields["typ_e"].initial = 'm'
                form.base_fields["typ_e"].disabled = True
            required_fields = ['mutation', 'mutation_type', 'mutation_position']
            [setattr(form.base_fields[f], 'required', True) for f in required_fields]

        return form

    def get_readonly_fields(self, request, obj=None):
        '''Override default get_readonly_fields to define user-specific read-only fields
        If a user is not a superuser, lab manager or the user who created a record
        return all fields as read-only
        'created_date_time' and 'last_changed_date_time' fields must always be read-only
        because their set by Django itself'''

        if obj:
            if request.user.has_perm('collection.change_wormstrainallele', obj):
                return ['lab_identifier', 'typ_e', 'map_png', 'created_date_time',
                        'last_changed_date_time', 'created_by',]
            if not (request.user.is_superuser
                    or request.user.groups.filter(name='Lab manager').exists()
                    or request.user == obj.created_by
                    or obj.created_by.labuser.is_principal_investigator
                    or obj.created_by.groups.filter(name='Past member').exists()):
                return self.specific_fields + self.ownership_fields + ['note', 'map', 'map_gbk', 'map_png']
            else:
                if (obj.created_by.labuser.is_principal_investigator
                    or obj.created_by.groups.filter(name='Past member').exists()) \
                   and not (request.user.is_superuser or request.user.groups.filter(name='Lab manager').exists()):
                     # Show map and note as editable fields, if record belongs to PI or old member
                    return self.specific_fields + ['map_png'] + self.ownership_fields
                else:
                    return ['lab_identifier', 'map_png', 'created_date_time',
                            'last_changed_date_time', 'created_by']
        else:
            return ['created_date_time', 'last_changed_date_time']
    
    def add_view(self, request, extra_context=None):
        '''Override default add_view to show only desired fields'''

        fields = self.specific_fields + ['note', 'map', 'map_gbk']
        self.allele_type = request.GET.get('allele_type')

        if self.allele_type == 't':
            self.fields = [f for f in fields if not f.startswith('mutation')]
        elif self.allele_type == 'm':
            self.fields = [f for f in fields if not f.startswith('transgene')]
        else:
            self.fields = []

        return super(WormStrainAllelePage,self).add_view(request)

    def change_view(self, request, object_id, extra_context=None):
        '''Override default change_view to show only desired fields'''

        self.can_change = False

        extra_context = extra_context or {}
        extra_context['show_disapprove'] = False
        extra_context['show_formz'] = False

        if object_id:
            
            obj = self.model.objects.get(pk=object_id)

            if request.user == obj.created_by \
            or request.user.groups.filter(name='Lab manager').exists() \
            or request.user.labuser.is_principal_investigator \
            or request.user.is_superuser \
            or obj.created_by.labuser.is_principal_investigator \
            or obj.created_by.groups.filter(name='Past member') \
            or request.user.has_perm('collection.change_wormstrainallele', obj):
                    
                    self.can_change = True
                    
                    if (obj.created_by.labuser.is_principal_investigator
                        or obj.created_by.groups.filter(name='Past member')) \
                    and not request.user.has_perm('collection.change_wormstrainallele', obj):
                        
                        extra_context.update({'show_close': True,
                                        'show_save_and_add_another': False,
                                        'show_save_and_continue': True,
                                        'show_duplicate': False,
                                        'show_save': True,
                                        'show_obj_permission': False,
                                        'show_redetect_save': True})
                    else:

                        extra_context.update({'show_close': True,
                                    'show_save_and_add_another': True,
                                    'show_save_and_continue': True,

                                    'show_save': True,
                                    'show_obj_permission': True,
                                    'show_redetect_save': True})

            else:
                
                extra_context.update({'show_close': True,
                                 'show_save_and_add_another': True,
                                 'show_save_and_continue': True,

                                 'show_save': True,
                                 'show_obj_permission': False,
                                 'show_redetect_save': False})

            fields = self.specific_fields + ['note', 'map', 'map_gbk', 'map_png'] + self.ownership_fields

            if obj.typ_e == 't':
                self.fields = [f for f in fields if not f.startswith('mutation')]
            elif obj.typ_e == 'm':
                self.fields = [f for f in fields if not f.startswith('transgene')]
            else:
                self.fields = fields

        return super(WormStrainAllelePage, self).change_view(request, object_id, extra_context=extra_context)

    def get_map_short_name(self, instance):

        if instance.map:
            ove_dna_preview = instance.get_ove_url_map()
            ove_gbk_preview =  instance.get_ove_url_map_gbk()
            return mark_safe(f'<a class="magnific-popup-img-map" href="{instance.map_png.url}">png</a> | '
                             f'<a href="{instance.map.url}">dna</a> <a class="magnific-popup-iframe-map-dna" href="{ove_dna_preview}">⊙</a> | '
                             f'<a href="{instance.map_gbk.url}">gbk</a> <a class="magnific-popup-iframe-map-gbk" href="{ove_gbk_preview}">⊙</a>')
        else:
            return ''
    get_map_short_name.short_description = 'Map'

    def obj_perms_manage_view(self, request, object_pk):
        """
        Main object Guardian permissions view. 

        Customized to allow only record owner to change permissions
        """
        obj = self.model.objects.get(pk=object_pk)
        
        if obj:
            if not (request.user.is_superuser
                    or request.user.groups.filter(name='Lab manager').exists()
                    or request.user == obj.created_by
                    or request.user.labuser.is_principal_investigator):
                messages.error(request, 'Nice try, you are allowed to change the permissions of your own records only.')
                return HttpResponseRedirect("..")
        return super(WormStrainAllelePage,self).obj_perms_manage_view(request, object_pk)

    def get_history_array_fields(self):

        return {**super(WormStrainAllelePage, self).get_history_array_fields(),
                'history_formz_elements': FormZBaseElement,
                }