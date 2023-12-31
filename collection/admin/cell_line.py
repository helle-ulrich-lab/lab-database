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

from djangoql.schema import DjangoQLSchema
from djangoql.admin import DjangoQLSearchMixin
from import_export import resources
from import_export.fields import Field
from djangoql.schema import StrField
from djangoql.schema import IntField

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
from .admin import FieldCreated
from .admin import FieldLastChanged
from .admin import FieldFormZProject
from .admin import formz_as_html
from .admin import CustomGuardedModelAdmin
from .admin import Approval
from .admin import SortAutocompleteResultsId

from ..models.cell_line import CellLine
from ..models.cell_line import CellLineDoc
from ..models.cell_line import CellLineEpisomalPlasmid
from ..models.plasmid import Plasmid
from formz.models import FormZProject
from formz.models import FormZBaseElement
from formz.models import Species
from formz.models import GenTechMethod


class CellLineDocPage(admin.ModelAdmin):
    
    list_display = ('id','name',)
    list_display_links = ('id','name', )
    list_per_page = 25
    ordering = ['id']

    def has_module_permission(self, request):
        '''Hide module from Admin'''
        return False

    def get_readonly_fields(self, request, obj=None):
        '''Override default get_readonly_fields'''

        if obj:
            return ['name', 'typ_e', 'date_of_test', 'cell_line', 'created_date_time',]
    
    def add_view(self,request,extra_context=None):
        '''Override default add_view to show only desired fields'''

        self.fields = (['name', 'typ_e', 'cell_line', 'comment', 'date_of_test'])
        return super(CellLineDocPage,self).add_view(request)

    def change_view(self,request,object_id,extra_context=None):
        '''Override default change_view to show only desired fields'''

        self.fields = (['name', 'typ_e', 'date_of_test', 'cell_line', 'comment', 'created_date_time',])
        return super(CellLineDocPage,self).change_view(request,object_id)

class CellLineDocInline(admin.TabularInline):
    """Inline to view existing cell line documents"""

    model = CellLineDoc
    verbose_name_plural = "Existing docs"
    extra = 0
    fields = ['typ_e', 'date_of_test', 'get_doc_short_name', 'comment']
    readonly_fields = ['get_doc_short_name', 'typ_e', 'date_of_test']

    def has_add_permission(self, request, obj):
        return False
    
    def get_doc_short_name(self, instance):
        '''This function allows you to define a custom field for the list view to
        be defined in list_display as the name of the function, e.g. in this case
        list_display = ('id', 'name', 'selection', 'get_plasmidmap_short_name','created_by',)'''
        if instance.name:
            return mark_safe('<a href="{}">View</a>'.format(str(instance.name.url)))
        else:
            return ''
    get_doc_short_name.short_description = 'Document'

class AddCellLineDocInline(admin.TabularInline):
    """Inline to add new cell line documents"""
    
    model = CellLineDoc
    verbose_name_plural = "New docs"
    extra = 0
    fields = ['typ_e', 'date_of_test', 'name','comment']

    def has_change_permission(self, request, obj=None):
        return False

    def get_queryset(self, request):
        return CellLineDoc.objects.none()

#################################################
#                CELL LINE PAGES                #
#################################################

class FieldParentalLine(IntField):

    name = 'parental_line_id'
    
    def get_lookup_name(self):
        return 'parental_line__id'

class SearchFieldOptUsernameCellLine(SearchFieldOptUsername):

    id_list = CellLine.objects.all().values_list('created_by', flat=True).distinct()

class SearchFieldOptLastnameCellLine(SearchFieldOptLastname):

    id_list = CellLine.objects.all().values_list('created_by', flat=True).distinct()

class FieldEpisomalPlasmidFormZProjectCellLine(StrField):
    
    name = 'episomal_plasmids_formz_projects_title'
    suggest_options = True

    def get_options(self, search):
        return FormZProject.objects.all().values_list('short_title', flat=True)

    def get_lookup_name(self):
        return 'celllineepisomalplasmid__formz_projects__short_title'

class CellLineQLSchema(DjangoQLSchema):
    '''Customize search functionality'''
    
    include = (CellLine, User) # Include only the relevant models to be searched

    def get_fields(self, model):
        '''Define fields that can be searched'''
        
        if model == CellLine:
            return ['id', 'name', 'box_name', 'alternative_name', FieldParentalLine(), 'organism', 'cell_type_tissue', 'culture_type', 
            'growth_condition','freezing_medium', 'received_from', FieldIntegratedPlasmidM2M(), FieldEpisomalPlasmidM2M(),'description_comment', 
            'created_by', FieldCreated(), FieldLastChanged(), FieldFormZProject(), FieldEpisomalPlasmidFormZProjectCellLine()]
        elif model == User:
            return [SearchFieldOptUsernameCellLine(), SearchFieldOptLastnameCellLine()]
        return super(CellLineQLSchema, self).get_fields(model)

class CellLineExportResource(resources.ModelResource):
    """Defines a custom export resource class for CellLine"""
    organism_name = Field()
    
    def dehydrate_organism_name(self, strain):
                
        return str(strain.organism)
    
    class Meta:
        model = CellLine
        fields = ('id', 'name', 'box_name', 'alternative_name', 'parental_line', 'organism_name', 'cell_type_tissue', 
                'culture_type', 'growth_condition', 'freezing_medium', 'received_from', 'description_comment', 
                'integrated_plasmids', 'created_date_time', 'created_by__username',)
        export_order = ('id', 'name', 'box_name', 'alternative_name', 'parental_line', 'organism_name', 'cell_type_tissue', 
                'culture_type', 'growth_condition', 'freezing_medium', 'received_from', 'description_comment', 
                'integrated_plasmids', 'created_date_time', 'created_by__username',)

def export_cellline(modeladmin, request, queryset):
    """Export CellLine"""

    export_data = CellLineExportResource().export(queryset)

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
export_cellline.short_description = "Export selected cell lines"

class CellLineEpisomalPlasmidInline(admin.TabularInline):
    
    autocomplete_fields = ['plasmid', 'formz_projects']
    model = CellLineEpisomalPlasmid
    verbose_name_plural = mark_safe('Transiently transfected plasmids <span style="text-transform:lowercase;">(virus packaging plasmids are highlighted in <span style="color:var(--accent)">yellow</span>)</span>')
    verbose_name = 'Episomal Plasmid'
    classes = ['collapse']
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

        """Do not show as collapsed in add view"""

        parent_object = self.get_parent_object(request)

        if parent_object:
            parent_obj_episomal_plasmids = parent_object.episomal_plasmids.all()
            if parent_obj_episomal_plasmids.filter(celllineepisomalplasmid__s2_work_episomal_plasmid=True):
                self.classes = []
        else:
            self.classes = []
        return super(CellLineEpisomalPlasmidInline, self).get_queryset(request)

class CellLinePage(DjangoQLSearchMixin, SimpleHistoryWithSummaryAdmin, CustomGuardedModelAdmin, Approval, AdminChangeFormWithNavigation, SortAutocompleteResultsId):
    
    list_display = ('id', 'name', 'box_name', 'created_by', 'approval')
    list_display_links = ('id',)
    list_per_page = 25
    formfield_overrides = {CharField: {'widget': TextInput(attrs={'size':'93'})},}
    djangoql_schema = CellLineQLSchema
    djangoql_completion_enabled_by_default = False
    inlines = [CellLineEpisomalPlasmidInline, CellLineDocInline, AddCellLineDocInline]
    actions = [export_cellline, formz_as_html]
    search_fields = ['id', 'name']
    autocomplete_fields = ['parental_line', 'integrated_plasmids', 'formz_projects', 'zkbs_cell_line', 'formz_gentech_methods', 'formz_elements']

    def save_model(self, request, obj, form, change):
        '''Override default save_model to limit a user's ability to save a record
        Superusers and lab managers can change all records
        Regular users can change only their own records
        Guests cannot change any record'''

        if obj.pk == None:
            
            obj.id = CellLine.objects.order_by('-id').first().id + 1 if CellLine.objects.exists() else 1
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
                CellLine.objects.filter(id=obj.pk).update(last_changed_date_time=original_last_changed_date_time)
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
                    CellLine.objects.filter(id=obj.pk).update(last_changed_date_time=original_last_changed_date_time)
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
    
    def get_readonly_fields(self, request, obj=None):
        '''Override default get_readonly_fields to define user-specific read-only fields
        If a user is not a superuser, lab manager or the user who created a record
        return all fields as read-only 
        'created_date_time' and 'last_changed_date_time' fields must always be read-only
        because their set by Django itself'''

        if obj:
            if self.can_change:
                    return ['created_date_time', 'created_approval_by_pi', 'last_changed_date_time', 'last_changed_approval_by_pi', 'created_by']
            else:
                return ['name', 'box_name', 'alternative_name', 'parental_line', 'organism', 'cell_type_tissue', 'culture_type', 'growth_condition',
                'freezing_medium', 'received_from', 'integrated_plasmids', 'description_comment', 's2_work', 'created_date_time', 'created_approval_by_pi',
                'last_changed_date_time', 'last_changed_approval_by_pi', 'created_by', 'formz_projects', 'formz_risk_group','zkbs_cell_line', 
                'formz_gentech_methods', 'formz_elements', 'destroyed_date',]
        else:
            return ['created_date_time', 'created_approval_by_pi', 'last_changed_date_time', 'last_changed_approval_by_pi',]
    
    def save_related(self, request, form, formsets, change):
        
        super(CellLinePage, self).save_related(request, form, formsets, change)

        # Keep a record of the IDs of linked M2M fields in the main strain record
        # Not pretty, but it works

        obj = CellLine.objects.get(pk=form.instance.id)

        obj.history_integrated_plasmids = list(obj.integrated_plasmids.order_by('id').distinct('id').values_list('id', flat=True)) if obj.integrated_plasmids.exists() else []
        obj.history_episomal_plasmids = list(obj.episomal_plasmids.order_by('id').distinct('id').values_list('id', flat=True)) if obj.episomal_plasmids.exists() else []

        obj.history_formz_projects = list(obj.formz_projects.distinct('id').order_by('id').values_list('id', flat=True)) if obj.formz_projects.exists() else []
        obj.history_formz_gentech_methods = list(obj.formz_gentech_methods.distinct('id').order_by('id').values_list('id', flat=True)) if obj.formz_gentech_methods.exists() else []
        obj.history_formz_elements = list(obj.formz_elements.distinct('id').order_by('id').values_list('id', flat=True)) if obj.formz_elements.exists() else []
        obj.history_documents = list(obj.celllinedoc_set.order_by('id').distinct('id').values_list('id', flat=True)) if obj.celllinedoc_set.exists() else []

        obj.save_without_historical_record()

        history_obj = obj.history.latest()
        history_obj.history_integrated_plasmids = obj.history_integrated_plasmids
        history_obj.history_episomal_plasmids = obj.history_episomal_plasmids
        history_obj.history_formz_projects = obj.history_formz_projects
        history_obj.history_formz_gentech_methods = obj.history_formz_gentech_methods
        history_obj.history_formz_elements = obj.history_formz_elements
        history_obj.history_documents = obj.history_documents
        history_obj.save()

    def add_view(self,request,extra_context=None):
        '''Override default add_view to show only desired fields'''

        self.fieldsets = (
        (None, {
            'fields': ('name', 'box_name', 'alternative_name', 'parental_line', 'organism', 'cell_type_tissue', 'culture_type', 'growth_condition',
                'freezing_medium', 'received_from', 'integrated_plasmids', 'description_comment', 's2_work',)
        }),
        ('FormZ', {
            'fields': ('formz_projects', 'formz_risk_group','zkbs_cell_line', 'formz_gentech_methods', 'formz_elements', 'destroyed_date',)
        }),
        )

        return super(CellLinePage,self).add_view(request)

    def change_view(self,request,object_id,extra_context=None):
        '''Override default change_view to show only desired fields'''

        self.can_change = False

        extra_context = extra_context or {}
        extra_context['show_disapprove'] = False
        extra_context['show_formz'] = False
        
        if object_id:
            
            obj = CellLine.objects.get(pk=object_id)
            
            if obj.history_integrated_plasmids:
                extra_context['plasmid_id_list'] = tuple(obj.history_integrated_plasmids)
        
            if request.user == obj.created_by or request.user.groups.filter(name='Lab manager').exists() or \
                request.user.labuser.is_principal_investigator or request.user.is_superuser or \
                request.user.has_perm('collection.change_cellline', obj):
                
                self.can_change = True
                
                extra_context.update({'show_close': True,
                            'show_save_and_add_another': True,
                            'show_save_and_continue': True,
                            'show_save_as_new': True,
                            'show_save': True,
                            'show_obj_permission': True,})
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
                'fields': ('name', 'box_name', 'alternative_name', 'parental_line', 'organism', 'cell_type_tissue', 'culture_type', 'growth_condition',
                    'freezing_medium', 'received_from', 'integrated_plasmids', 'description_comment', 's2_work',)
            }),
            ('FormZ', {
                'fields': ('formz_projects', 'formz_risk_group','zkbs_cell_line', 'formz_gentech_methods', 'formz_elements', 'destroyed_date',)
            }),
            )
            extra_context.update({'show_save_and_continue': False,
                                 'show_save': False,
                                 'show_save_and_add_another': False,
                                 'show_disapprove': False,
                                 'show_formz': False,
                                 'show_save_and_continue': False,
                                 'show_obj_permission': False
                                 })

        else:
            self.fieldsets = (
            (None, {
                'fields': ('name', 'box_name', 'alternative_name', 'parental_line', 'organism', 'cell_type_tissue', 'culture_type', 'growth_condition',
                    'freezing_medium', 'received_from', 'integrated_plasmids', 'description_comment', 's2_work', 'created_date_time', 'created_approval_by_pi',
                'last_changed_date_time', 'last_changed_approval_by_pi', 'created_by',)
            }),
            ('FormZ', {
                'classes': ('collapse',) if not request.GET.get('_approval', '') else tuple(),
                'fields': ('formz_projects', 'formz_risk_group','zkbs_cell_line', 'formz_gentech_methods', 'formz_elements', 'destroyed_date',)
            }),
            )
            
        return super(CellLinePage,self).change_view(request,object_id,extra_context=extra_context)

    def get_formsets_with_inlines(self, request, obj=None):
        """Remove AddCellLineDocInline from add/change form if user who
        created a CellLine object is not the request user a lab manager
        or a superuser"""
        
        if obj:
            for inline in self.get_inline_instances(request, obj):
                if inline.verbose_name_plural == 'Existing docs':
                    yield inline.get_formset(request, obj), inline
                else:
                    if not request.user.groups.filter(name='Guest').exists():
                        yield inline.get_formset(request, obj), inline
        else:
            for inline in self.get_inline_instances(request, obj):
                if inline.verbose_name_plural == 'Existing docs':
                    continue
                else:
                    yield inline.get_formset(request, obj), inline
    
    def obj_perms_manage_view(self, request, object_pk):
        """
        Main object Guardian permissions view. 

        Customized to allow only record owner to change permissions
        """
        obj = CellLine.objects.get(pk=object_pk)
        
        if obj:
            if not (request.user.is_superuser or request.user.groups.filter(name='Lab manager').exists() or \
                request.user == obj.created_by or request.user.labuser.is_principal_investigator):
                messages.error(request, 'Nice try, you are allowed to change the permissions of your own records only.')
                return HttpResponseRedirect("..")
        return super(CellLinePage,self).obj_perms_manage_view(request, object_pk)
    
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
        
        return super(CellLinePage,self).response_change(request,obj)
    
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        
        try:
            request.resolver_match.args[0]
        except:
            
            # Exclude certain users from the 'Created by' field in the order form

            if db_field.name == 'organism':
                kwargs["queryset"] = Species.objects.filter(show_in_cell_line_collection=True)

        return super(CellLinePage, self).formfield_for_foreignkey(db_field, request, **kwargs)

    def get_history_array_fields(self):

        return {**super(CellLinePage, self).get_history_array_fields(),
                'history_integrated_plasmids': Plasmid,
                'history_episomal_plasmids': Plasmid,
                'history_formz_projects': FormZProject,
                'history_formz_gentech_methods': GenTechMethod,
                'history_formz_elements': FormZBaseElement,
                'history_document': CellLineDoc
                }