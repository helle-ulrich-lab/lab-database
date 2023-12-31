from django.contrib import admin
from django.http import HttpResponse
from django.utils.safestring import mark_safe
from django.forms import TextInput
from django.db.models import CharField
from django.contrib.auth.models import User
from django.urls import reverse, resolve
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
from djangoql.schema import StrField

import xlrd
import csv
import time
from urllib.parse import quote as urlquote

from common.shared_elements import SimpleHistoryWithSummaryAdmin
from common.shared_elements import AdminChangeFormWithNavigation
from common.shared_elements import SearchFieldOptUsername
from common.shared_elements import SearchFieldOptLastname
from .admin import FieldIntegratedPlasmidM2M
from .admin import FieldEpisomalPlasmidM2M
from .admin import FieldCassettePlasmidM2M
from .admin import FieldCreated
from .admin import FieldLastChanged
from .admin import FieldFormZProject
from .admin import FieldParent1
from .admin import FieldParent2
from .admin import formz_as_html
from .admin import Approval
from .admin import SortAutocompleteResultsId

from ..models.plasmid import Plasmid
from formz.models import FormZProject
from formz.models import FormZBaseElement
from formz.models import GenTechMethod

from ..models.sc_pombe_strain import ScPombeStrain
from ..models.sc_pombe_strain import ScPombeStrainEpisomalPlasmid


class SearchFieldOptUsernameScPom(SearchFieldOptUsername):

    id_list = ScPombeStrain.objects.all().values_list('created_by', flat=True).distinct()

class SearchFieldOptLastnameScPom(SearchFieldOptLastname):

    id_list = ScPombeStrain.objects.all().values_list('created_by', flat=True).distinct()

class FieldEpisomalPlasmidFormZProjectScPom(StrField):
    
    name = 'episomal_plasmids_formz_projects_title'
    suggest_options = True

    def get_options(self, search):
        return FormZProject.objects.all().values_list('short_title', flat=True)

    def get_lookup_name(self):
        return 'scpombestrainepisomalplasmid__formz_projects__short_title'

class ScPombeStrainQLSchema(DjangoQLSchema):
    '''Customize search functionality'''
    
    include = (ScPombeStrain, User) # Include only the relevant models to be searched

    def get_fields(self, model):
        '''Define fields that can be searched'''
        
        if model == ScPombeStrain:
            return ['id', 'box_number', FieldParent1(), FieldParent2(), 'parental_strain', 'mating_type', 
            'auxotrophic_marker', 'name', FieldIntegratedPlasmidM2M(), FieldCassettePlasmidM2M(), FieldEpisomalPlasmidM2M(),
            'phenotype', 'received_from', 'comment', 'created_by', FieldCreated(), FieldLastChanged(),
            FieldFormZProject(), FieldEpisomalPlasmidFormZProjectScPom()]
        elif model == User:
            return [SearchFieldOptUsernameScPom(), SearchFieldOptLastnameScPom()]
        return super(ScPombeStrainQLSchema, self).get_fields(model)

class ScPombeStrainExportResource(resources.ModelResource):
    """Defines a custom export resource class for ScPombeStrain"""

    additional_parental_strain_info = Field(attribute='parental_strain', column_name='additional_parental_strain_info')
    episomal_plasmids_in_stock = Field()

    def dehydrate_episomal_plasmids_in_stock(self, strain):
        return str(tuple(strain.episomal_plasmids.filter(scpombestrainepisomalplasmid__present_in_stocked_strain=True).values_list('id', flat=True))).replace(" ", "").replace(',)', ')')[1:-1]

    class Meta:
        model = ScPombeStrain
        fields = ('id', 'box_number', 'parent_1', 'parent_2', 'additional_parental_strain_info', 'mating_type',
        'auxotrophic_marker', 'name', 'phenotype', 'integrated_plasmids', 'cassette_plasmids', 'episomal_plasmids_in_stock',
        'received_from', 'comment', 'created_date_time', 'created_by__username')
        export_order = ('id', 'box_number', 'parent_1', 'parent_2', 'additional_parental_strain_info', 'mating_type',
        'auxotrophic_marker', 'name', 'phenotype', 'integrated_plasmids', 'cassette_plasmids', 'episomal_plasmids_in_stock',
        'received_from', 'comment', 'created_date_time', 'created_by__username')

def export_scpombestrain(modeladmin, request, queryset):
    """Export ScPombeStrain"""

    export_data = ScPombeStrainExportResource().export(queryset)

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
export_scpombestrain.short_description = "Export selected strains"

class ScPombeStrainForm(forms.ModelForm):
    
    def clean_name(self):
        """Check if name is unique before saving"""
        
        if not self.instance.pk:
            qs = ScPombeStrain.objects.filter(name=self.cleaned_data["name"])
            if qs:
                raise forms.ValidationError('Strain with this name already exists.')
            else:
                return self.cleaned_data["name"]
        else:
            return self.cleaned_data["name"]

class ScPombeStrainEpisomalPlasmidInline(admin.TabularInline):
    
    autocomplete_fields = ['plasmid', 'formz_projects']
    model = ScPombeStrainEpisomalPlasmid
    verbose_name_plural = mark_safe('Episomal plasmids <span style="text-transform:lowercase;">(highlighted in <span style="color:var(--accent)">yellow</span>, if present in the stocked strain</span>)')
    verbose_name = 'Episomal Plasmid'
    classes = ['collapse']
    ordering = ("-present_in_stocked_strain",'id',)
    extra = 0
    template = 'admin/tabular.html'
    
    def get_parent_object(self, request):
        """
        Returns the parent object from the request or None.

        Note that this only works for Inlines, because the `parent_model`
        is not available in the regular admin.ModelAdmin as an attribute.
        """

        resolved = resolve(request.path_info)
        if resolved.kwargs:
            return self.parent_model.objects.get(pk=resolved.kwargs['object_id'])
        return None

    def get_queryset(self,request):

        """Modify to conditionally collapse inline if there is an episomal 
        plasmid in the -80 stock"""

        parent_object = self.get_parent_object(request)
        if parent_object:
            parent_obj_episomal_plasmids = parent_object.episomal_plasmids.all()
            if parent_obj_episomal_plasmids.filter(scpombestrainepisomalplasmid__present_in_stocked_strain=True):
                self.classes = []
        else:
            self.classes = []
        return super(ScPombeStrainEpisomalPlasmidInline, self).get_queryset(request)

class ScPombeStrainPage(DjangoQLSearchMixin, SimpleHistoryWithSummaryAdmin, Approval, AdminChangeFormWithNavigation, SortAutocompleteResultsId):
    list_display = ('id', 'name', 'auxotrophic_marker', 'mating_type', 'approval',)
    list_display_links = ('id',)
    list_per_page = 25
    formfield_overrides = {CharField: {'widget': TextInput(attrs={'size':'93'})},}
    djangoql_schema = ScPombeStrainQLSchema
    djangoql_completion_enabled_by_default = False
    actions = [export_scpombestrain, formz_as_html]
    form = ScPombeStrainForm
    search_fields = ['id', 'name']
    autocomplete_fields = ['parent_1', 'parent_2', 'integrated_plasmids', 'cassette_plasmids', 
                           'formz_projects', 'formz_gentech_methods', 'formz_elements']
    inlines = [ScPombeStrainEpisomalPlasmidInline]

    def save_model(self, request, obj, form, change):
        '''Override default save_model to limit a user's ability to save a record
        Superusers and lab managers can change all records
        Regular users can change only their own records
        Guests cannot change any record'''
        
        if obj.pk == None:
            
            obj.id = ScPombeStrain.objects.order_by('-id').first().id + 1 if ScPombeStrain.objects.exists() else 1
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
                ScPombeStrain.objects.filter(id=obj.pk).update(last_changed_date_time=original_last_changed_date_time)
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
                    ScPombeStrain.objects.filter(id=obj.pk).update(last_changed_date_time=original_last_changed_date_time)
                return
        
            if self.can_change:

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

            else:
                raise PermissionDenied
    
    def get_readonly_fields(self, request, obj=None):
        '''Override default get_readonly_fields to define user-specific read-only fields
        If a user is not a superuser, lab manager or the user who created a record
        return all fields as read-only 
        'created_date_time' and 'last_changed_date_time' fields must always be read-only
        because their set by Django itself'''
        
        if obj:
            if self.can_change:
                return ['created_date_time', 'created_approval_by_pi', 'last_changed_date_time', 'last_changed_approval_by_pi','created_by',]
            else:
                return ['box_number', 'parent_1', 'parent_2', 'parental_strain', 'mating_type', 'auxotrophic_marker', 'name',
                        'integrated_plasmids', 'cassette_plasmids', 'phenotype', 'received_from', 'comment', 'created_date_time', 
                        'created_approval_by_pi', 'last_changed_date_time', 'last_changed_approval_by_pi', 'created_by',
                        'formz_projects', 'formz_risk_group', 'formz_gentech_methods', 'formz_elements', 'destroyed_date']
        else:
            return ['created_date_time', 'created_approval_by_pi', 'last_changed_date_time', 'last_changed_approval_by_pi','created_by',]

    def save_related(self, request, form, formsets, change):
        
        super(ScPombeStrainPage, self).save_related(request, form, formsets, change)

        # Keep a record of the IDs of linked M2M fields in the main strain record
        # Not pretty, but it works

        obj = ScPombeStrain.objects.get(pk=form.instance.id)
        
        integrated_plasmids = obj.integrated_plasmids.order_by('id').distinct('id')
        cassette_plasmids = obj.cassette_plasmids.order_by('id').distinct('id')
        episomal_plasmids = obj.episomal_plasmids.order_by('id').distinct('id')

        obj.history_integrated_plasmids = list(integrated_plasmids.values_list('id', flat=True)) if integrated_plasmids.exists() else []
        obj.history_cassette_plasmids = list(cassette_plasmids.values_list('id', flat=True)) if cassette_plasmids.exists() else []
        obj.history_episomal_plasmids = list(episomal_plasmids.values_list('id', flat=True)) if episomal_plasmids.exists() else []

        plasmid_id_list = integrated_plasmids | cassette_plasmids | episomal_plasmids.filter(sacerevisiaestrainepisomalplasmid__present_in_stocked_strain=True) # Merge querysets
        if plasmid_id_list:
            obj.history_all_plasmids_in_stocked_strain = list(plasmid_id_list.order_by('id').distinct('id').values_list('id', flat=True))

        obj.history_formz_projects = list(obj.formz_projects.order_by('id').distinct('id').values_list('id', flat=True)) if obj.formz_projects.exists() else []
        obj.history_formz_gentech_methods = list(obj.formz_gentech_methods.order_by('id').distinct('id').values_list('id', flat=True)) if obj.formz_gentech_methods.exists() else []
        obj.history_formz_elements = list(obj.formz_elements.order_by('id').distinct('id').values_list('id', flat=True)) if obj.formz_elements.exists() else []

        obj.save_without_historical_record()

        history_obj = obj.history.latest()
        history_obj.history_integrated_plasmids = obj.history_integrated_plasmids
        history_obj.history_cassette_plasmids = obj.history_cassette_plasmids
        history_obj.history_episomal_plasmids = obj.history_episomal_plasmids
        history_obj.history_all_plasmids_in_stocked_strain = obj.history_all_plasmids_in_stocked_strain
        history_obj.history_formz_projects = obj.history_formz_projects
        history_obj.history_formz_gentech_methods = obj.history_formz_gentech_methods
        history_obj.history_formz_elements = obj.history_formz_elements
        history_obj.save()

        # Clear non-relevant fields for in-stock episomal plasmids

        for in_stock_episomal_plasmid in ScPombeStrainEpisomalPlasmid.objects.filter(scpombe_strain__id=form.instance.id).filter(present_in_stocked_strain=True):
            in_stock_episomal_plasmid.formz_projects.clear()

    def add_view(self,request,extra_context=None):
        '''Override default add_view to show only desired fields'''

        self.fieldsets = (
        (None, {
            'fields': ('box_number', 'parent_1', 'parent_2', 'parental_strain', 'mating_type', 'auxotrophic_marker', 'name',
        'integrated_plasmids', 'cassette_plasmids', 'phenotype', 'received_from', 'comment',)
        }),
        ('FormZ', {
            'fields': ('formz_projects', 'formz_risk_group', 'formz_gentech_methods', 'formz_elements', 'destroyed_date')
        }),
        )

        return super(ScPombeStrainPage,self).add_view(request)

    def change_view(self,request,object_id,extra_context=None):
        '''Override default change_view to show only desired fields'''
        
        self.can_change = False

        extra_context = extra_context or {}
        extra_context['show_disapprove'] = False
        extra_context['show_formz'] = False

        if object_id:
            
            self.can_change = request.user == ScPombeStrain.objects.get(pk=object_id).created_by or \
                    request.user.groups.filter(name='Lab manager').exists() or \
                    request.user.is_superuser or request.user.labuser.is_principal_investigator
            extra_context = extra_context or {}
            extra_context['show_formz'] = True
            obj = ScPombeStrain.objects.get(pk=object_id)
            
            if obj.history_all_plasmids_in_stocked_strain:
                extra_context['plasmid_id_list'] = tuple(obj.history_all_plasmids_in_stocked_strain)
            
            if request.user == obj.created_by or request.user.groups.filter(name='Lab manager').exists() or \
                request.user.is_superuser or request.user.labuser.is_principal_investigator:

                extra_context.update({'show_close': True,
                                'show_save_and_add_another': True,
                                'show_save_and_continue': True,
                                'show_save_as_new': True,
                                'show_save': True,
                                'show_obj_permission': True
                                })

            else:

                 extra_context.update({'show_close': True,
                                 'show_save_and_add_another': False,
                                 'show_save_and_continue': False,
                                 'show_save_as_new': False,
                                 'show_save': False,
                                 'show_obj_permission': False})
            
            extra_context['show_disapprove'] = True if request.user.groups.filter(name='Approval manager').exists() else False
            extra_context['show_formz'] = True

        if '_saveasnew' in request.POST:
            self.fieldsets = (
            (None, {
                'fields': ('box_number', 'parent_1', 'parent_2', 'parental_strain', 'mating_type', 'auxotrophic_marker', 'name',
                'integrated_plasmids', 'cassette_plasmids', 'phenotype', 'received_from', 'comment', 'created_date_time', 
                'created_approval_by_pi', 'last_changed_date_time', 'last_changed_approval_by_pi','created_by',)
            }),
            ('FormZ', {
                'fields': ('formz_projects', 'formz_risk_group', 'formz_gentech_methods', 'formz_elements', 'destroyed_date')
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
            self.fieldsets = (
            (None, {
                'fields': ('box_number', 'parent_1', 'parent_2', 'parental_strain', 'mating_type', 'auxotrophic_marker', 'name',
                'integrated_plasmids', 'cassette_plasmids', 'phenotype', 'received_from', 'comment', 'created_date_time', 
                'created_approval_by_pi', 'last_changed_date_time', 'last_changed_approval_by_pi','created_by',)
            }),
            ('FormZ', {
                'classes': ('collapse',) if not request.GET.get('_approval', '') else tuple(),
                'fields': ('formz_projects', 'formz_risk_group', 'formz_gentech_methods', 'formz_elements', 'destroyed_date')
            }),
            )

        return super(ScPombeStrainPage,self).change_view(request,object_id, extra_context=extra_context)

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
        
        return super(ScPombeStrainPage,self).response_change(request,obj)

    def get_history_array_fields(self):

        return {**super(ScPombeStrainPage, self).get_history_array_fields(),
                'history_integrated_plasmids': Plasmid,
                'history_cassette_plasmids': Plasmid,
                'history_episomal_plasmids': Plasmid,
                'history_all_plasmids_in_stocked_strain': Plasmid,
                'history_formz_projects': FormZProject,
                'history_formz_gentech_methods': GenTechMethod,
                'history_formz_elements': FormZBaseElement,
                }