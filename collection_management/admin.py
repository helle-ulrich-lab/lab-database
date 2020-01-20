#################################################
#    DJANGO 'CORE' FUNCTIONALITIES IMPORTS      #
#################################################

from django.contrib import admin
from django.contrib import messages
from django.db.models import CharField
from django.urls import reverse, resolve
from django.core.mail import mail_admins
from django.core.exceptions import PermissionDenied
from django.utils.translation import ugettext as _, ugettext_lazy
from django import forms
from django.forms import TextInput
from django.http import HttpResponseRedirect
from django.http import HttpResponse
from django_project.settings import MEDIA_ROOT
from django_project.settings import BASE_DIR
from django_project.private_settings import LAB_ABBREVIATION_FOR_FILES
from django.contrib.auth.models import User
from django.utils.safestring import mark_safe
from django.contrib.admin.utils import quote
from django.utils.html import format_html
from django.contrib.admin.utils import unquote
from django.contrib.admin.templatetags.admin_urls import add_preserved_filters
from django.template.response import TemplateResponse
from django.shortcuts import get_object_or_404, render
from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.utils.encoding import force_text
from django.utils.text import capfirst
from django.utils import timezone

IS_POPUP_VAR = '_popup'
TO_FIELD_VAR = '_to_field'

#################################################
#        ADDED FUNCTIONALITIES IMPORTS          #
#################################################

# Advanced search functionalities from DjangoQL
from djangoql.admin import DjangoQLSearchMixin
from djangoql.schema import DjangoQLSchema
from djangoql.schema import StrField
from djangoql.schema import IntField

# Import/Export functionalities from django-import-export
from import_export import resources
from import_export.fields import Field

# Background tasks
from background_task import background

# Object history tracking from django-simple-history
from simple_history.admin import SimpleHistoryAdmin

# Django guardian
from guardian.admin import GuardedModelAdmin
from guardian.admin import UserManage

#################################################
#                OTHER IMPORTS                  #
#################################################

from urllib.parse import quote as urlquote

import json

from snapgene.pyclasses.client import Client
from snapgene.pyclasses.config import Config
import zmq
import os
import time

from formz.models import FormZBaseElement
from formz.models import FormZProject
from formz.models import Species

import xlrd
import csv

#################################################
#                CUSTOM CLASSES                 #
#################################################

class Approval():
    def approval(self, instance):

        """ Custom list_view field to show whether record has been approved or not """

        if instance.last_changed_approval_by_pi is not None:
            return instance.last_changed_approval_by_pi
        else:
            return instance.created_approval_by_pi
    approval.boolean = True
    approval.short_description = "Approved"

class SimpleHistoryWithSummaryAdmin(SimpleHistoryAdmin):

    object_history_template = "admin/object_history_with_change_summary.html"
    
    def history_view(self, request, object_id, extra_context=None):
        """The 'history' admin view for this model."""

        from django.http import Http404

        def pairwise(iterable):
            """ Create pairs of consecutive items from
            iterable"""

            import itertools
            a, b = itertools.tee(iterable)
            next(b, None)
            return zip(a, b)

        request.current_app = self.admin_site.name
        model = self.model
        opts = model._meta
        app_label = opts.app_label
        pk_name = opts.pk.attname
        history = getattr(model, model._meta.simple_history_manager_attribute)
        object_id = unquote(object_id)
        action_list = history.filter(**{pk_name: object_id})
        # If no history was found, see whether this object even exists.
        try:
            obj = self.get_queryset(request).get(**{pk_name: object_id})
        except model.DoesNotExist:
            try:
                obj = action_list.latest('history_date').instance
            except action_list.model.DoesNotExist:
                raise Http404

        # if not self.has_change_permission(request, obj): # Disable so that guests can access history summary view
        #     raise PermissionDenied

        # Create data structure for history summary
        history_summary_data = []
        try:
            # Get all history
            history_summary = obj.history.all()
            
            # If more than one history obj, create pairs of history objs
            if len(history_summary) > 1:
                history_pairs = pairwise(history_summary)
                for history_element in history_pairs:
                    
                    # Get differences between history obj pairs and add them to a list
                    delta = history_element[0].diff_against(history_element[1])
                    if delta:
                        if delta.changes:
                            changes_list = []
                            for change in delta.changes:
                                
                                # Do not show created/changed date/time or approval by PI fields, and png/gbk map fields
                                if not change.field.endswith(("time", "_pi", "map_png", "map_gbk", '_user')):
                                    
                                    field_name = model._meta.get_field(change.field).verbose_name
                                    field_type = model._meta.get_field(change.field).get_internal_type()
                                    
                                    if field_type == 'FileField':
                                        if change.field == 'map':
                                            field_name = field_name.replace(' (.dna)', '')
                                        changes_list.append(
                                            (capfirst(field_name), 
                                            os.path.basename(change.old).replace('.dna', '') if change.old else 'None', 
                                            os.path.basename(change.new).replace('.dna', '') if change.new else 'None'))
                                    else:
                                        changes_list.append(
                                            (capfirst(field_name), 
                                            change.old if change.old else 'None', 
                                            change.new if change.new else 'None'))
                            
                            if changes_list:
                                history_summary_data.append(
                                    (history_element[0].last_changed_date_time, 
                                    User.objects.get(id=int(history_element[0].history_user_id)), 
                                    changes_list))
        except:
            pass

        context = {
            'title': _('Change history: %s') % force_text(obj),
            'action_list': action_list,
            'module_name': capfirst(force_text(opts.verbose_name_plural)),
            'object': obj,
            'root_path': getattr(self.admin_site, 'root_path', None),
            'app_label': app_label,
            'opts': opts,
            'history_summary_data': history_summary_data,
        }
        context.update(self.admin_site.each_context(request))
        context.update(extra_context or {})
        extra_kwargs = {}
        
        return render(request, self.object_history_template, context,
                      **extra_kwargs)

class CustomUserManage(UserManage):
    
    """
    Add drop-down menu to select user to who to give additonal permissions
    """

    from django import forms

    try: # Added this try block because if user_auth table not present in DB (e.g. very first migration) the following code runs and throws an exception
        user = forms.ChoiceField(choices=[('------', '------')] + [(u.username, u) for u in User.objects.all().order_by('last_name') if u.groups.filter(name='Regular lab member').exists()],
                                label=_("Username"),
                            error_messages={'does_not_exist': _(
                                "This user does not exist")},)
        is_permanent = forms.BooleanField(required=False, label=_("Grant indefinitely?"))
    except:
        pass

@background(schedule=86400) # Run 24 h after it is called, as "background" process
def delete_obj_perm_after_24h(perm, user_id, obj_id, app_label, model_name):
    """ Delete object permession after 24 h"""
    
    from django.apps import apps
    from guardian.shortcuts import remove_perm
    
    user = User.objects.get(id=user_id)
    obj = apps.get_model(app_label, model_name).objects.get(id=obj_id)

    remove_perm(perm, user, obj)

class CustomGuardedModelAdmin(GuardedModelAdmin):

    def get_urls(self):
        """
        Extends standard guardian admin model urls with delete url
        """
        
        from django.conf.urls import url
        
        urls = super(CustomGuardedModelAdmin, self).get_urls()

        info = self.model._meta.app_label, self.model._meta.model_name
        myurls = [
            url(r'^(?P<object_pk>.+)/permissions/(?P<user_id>\-?\d+)/remove/$',
                view=self.admin_site.admin_view(
                    self.obj_perms_delete),name='%s_%s_permissions_delete' % info)
        ]
        urls = myurls + urls
        
        return urls

    def obj_perms_manage_view(self, request, object_pk):
        """
        Main object permissions view. Presents all users and groups with any
        object permissions for the current model *instance*. Users or groups
        without object permissions for related *instance* would **not** be
        shown. In order to add or manage user or group one should use links or
        forms presented within the page.
        """

        from guardian.shortcuts import assign_perm
        from guardian.shortcuts import get_user_model
        from guardian.shortcuts import get_users_with_perms
        from collections import OrderedDict
        from django.contrib.admin.utils import unquote
        from django.shortcuts import redirect

        if not self.has_change_permission(request, None):
            post_url = reverse('admin:index', current_app=self.admin_site.name)
            return redirect(post_url)

        obj = get_object_or_404(self.get_queryset(
            request), pk=unquote(object_pk))
        users_perms = OrderedDict(
            sorted(
                get_users_with_perms(obj, attach_perms=True,
                                     with_group_users=False).items(),
                key=lambda user: getattr(
                    user[0], get_user_model().USERNAME_FIELD)
            )
        )

        if request.method == 'POST' and 'submit_manage_user' in request.POST:
            perm = '{}.change_{}'.format(self.model._meta.app_label, self.model._meta.model_name)
            user = User.objects.get(username=request.POST['user'])
            assign_perm(perm, user, obj)
            user_form = self.get_obj_perms_user_select_form(request)(request.POST)
            group_form = self.get_obj_perms_group_select_form(request)(request.POST)
            info = (
                self.admin_site.name,
                self.model._meta.app_label,
                self.model._meta.model_name,
            )
            if user_form.is_valid():
                user_id = user_form.cleaned_data['user'].pk
                messages.success(request, 'Permissions saved.')
                if not request.POST.get('is_permanent', False): # If "Grant indefinitely" not selected remove permission after 24 h
                    delete_obj_perm_after_24h(perm, user.id, obj.id, obj._meta.app_label, obj._meta.model_name)
                return HttpResponseRedirect(".")
        else:
            user_form = self.get_obj_perms_user_select_form(request)()

        context = self.get_obj_perms_base_context(request, obj)
        context['users_perms'] = users_perms
        context['user_form'] = user_form

        # https://github.com/django/django/commit/cf1f36bb6eb34fafe6c224003ad585a647f6117b
        request.current_app = self.admin_site.name

        return render(request, self.get_obj_perms_manage_template(), context)

    def obj_perms_manage_user_view(self, request, object_pk, user_id):
        """
        Forbid usage of this view
        """

        raise PermissionDenied

    def get_obj_perms_user_select_form(self, request):
        """
        Returns form class for selecting a user for permissions management.  By
        default :form:`UserManage` is returned.
        """
        
        return CustomUserManage

    def obj_perms_delete(self, request, object_pk, user_id):
        """ Delete object permission for a user"""

        from guardian.shortcuts import get_user_model
        from guardian.shortcuts import remove_perm

        user = get_object_or_404(get_user_model(), pk=user_id)
        obj = get_object_or_404(self.get_queryset(request), pk=object_pk)
        
        remove_perm('{}.change_{}'.format(self.model._meta.app_label, self.model._meta.model_name),  user, obj)
        messages.success(request, 'Permission removed.')

        return HttpResponseRedirect("../..")

#################################################
#          CUSTOM USER SEARCH OPTIONS           #
#################################################

class SearchFieldOptUsername(StrField):
    """Create a list of unique users' usernames for search"""

    model = User
    name = 'username'
    suggest_options = True
    id_list = []

    def get_options(self):
        """exclude(id__in=[1,20,36]) removes admin, guest and anaonymous accounts from 
        the list of options, distinct() returns only unique values
        sorted in alphabetical order"""

        if self.id_list:
            return super(SearchFieldOptUsername, self).get_options().\
            filter(id__in=self.id_list).\
            order_by(self.name).\
            values_list(self.name, flat=True)
        else:
            return super(SearchFieldOptUsername, self).\
            get_options().\
            exclude(id__in=[1,20,36]).\
            distinct().order_by(self.name).\
            values_list(self.name, flat=True)

class SearchFieldOptLastname(StrField):
    """Create a list of unique user's last names for search"""

    model = User
    name = 'last_name'
    suggest_options = True
    id_list = []

    def get_options(self):
        """exclude(id__in=[1,20,36]) removes admin, guest and anaonymous accounts from 
        the list of options, distinct() returns only unique values
        sorted in alphabetical order"""
        
        if self.id_list:
            return super(SearchFieldOptLastname, self).get_options().\
            filter(id__in=self.id_list).\
            order_by(self.name).\
            values_list(self.name, flat=True)
        else:
            return super(SearchFieldOptLastname, self).\
            get_options().\
            exclude(id__in=[1,20,36]).\
            distinct().order_by(self.name).\
            values_list(self.name, flat=True)

class FieldUse(StrField):

    name = 'use'
    
    def get_lookup_name(self):
        return 'us_e'

class FieldLocation(StrField):

    name = 'location'

    def get_lookup_name(self):
        return 'l_ocation'

class FieldApplication(StrField):

    name = 'application'

    def get_lookup_name(self):
        return 'a_pplication'

#################################################
#          DOWNLOAD FORMBLATT Z ACTION          #
#################################################

def formz_as_html(modeladmin, request, queryset):

    """Export ForblattZ as html """

    from django.template.loader import get_template
    from bs4 import BeautifulSoup
    import zipfile
    from django.http import HttpResponse

    def get_params(app_label, model_name, obj_id):
        from formz.models import FormZStorageLocation
        from formz.models import FormZHeader
        from django.apps import apps
        from django.contrib.contenttypes.models import ContentType
        from formz.models import ZkbsCellLine

        model = apps.get_model(app_label, model_name)
        model_content_type = ContentType.objects.get(app_label=app_label, model=model_name)
        opts = model._meta
        obj = model.objects.get(id=int(obj_id))
        
        # Get storage location object or create a new 'empty' one
        if FormZStorageLocation.objects.get(collection_model=model_content_type):
            storage_location = FormZStorageLocation.objects.get(collection_model=model_content_type)
        else:
            storage_location = FormZStorageLocation(
                collection_model = None,
                storage_location = None,
                species_name = None,
                species_risk_group = None
            )

        if FormZHeader.objects.all().first():
            formz_header = FormZHeader.objects.all().first()
        else:
            formz_header = None

        obj.common_formz_elements = obj.get_all_common_formz_elements()
        obj.uncommon_formz_elements =  obj.get_all_uncommon_formz_elements()
        obj.instock_plasmids = obj.get_all_instock_plasmids()
        obj.transient_episomal_plasmids = obj.get_all_transient_episomal_plasmids()

        if model_name == 'cellline':
            storage_location.species_name = obj.organism
            obj.s2_plasmids = obj.celllineepisomalplasmid_set.all().filter(s2_work_episomal_plasmid=True).distinct().order_by('id')
            transfected = True
            try:
                virus_packaging_cell_line = ZkbsCellLine.objects.filter(name__iexact='293T (HEK 293T)').order_by('id')[0]
            except:
                virus_packaging_cell_line = ZkbsCellLine(name = '293T (HEK 293T)')
        else:
            obj.s2_plasmids = None
            transfected = False
            virus_packaging_cell_line = None

        params = {'object': obj,
                'storage_location': storage_location,
                'formz_header': formz_header,
                'transfected': transfected,
                'virus_packaging_cell_line': virus_packaging_cell_line,
                }

        return params

    response = HttpResponse(content_type='application/zip')
    response['Content-Disposition'] = 'attachment; filename="formblattz_{}_{}.zip'.format(time.strftime("%Y%m%d"), time.strftime("%H%M%S"))

    template = get_template('admin/formz_for_export.html')
    app_label = queryset[0]._meta.app_label
    model_name = queryset[0].__class__.__name__

    # Generates zip file

    with zipfile.ZipFile(response, "w", zipfile.ZIP_DEFLATED) as zip_file:
        for obj in queryset:
            params = get_params(app_label, model_name.lower(), obj.id)
            params['map_attachment_type'] = request.POST.get('map_attachment_type', default='none')
            html = template.render(params)
            html = BeautifulSoup(html, features="lxml")
            html = html.prettify("utf-8")
            zip_file.writestr('{}_{}.html'.format(model_name, obj.id), html)
        
    return response

formz_as_html.short_description = "Export Formblatt Z for selected items"

#################################################
#          SA. CEREVISIAE STRAIN PAGES          #
#################################################

from .models import SaCerevisiaeStrain
from .models import SaCerevisiaeStrainEpisomalPlasmid

class FieldIntegratedPlasmidM2M(IntField):
    
    name = 'integrated_plasmids_id'

    def get_lookup_name(self):
        return 'integrated_plasmids__id'

class FieldCassettePlasmidM2M(IntField):
    
    name = 'cassette_plasmids_id'

    def get_lookup_name(self):
        return 'cassette_plasmids__id'

class FieldEpisomalPlasmidM2M(IntField):
    
    name = 'episomal_plasmids_id'
    
    def get_lookup_name(self):
        return 'episomal_plasmids__id'

class FieldParent1(IntField):

    name = 'parent_1_id'
    
    def get_lookup_name(self):
        return 'parent_1__id'

class FieldParent2(IntField):

    name = 'parent_2_id'

    def get_lookup_name(self):
        return 'parent_2__id'

class SearchFieldOptUsernameSaCerStrain(SearchFieldOptUsername):

    id_list = SaCerevisiaeStrain.objects.all().values_list('created_by', flat=True).distinct()

class SearchFieldOptLastnameSaCerStrain(SearchFieldOptLastname):

    id_list = SaCerevisiaeStrain.objects.all().values_list('created_by', flat=True).distinct()

class FieldFormZProject(StrField):
    
    name = 'formz_projects_title'
    suggest_options = True

    def get_options(self):
        return FormZProject.objects.all().values_list('short_title', flat=True)

    def get_lookup_name(self):
        return 'formz_projects__short_title'

class FieldEpisomalPlasmidFormZProjectSaCerStrain(StrField):
    
    name = 'episomal_plasmids_formz_projects_title'
    suggest_options = True

    def get_options(self):
        return FormZProject.objects.all().values_list('short_title', flat=True)

    def get_lookup_name(self):
        return 'sacerevisiaestrainepisomalplasmid__formz_projects__short_title'

class SaCerevisiaeStrainQLSchema(DjangoQLSchema):
    '''Customize search functionality'''
    
    include = (SaCerevisiaeStrain, User) # Include only the relevant models to be searched

    def get_fields(self, model):
        ''' Define fields that can be searched'''
        
        if model == SaCerevisiaeStrain:
            return ['id', 'name', 'relevant_genotype', 'mating_type', 'chromosomal_genotype', FieldParent1(), FieldParent2(), 'parental_strain',
                'construction', 'modification', FieldIntegratedPlasmidM2M(), FieldCassettePlasmidM2M(), FieldEpisomalPlasmidM2M(), 'plasmids', 'selection', 
                'phenotype', 'background', 'received_from', FieldUse(), 'note', 'reference', 'created_by', FieldFormZProject(), FieldEpisomalPlasmidFormZProjectSaCerStrain()]
        elif model == User:
            return [SearchFieldOptUsernameSaCerStrain(), SearchFieldOptLastnameSaCerStrain()]
        return super(SaCerevisiaeStrainQLSchema, self).get_fields(model)

class SaCerevisiaeStrainExportResource(resources.ModelResource):
    """Defines a custom export resource class for SaCerevisiaeStrain"""
    
    episomal_plasmids_in_stock = Field()
    other_plasmids = Field(attribute='plasmids', column_name='other_plasmids_info')
    additional_parental_strain_info = Field(attribute='parental_strain', column_name='additional_parental_strain_info')

    def dehydrate_episomal_plasmids_in_stock(self, strain):
        return str(tuple(strain.episomal_plasmids.filter(sacerevisiaestrainepisomalplasmid__present_in_stocked_strain=True).values_list('id', flat=True))).replace(" ", "").replace(',)', ')')[1:-1]

    class Meta:
        model = SaCerevisiaeStrain
        fields = ('id', 'name', 'relevant_genotype', 'mating_type', 'chromosomal_genotype', 'parent_1', 'parent_2','additional_parental_strain_info',
        'construction', 'modification', 'integrated_plasmids', 'cassette_plasmids', 'episomal_plasmids_in_stock', 'other_plasmids', 
        'selection', 'phenotype', 'background', 'received_from','us_e', 'note', 'reference', 'created_date_time', 
        'created_by__username',)
        export_order = fields = ('id', 'name', 'relevant_genotype', 'mating_type', 'chromosomal_genotype', 'parent_1', 'parent_2','additional_parental_strain_info',
        'construction', 'modification', 'integrated_plasmids', 'cassette_plasmids', 'episomal_plasmids_in_stock', 'other_plasmids', 
        'selection', 'phenotype', 'background', 'received_from','us_e', 'note', 'reference', 'created_date_time', 
        'created_by__username',)

def export_sacerevisiaestrain(modeladmin, request, queryset):
    """Export SaCerevisiaeStrain"""

    export_data = SaCerevisiaeStrainExportResource().export(queryset)

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
export_sacerevisiaestrain.short_description = "Export selected strains"

class SaCerevisiaeStrainForm(forms.ModelForm):
    
    # change_reason = forms.CharField(required=False)

    class Meta:
        model = SaCerevisiaeStrain
        fields = '__all__'

    def clean_name(self):
        """Check if name is unique before saving"""
        
        if not self.instance.pk:
            qs = SaCerevisiaeStrain.objects.filter(name=self.cleaned_data["name"])
            if qs.exists():
                raise forms.ValidationError('Strain with this name already exists.')
            else:
                return self.cleaned_data["name"]
        else:
            return self.cleaned_data["name"]

class SaCerevisiaeStrainEpisomalPlasmidInline(admin.TabularInline):
    
    autocomplete_fields = ['plasmid', 'formz_projects']
    model = SaCerevisiaeStrainEpisomalPlasmid
    verbose_name_plural = "Episomal plasmids"
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
            if parent_obj_episomal_plasmids.filter(sacerevisiaestrainepisomalplasmid__present_in_stocked_strain=True):
                self.classes = []
        else:
            self.classes = []
        return super(SaCerevisiaeStrainEpisomalPlasmidInline, self).get_queryset(request)

class SaCerevisiaeStrainPage(DjangoQLSearchMixin, SimpleHistoryWithSummaryAdmin, CustomGuardedModelAdmin, Approval):
    
    list_display = ('id', 'name', 'mating_type', 'background', 'created_by', 'approval')
    list_display_links = ('id', )
    list_per_page = 25
    djangoql_schema = SaCerevisiaeStrainQLSchema
    actions = [export_sacerevisiaestrain, formz_as_html]
    form = SaCerevisiaeStrainForm
    formfield_overrides = {CharField: {'widget': TextInput(attrs={'size':'93'})},} # Make TextInput fields wider
    search_fields = ['id', 'name']
    autocomplete_fields = ['parent_1', 'parent_2', 'integrated_plasmids', 'cassette_plasmids', 
                           'formz_projects', 'formz_gentech_methods', 'formz_elements']
    inlines = [SaCerevisiaeStrainEpisomalPlasmidInline]
    
    def save_model(self, request, obj, form, change):
        '''Override default save_model to limit a user's ability to save a record
        Superusers and lab managers can change all records
        Regular users can change only their own records
        Guests cannot change any record'''

        if obj.pk == None:
            
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
                SaCerevisiaeStrain.objects.filter(id=obj.pk).update(last_changed_date_time=original_last_changed_date_time)
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
                    SaCerevisiaeStrain.objects.filter(id=obj.pk).update(last_changed_date_time=original_last_changed_date_time)
                return
            
            # Check if the request's user can change the object, if not raise PermissionDenied
            if self.can_change:
                
                # Approve right away if the request's user is the principal investigator. If not,
                # create an approval record
                if request.user.labuser.is_principal_investigator and request.user.id in obj.formz_projects.all().values_list('project_leader__id', flat=True):
                    obj.last_changed_approval_by_pi = True
                    obj.approval_user = request.user
                    obj.approval_by_pi_date_time = timezone.now()
                    if obj.approval.all().exists():
                        approval_records = obj.approval.all()
                        approval_records.delete()
                else:
                    obj.last_changed_approval_by_pi = False
                    obj.approval_user = None

                    # If an approval record for this object does not exist, create one
                    if not obj.approval.all().exists():
                        obj.approval.create(activity_type='changed', activity_user=request.user)
                    else:
                        # If an approval record for this object exists, check if a message was 
                        # sent. If so, update the approval record's edited field
                        approval_obj = obj.approval.all().latest(field_name='message_date_time')
                        if approval_obj.message_date_time:
                            if obj.last_changed_date_time > approval_obj.message_date_time:
                                approval_obj.edited = True
                                approval_obj.save()

                obj.save()

            else:
                raise PermissionDenied
    
    def save_related(self, request, form, formsets, change):
        
        super(SaCerevisiaeStrainPage, self).save_related(request, form, formsets, change)

        # Keep a record of the IDs of linked M2M fields in the main strain record
        # Not pretty, but it works

        obj = SaCerevisiaeStrain.objects.get(pk=form.instance.id)
        
        integrated_plasmids = obj.integrated_plasmids.all().order_by('id')
        cassette_plasmids = obj.cassette_plasmids.all().order_by('id')
        episomal_plasmids = obj.episomal_plasmids.all().order_by('id')

        obj.history_integrated_plasmids = str(tuple(integrated_plasmids.values_list('id', flat=True))).replace(',)', ')') if integrated_plasmids else ""
        obj.history_cassette_plasmids = str(tuple(cassette_plasmids.values_list('id', flat=True))).replace(',)', ')') if cassette_plasmids else ""
        obj.history_episomal_plasmids = str(tuple(episomal_plasmids.values_list('id', flat=True))).replace(',)', ')') if episomal_plasmids else ""

        plasmid_id_list = integrated_plasmids | cassette_plasmids | episomal_plasmids.filter(sacerevisiaestrainepisomalplasmid__present_in_stocked_strain=True) # Merge querysets
        if plasmid_id_list:
            plasmid_id_list = tuple(plasmid_id_list.distinct().order_by('id').values_list('id', flat=True))
            obj.history_all_plasmids_in_stocked_strain = str(plasmid_id_list).replace(',)', ')')

        obj.history_formz_projects = str(tuple(obj.formz_projects.all().order_by('short_title_english').values_list('short_title_english', flat=True))).replace(',)', ')') if obj.formz_projects.all() else ""
        obj.history_formz_gentech_methods = str(tuple(obj.formz_gentech_methods.all().order_by('english_name').values_list('english_name', flat=True))).replace(',)', ')') if obj.formz_gentech_methods.all() else ""
        obj.history_formz_elements = str(tuple(obj.formz_elements.all().order_by('name').values_list('name', flat=True))).replace(',)', ')') if obj.formz_elements.all() else ""

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

        for in_stock_episomal_plasmid in SaCerevisiaeStrainEpisomalPlasmid.objects.filter(sacerevisiae_strain__id=form.instance.id).filter(present_in_stocked_strain=True):
            in_stock_episomal_plasmid.formz_projects.clear()

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
                if request.user.has_perm('collection_management.change_sacerevisiaestrain', obj):
                    return ['created_date_time', 'created_approval_by_pi', 'last_changed_date_time', 'last_changed_approval_by_pi', 'created_by',]
                if obj.created_by.groups.filter(name='Past member') or obj.created_by.labuser.is_principal_investigator:
                    return ['name', 'relevant_genotype', 'mating_type', 'chromosomal_genotype', 'parent_1', 'parent_2', 'parental_strain',
                'construction', 'modification', 'integrated_plasmids', 'cassette_plasmids', 'plasmids', 'selection', 'phenotype', 
                'background', 'received_from', 'us_e', 'reference', 'created_date_time', 'created_approval_by_pi', 'last_changed_date_time',
                'last_changed_approval_by_pi', 'created_by', 'formz_projects', 'formz_risk_group', 'formz_gentech_methods', 'formz_elements', 
                'destroyed_date']
                else:
                    return ['name', 'relevant_genotype', 'mating_type', 'chromosomal_genotype', 'parent_1', 'parent_2', 'parental_strain',
                    'construction', 'modification', 'integrated_plasmids', 'cassette_plasmids', 'plasmids', 'selection', 'phenotype', 
                    'background', 'received_from', 'us_e', 'note', 'reference', 'created_date_time', 'created_approval_by_pi', 
                    'last_changed_date_time', 'last_changed_approval_by_pi', 'created_by', 'formz_projects', 'formz_risk_group', 
                    'formz_gentech_methods', 'formz_elements', 'destroyed_date']
        else:
            return ['created_date_time', 'created_approval_by_pi', 'last_changed_date_time', 'last_changed_approval_by_pi',]

    def add_view(self,request,extra_context=None):
        '''Override default add_view to show desired fields'''

        self.fieldsets = (
        (None, {
            'fields': ('name', 'relevant_genotype', 'mating_type', 'chromosomal_genotype', 'parent_1', 'parent_2', 
        'parental_strain', 'construction', 'modification','integrated_plasmids', 'cassette_plasmids', 'plasmids', 
        'selection', 'phenotype', 'background', 'received_from', 'us_e', 'note', 'reference',)
        }),
        ('FormZ', {
            'fields': ('formz_projects', 'formz_risk_group', 'formz_gentech_methods', 'formz_elements', 'destroyed_date')
        }),
        )

        return super(SaCerevisiaeStrainPage,self).add_view(request)

    def change_view(self,request,object_id,extra_context=None):
        '''Override default change_view to show desired fields'''

        self.can_change = False

        extra_context = extra_context or {}

        if object_id:

            obj = SaCerevisiaeStrain.objects.get(pk=object_id)
            
            if obj.history_all_plasmids_in_stocked_strain:
                extra_context['plasmid_id_list'] = obj.history_all_plasmids_in_stocked_strain
        
            if request.user == obj.created_by or request.user.groups.filter(name='Lab manager').exists() or \
                request.user.labuser.is_principal_investigator or obj.created_by.labuser.is_principal_investigator or \
                obj.created_by.groups.filter(name='Past member') or request.user.is_superuser or \
                request.user.has_perm('collection_management.change_sacerevisiaestrain', obj):
                
                self.can_change = True

                if (obj.created_by.labuser.is_principal_investigator or obj.created_by.groups.filter(name='Past member')) and \
                        not request.user.has_perm('collection_management.change_plasmid', obj):
                    
                    extra_context = {'show_close': True,
                                    'show_save_and_add_another': False,
                                    'show_save_and_continue': True,
                                    'show_save_as_new': False,
                                    'show_save': True,
                                    'show_obj_permission': False,}

                else:
                    
                    extra_context = {'show_close': True,
                                    'show_save_and_add_another': True,
                                    'show_save_and_continue': True,
                                    'show_save_as_new': True,
                                    'show_save': True,
                                    'show_obj_permission': True,
                                    }
            
            else:

                extra_context = {'show_close': True,
                    'show_save_and_add_another': False,
                    'show_save_and_continue': False,
                    'show_save_as_new': False,
                    'show_save': False,
                    'show_obj_permission': False}

            extra_context['show_disapprove'] = True if request.user.groups.filter(name='Approval manager').exists() else False
            extra_context['show_formz'] = True

        if '_saveasnew' in request.POST:
            
            self.fieldsets = (
            (None, {
                'fields': ('name', 'relevant_genotype', 'mating_type', 'chromosomal_genotype', 'parent_1', 'parent_2', 
            'parental_strain', 'construction', 'modification','integrated_plasmids', 'cassette_plasmids', 'plasmids', 
            'selection', 'phenotype', 'background', 'received_from', 'us_e', 'note', 'reference',)
            }),
            ('FormZ', {
                'fields': ('formz_projects', 'formz_risk_group', 'formz_gentech_methods', 'formz_elements', 'destroyed_date')
            }),
            )

        else:

            if request.user == obj.created_by or not obj.created_by.groups.filter(name='Past member').exists():
                self.fieldsets = (
                (None, {
                    'fields': ('name', 'relevant_genotype', 'mating_type', 'chromosomal_genotype', 'parent_1', 'parent_2', 
                    'parental_strain', 'construction', 'modification', 'integrated_plasmids', 'cassette_plasmids', 'plasmids', 
                    'selection', 'phenotype', 'background', 'received_from','us_e', 'note', 'reference', 'created_date_time', 
                    'created_approval_by_pi', 'last_changed_date_time', 'last_changed_approval_by_pi', 'created_by',)
                }),
                ('FormZ', {
                    'classes': ('collapse',),
                    'fields': ('formz_projects', 'formz_risk_group', 'formz_gentech_methods', 'formz_elements','destroyed_date')
                }),
                )
            else:
                self.fieldsets = (
                (None, {
                    'fields': ('name', 'relevant_genotype', 'mating_type', 'chromosomal_genotype', 'parent_1', 'parent_2', 
                    'parental_strain', 'construction', 'modification', 'integrated_plasmids', 'cassette_plasmids', 'plasmids', 
                    'selection', 'phenotype', 'background', 'received_from','us_e', 'note', 'reference', 'created_date_time', 
                    'created_approval_by_pi', 'last_changed_date_time', 'last_changed_approval_by_pi', 'created_by')
                }),
                ('FormZ', {
                    'classes': ('collapse',),
                    'fields': ('formz_projects', 'formz_risk_group', 'formz_gentech_methods', 'formz_elements', 'destroyed_date')
                }),
                )

        return super(SaCerevisiaeStrainPage,self).change_view(request,object_id,extra_context=extra_context)
   
    def obj_perms_manage_view(self, request, object_pk):
        """
        Main object Guardian permissions view. 

        Customized to allow only record owner to change permissions
        """
        obj = SaCerevisiaeStrain.objects.get(pk=object_pk)
        
        if obj:
            if not (request.user.is_superuser or request.user.groups.filter(name='Lab manager').exists() or \
                request.user == obj.created_by or request.user.labuser.is_principal_investigator):
                messages.error(request, 'Nice try, you are allowed to change the permissions of your own records only.')
                return HttpResponseRedirect("..")
        return super(SaCerevisiaeStrainPage,self).obj_perms_manage_view(request, object_pk)

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
            return HttpResponseRedirect(reverse("admin:record_approval_recordtobeapproved_change", args=(obj.approval.latest('created_date_time').id,)))
        
        return super(SaCerevisiaeStrainPage,self).response_change(request,obj)

#################################################
#                 PLASMID PAGES                 #
#################################################

from .models import Plasmid

class SearchFieldOptUsernamePlasmid(SearchFieldOptUsername):

    id_list = Plasmid.objects.all().values_list('created_by', flat=True).distinct()

class SearchFieldOptLastnamePlasmid(SearchFieldOptLastname):

    id_list = Plasmid.objects.all().values_list('created_by', flat=True).distinct()

class FieldFormZBaseElement(StrField):
    
    name = 'formz_elements_name'
    model = Plasmid
    suggest_options = True

    def get_options(self):
        return FormZBaseElement.objects.all().values_list('name', flat=True)

    def get_lookup_name(self):
        return 'formz_elements__name'

class PlasmidQLSchema(DjangoQLSchema):
    '''Customize search functionality'''
    
    include = (Plasmid, User) # Include only the relevant models to be searched

    def get_fields(self, model):
        '''Define fields that can be searched'''
        
        if model == Plasmid:
            return ['id', 'name', 'other_name', 'parent_vector', 'selection', FieldUse(), 'construction_feature', 'received_from', 'note', 
                'reference', 'created_by', FieldFormZBaseElement(), FieldFormZProject()]
        elif model == User:
            return [SearchFieldOptUsernamePlasmid(), SearchFieldOptLastnamePlasmid()]
        return super(PlasmidQLSchema, self).get_fields(model)

class PlasmidExportResource(resources.ModelResource):
    """Defines a custom export resource class for Plasmid"""
    
    additional_parent_vector_info = Field(attribute='old_parent_vector', column_name='additional_parent_vector_info')

    class Meta:
        model = Plasmid
        fields = ('id', 'name', 'other_name', 'parent_vector', 'additional_parent_vector_info', 'selection', 'us_e', 
                  'construction_feature', 'received_from', 'note', 'reference', 'map', 'created_date_time',
                  'created_by__username',)
        export_order = ('id', 'name', 'other_name', 'parent_vector', 'additional_parent_vector_info', 'selection', 'us_e', 
                  'construction_feature', 'received_from', 'note', 'reference', 'map', 'created_date_time',
                  'created_by__username',)

def export_plasmid(modeladmin, request, queryset):
    """Export Plasmid"""

    export_data = PlasmidExportResource().export(queryset)

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
export_plasmid.short_description = "Export selected plasmids"

class PlasmidForm(forms.ModelForm):
    
    class Meta:
        model = Plasmid
        fields = '__all__'

    def clean_name(self):
        """Check if name is unique before saving"""
        
        if not self.instance.pk:
            if Plasmid.objects.filter(name=self.cleaned_data["name"]).exists():
                raise forms.ValidationError('Plasmid with this name already exists.')
            else:
                return self.cleaned_data["name"]
        else:
            return self.cleaned_data["name"]

    def clean(self):

        """Check if both the .dna and .gbk map is changed at the same time, which 
        is not allowed"""

        map_dna = self.cleaned_data.get('map', None)
        map_gbk = self.cleaned_data.get('map_gbk', None)

        if not self.instance.pk:
            if map_dna and map_gbk:
                self.add_error(None, "You cannot add both a .dna and a .gbk map at the same time. Please choose only one")

        else:
            saved_obj = Plasmid.objects.get(id=self.instance.pk)
            saved_dna_map = saved_obj.map.name if saved_obj.map.name else None
            saved_gbk_map = saved_obj.map_gbk.name if saved_obj.map_gbk.name else None

            if  map_dna != saved_dna_map and map_gbk != saved_gbk_map:
                self.add_error(None, "You cannot change both a .dna and a .gbk map at the same time. Please choose only one")

        return self.cleaned_data

class PlasmidPage(DjangoQLSearchMixin, SimpleHistoryWithSummaryAdmin, CustomGuardedModelAdmin, Approval):
    
    list_display = ('id', 'name', 'selection', 'get_plasmidmap_short_name', 'created_by', 'approval')
    list_display_links = ('id', )
    list_per_page = 25
    formfield_overrides = {CharField: {'widget': TextInput(attrs={'size':'93'})},} # Make TextInput fields wider
    djangoql_schema = PlasmidQLSchema
    actions = [export_plasmid, formz_as_html]
    search_fields = ['id', 'name']
    autocomplete_fields = ['parent_vector', 'formz_projects', 'formz_elements', 'vector_zkbs', 'formz_ecoli_strains', 'formz_gentech_methods']
    redirect_to_obj_page = False
    form = PlasmidForm

    change_form_template = "admin/collection_management/plasmid/change_form.html"
    add_form_template = "admin/collection_management/plasmid/change_form.html"

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
            
            obj.created_by = request.user
            obj.save()
            new_obj = True
            self.new_obj = True
            
            # Check if a map is present and if so trigger functions to create a plasmid
            # map preview and delete the resulting duplicate history record
            if obj.map:
                rename_and_preview = True
                self.rename_and_preview = True
            elif obj.map_gbk:
                rename_and_preview = True
                self.rename_and_preview = True
                convert_map_to_dna = True

            # If the request's user is the principal investigator, approve the record
            # right away. If not, create an approval record
            if request.user.labuser.is_principal_investigator and request.user.id in obj.formz_projects.all().values_list('project_leader__id', flat=True):
                original_last_changed_date_time = obj.last_changed_date_time
                obj.created_approval_by_pi = True
                obj.approval_user = request.user
                obj.approval_by_pi_date_time = timezone.now()
                obj.save_without_historical_record()
                Plasmid.objects.filter(id=obj.pk).update(last_changed_date_time=original_last_changed_date_time)
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
                    Plasmid.objects.filter(id=obj.pk).update(last_changed_date_time=original_last_changed_date_time)
                return

            # Approve right away if the request's user is the principal investigator. If not,
            # create an approval record
            if request.user.labuser.is_principal_investigator and request.user.id in obj.formz_projects.all().values_list('project_leader__id', flat=True):
                obj.last_changed_approval_by_pi = True
                obj.approval_user = request.user
                obj.approval_by_pi_date_time = timezone.now()
                if obj.approval.all().exists():
                    approval_records = obj.approval.all()
                    approval_records.delete()
 
            else:
                obj.last_changed_approval_by_pi = False
                obj.approval_user = None

                # If an approval record for this object does not exist, create one
                if not obj.approval.all().exists():
                    obj.approval.create(activity_type='changed', activity_user=request.user)
                else:
                    # If an approval record for this object exists, check if a message was 
                    # sent. If so, update the approval record's edited field
                    approval_obj = obj.approval.all().latest(field_name='message_date_time')
                    if approval_obj.message_date_time:
                        if obj.last_changed_date_time > approval_obj.message_date_time:
                            approval_obj.edited = True
                            approval_obj.save()

            # Check if the request's user can change the object, if not raise PermissionDenied

            saved_obj = Plasmid.objects.get(pk=obj.pk)

            if self.can_change:

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

            else:
                
                if obj.created_by.labuser.is_principal_investigator: # Allow saving object, if record belongs to principal investigator
                    
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

                else:
                    raise PermissionDenied
        
        # Rename plasmid map
        if rename_and_preview:

            new_file_name = "p{}{}_{}_{}".format(LAB_ABBREVIATION_FOR_FILES, obj.id, time.strftime("%Y%m%d"), time.strftime("%H%M%S"))
            
            new_dna_file_name = os.path.join('collection_management/plasmid/dna/', new_file_name + '.dna')
            new_gbk_file_name = os.path.join('collection_management/plasmid/gbk/', new_file_name + '.gbk')
            new_png_file_name = os.path.join('collection_management/plasmid/png/', new_file_name + '.png')
            
            new_dna_file_path = os.path.join(MEDIA_ROOT, new_dna_file_name)
            new_gbk_file_path = os.path.join(MEDIA_ROOT, new_gbk_file_name)

            if convert_map_to_dna:
                old_gbk_file_path = obj.map_gbk.path
                os.rename(
                    old_gbk_file_path, 
                    new_gbk_file_path)
                try:
                    self.convert_plasmid_map_gbk_to_dna(new_gbk_file_path, new_dna_file_path)
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
                detect_common_features = request.POST.get("detect_common_features_map_dna", True) and request.POST.get("detect_common_features_map_gbk", True)
                self.create_plasmid_map_preview(obj.map.path, obj.map_png.path, obj.map_gbk.path, obj.id, obj.name, detect_common_features)
            except:
                messages.error(request, 'There was an error with detection of common features and/or saving of the map preview')


    def save_related(self, request, form, formsets, change):
        
        super(PlasmidPage, self).save_related(request, form, formsets, change)

        obj = Plasmid.objects.get(pk=form.instance.id)

        # If a plasmid map is provided, automatically add those
        # for which a corresponding FormZ base element is present
        # in the database

        if self.clear_formz_elements:
            obj.formz_elements.clear()

        if self.rename_and_preview or "_redetect_formz_elements" in request.POST:
            
            unknown_feat_name_list = []
            
            try:
                r = self.get_plasmid_map_features(obj.map.path)
            except:
                messages.error(request, 'There was an error getting your plasmid map features')
                r = {}
            
            if not self.new_obj:
                obj.formz_elements.clear()
            
            feature_names = [feat['name'].strip() for feat in r.get('features', [])]
            
            if feature_names:
            
                formz_base_elems = FormZBaseElement.objects.filter(extra_label__label__in = feature_names).distinct()
                aliases = list(formz_base_elems.values_list('extra_label__label', flat=True))
                obj.formz_elements.add(*list(formz_base_elems))

                unknown_feat_name_list = [feat for feat in feature_names if feat not in aliases]

                if unknown_feat_name_list:
                    self.redirect_to_obj_page = True
                    unknown_feat_name_list = str(unknown_feat_name_list)[1:-1].replace("'", "")
                    messages.warning(request, mark_safe("The following plasmid features were not added to <span style='background-color:rgba(0,0,0,0.1);'>FormZ Elements</span>,"
                                        " because they cannot be found in the database: <span class='missing-formz-features' style='background-color:rgba(255,0,0,0.2)'>{}</span>. You may want to add them manually "
                                        "yourself below.".format(unknown_feat_name_list)))
            else:
                self.redirect_to_obj_page = False

        # Keep a record of the IDs of linked M2M fields in the main strain record
        # Not pretty, but it works

        obj.history_formz_projects = str(tuple(obj.formz_projects.all().order_by('short_title_english').values_list('short_title_english', flat=True))).replace(',)', ')') if obj.formz_projects.all() else ""
        obj.history_formz_elements = str(tuple(obj.formz_elements.all().order_by('name').values_list('name', flat=True))).replace(',)', ')') if obj.formz_elements.all() else ""
        obj.history_formz_ecoli_strains = str(tuple(obj.formz_ecoli_strains.all().order_by('id').values_list('id', flat=True))).replace(',)', ')') if obj.formz_ecoli_strains.all() else ""
        obj.history_formz_gentech_methods = str(tuple(obj.formz_gentech_methods.all().order_by('english_name').values_list('english_name', flat=True))).replace(',)', ')') if obj.formz_gentech_methods.all() else ""

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
        history_obj.history_formz_projects = obj.history_formz_projects
        history_obj.history_formz_elements = obj.history_formz_elements
        history_obj.history_formz_ecoli_strains = obj.history_formz_ecoli_strains
        history_obj.history_formz_gentech_methods = obj.history_formz_gentech_methods
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
            return HttpResponseRedirect(reverse("admin:record_approval_recordtobeapproved_change", args=(obj.approval.latest('created_date_time').id,)))

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

    def get_readonly_fields(self, request, obj=None):
        '''Override default get_readonly_fields to define user-specific read-only fields
        If a user is not a superuser, lab manager or the user who created a record
        return all fields as read-only
        'created_date_time' and 'last_changed_date_time' fields must always be read-only
        because their set by Django itself'''
        
        if obj:
            if request.user.has_perm('collection_management.change_plasmid', obj):
                return ['map_png', 'created_date_time', 'created_approval_by_pi', 'last_changed_date_time', 'last_changed_approval_by_pi', 'created_by',]
            if not (request.user.is_superuser or request.user.groups.filter(name='Lab manager').exists() or request.user == obj.created_by or obj.created_by.labuser.is_principal_investigator or obj.created_by.groups.filter(name='Past member').exists()):
                return ['name', 'other_name', 'parent_vector', 'old_parent_vector', 'selection', 'us_e', 'construction_feature', 'received_from', 'note', 
                    'reference', 'map', 'map_png', 'map_gbk', 'created_date_time', 'created_approval_by_pi', 'last_changed_date_time',
                    'last_changed_approval_by_pi', 'created_by', 'formz_projects', 'formz_risk_group', 'vector_zkbs', 
                    'destroyed_date', 'formz_elements', 'formz_gentech_methods', 'formz_ecoli_strains']
            else:
                if (obj.created_by.labuser.is_principal_investigator or obj.created_by.groups.filter(name='Past member').exists()) and not (request.user.is_superuser or request.user.groups.filter(name='Lab manager').exists()): # Show map and note as editable fields, if record belongs to PI or old member
                    return ['name', 'other_name', 'parent_vector', 'old_parent_vector', 'selection', 'us_e', 'construction_feature', 'received_from', 
                    'reference', 'map_png', 'created_date_time', 'created_approval_by_pi', 'last_changed_date_time',
                    'last_changed_approval_by_pi', 'created_by', 'formz_projects', 'formz_risk_group', 'vector_zkbs', 
                    'destroyed_date', 'formz_elements', 'formz_gentech_methods', 'formz_ecoli_strains']
                else:
                    return ['map_png', 'created_date_time', 'created_approval_by_pi', 'last_changed_date_time', 'last_changed_approval_by_pi','created_by',]
        else:
            return ['created_date_time', 'created_approval_by_pi', 'last_changed_date_time', 'last_changed_approval_by_pi',]
    
    def add_view(self, request, extra_context=None):
        '''Override default add_view to show only desired fields'''

        self.fieldsets = (
        (None, {
            'fields': ('name', 'other_name', 'parent_vector', 'selection', 'us_e', 'construction_feature', 'received_from', 'note', 
                'reference', 'map', 'map_gbk')
        }),
        ('FormZ', {
            'fields': ('formz_projects', 'formz_risk_group', 'vector_zkbs', 'formz_gentech_methods', 'formz_elements', 'formz_ecoli_strains', 'destroyed_date',)
        }),
        )
        
        return super(PlasmidPage,self).add_view(request)
    
    def change_view(self, request, object_id, extra_context=None):
        '''Override default change_view to show only desired fields'''

        self.can_change = False

        extra_context = extra_context or {}

        if object_id:
            
            obj = Plasmid.objects.get(pk=object_id)
            
            if request.user == obj.created_by or request.user.groups.filter(name='Lab manager').exists() or \
                request.user.labuser.is_principal_investigator or request.user.is_superuser or \
                obj.created_by.labuser.is_principal_investigator or obj.created_by.groups.filter(name='Past member') or \
                request.user.has_perm('collection_management.change_plasmid', obj):
                    
                    self.can_change = True
                    
                    if (obj.created_by.labuser.is_principal_investigator or obj.created_by.groups.filter(name='Past member')) and \
                        not request.user.has_perm('collection_management.change_plasmid', obj):
                        
                        extra_context = {'show_close': True,
                                        'show_save_and_add_another': False,
                                        'show_save_and_continue': True,
                                        'show_save_as_new': False,
                                        'show_save': True,
                                        'show_obj_permission': False,
                                        'show_redetect_save': True}
                    else:

                        extra_context = {'show_close': True,
                                    'show_save_and_add_another': True,
                                    'show_save_and_continue': True,
                                    'show_save_as_new': True,
                                    'show_save': True,
                                    'show_obj_permission': True,
                                    'show_redetect_save': True
                                    }

            else:
                
                extra_context = {'show_close': True,
                                 'show_save_and_add_another': False,
                                 'show_save_and_continue': False,
                                 'show_save_as_new': False,
                                 'show_save': False,
                                 'show_obj_permission': False,
                                 'show_redetect_save': False}
            
            extra_context['show_disapprove'] = True if request.user.groups.filter(name='Approval manager').exists() else False
            extra_context['show_formz'] = True

        fieldsets_with_keep = (
                (None, {
                    'fields': ('name', 'other_name', 'parent_vector', 'selection', 'us_e', 'construction_feature', 'received_from', 'note', 
                        'reference', 'map', 'map_png', 'map_gbk', 'created_date_time', 'created_approval_by_pi', 'last_changed_date_time',
                        'last_changed_approval_by_pi', 'created_by', )
                }),
                ('FormZ', {
                    'classes': ('collapse',),
                    'fields': ('formz_projects', 'formz_risk_group', 'vector_zkbs', 'formz_gentech_methods', 'formz_elements', 'formz_ecoli_strains', 'destroyed_date',)
                }),
                )

        fieldsets_wo_keep = (
                (None, {
                    'fields': ('name', 'other_name', 'parent_vector', 'selection', 'us_e', 'construction_feature', 'received_from', 'note', 
                        'reference', 'map', 'map_png', 'map_gbk', 'created_date_time', 'created_approval_by_pi', 'last_changed_date_time',
                        'last_changed_approval_by_pi', 'created_by', )
                }),
                ('FormZ', {
                    'classes': ('collapse',),
                    'fields': ('formz_projects', 'formz_risk_group', 'vector_zkbs', 'formz_gentech_methods', 'formz_elements', 'formz_ecoli_strains', 'destroyed_date',)
                }),
                )

        if '_saveasnew' in request.POST:
            self.fieldsets = (
                (None, {
                    'fields': ('name', 'other_name', 'parent_vector', 'selection', 'us_e', 'construction_feature', 'received_from', 'note', 
                'reference', 'map',)
                }),
                ('FormZ', {
                    'fields': ('formz_projects', 'formz_risk_group', 'vector_zkbs', 'formz_gentech_methods', 'formz_elements', 'formz_ecoli_strains', 'destroyed_date',)
                    }),
                )
        else:
            if request.user.has_perm('collection_management.change_plasmid', obj):
                self.fieldsets = fieldsets_with_keep
            if not (request.user.is_superuser or request.user.groups.filter(name='Lab manager').exists() or request.user == obj.created_by or obj.created_by.labuser.is_principal_investigator):
                self.fieldsets = fieldsets_wo_keep
            else:
                if obj.created_by.labuser.is_principal_investigator and not (request.user.is_superuser or request.user.groups.filter(name='Lab manager').exists()):
                    self.fieldsets = fieldsets_with_keep
                else:
                    self.fieldsets = fieldsets_wo_keep
        
        return super(PlasmidPage, self).change_view(request, object_id, extra_context=extra_context)

    def get_plasmidmap_short_name(self, instance):
        '''This function allows you to define a custom field for the list view to
        be defined in list_display as the name of the function, e.g. in this case
        list_display = ('id', 'name', 'selection', 'get_plasmidmap_short_name','created_by',)'''
        
        if instance.map:
            return mark_safe('<a class="image-link" href="{}">png</a> | <a href="{}">dna</a> | <a href="{}">gbk</a>'.format(str(instance.map_png.url),str(instance.map.url), str(instance.map_gbk.url)))
        else:
            return ''
    get_plasmidmap_short_name.short_description = 'Plasmid map'

    class Media:
        css = {
            "all": ('admin/css/vendor/magnific-popup.css',
            )}

    def obj_perms_manage_view(self, request, object_pk):
        """
        Main object Guardian permissions view. 

        Customized to allow only record owner to change permissions
        """
        obj = Plasmid.objects.get(pk=object_pk)
        
        if obj:
            if not (request.user.is_superuser or request.user.groups.filter(name='Lab manager').exists() or \
                request.user == obj.created_by or request.user.labuser.is_principal_investigator):
                messages.error(request, 'Nice try, you are allowed to change the permissions of your own records only.')
                return HttpResponseRedirect("..")
        return super(PlasmidPage,self).obj_perms_manage_view(request, object_pk)

    #@background(schedule=1) # Run 1 s after it is called, as "background" process
    def create_plasmid_map_preview(self, plasmid_map_path, png_plasmid_map_path, gbk_plasmid_map_path, obj_id, obj_name, detect_common_features, attempt_number=3, messages=[]):
        """ Given a path to a snapgene plasmid map, use snapegene server
        to detect common features and create map preview as png
        and gbk"""

        if attempt_number > 0:
            try:
                config = Config()
                server_ports = config.get_server_ports()
                for port in server_ports.values():
                    try:
                        client = Client(port, zmq.Context())
                    except:
                        continue
                    else:
                        break
                
                common_features_path = os.path.join(BASE_DIR, "snapgene/standardCommonFeatures.ftrs")
                
                if detect_common_features:
                    argument = {"request":"detectFeatures", "inputFile": plasmid_map_path, 
                    "outputFile": plasmid_map_path, "featureDatabase": common_features_path}
                    r = client.requestResponse(argument, 10000)
                    r_code = r.get('code', 1)
                    if r_code > 0:
                        error_message = 'detectFeatures - error ' + r_code
                        if error_message not in messages: messages.append(error_message)
                        client.close()
                        raise Exception
                
                argument = {"request":"generatePNGMap", "inputFile": plasmid_map_path,
                "outputPng": png_plasmid_map_path, "title": "p{}{} - {}".format(LAB_ABBREVIATION_FOR_FILES, obj_id, obj_name),
                "showEnzymes": True, "showFeatures": True, "showPrimers": True, "showORFs": False}
                r = client.requestResponse(argument, 10000)
                r_code = r.get('code', 1)
                if r_code > 0:
                    error_message = 'generatePNGMap - error ' + r_code
                    if error_message not in messages: messages.append(error_message)
                    client.close()
                    raise Exception
                
                argument = {"request":"exportDNAFile", "inputFile": plasmid_map_path,
                "outputFile": gbk_plasmid_map_path, "exportFilter": "biosequence.gb"}
                r = client.requestResponse(argument, 10000)
                r_code = r.get('code', 1)
                if r_code > 0:
                    error_message = 'exportDNAFile - error ' + r_code
                    if error_message not in messages: messages.append(error_message)
                    client.close()
                    raise Exception

                client.close()

            except:
                self.create_plasmid_map_preview(plasmid_map_path, png_plasmid_map_path, gbk_plasmid_map_path, obj_id, obj_name, detect_common_features, attempt_number - 1, messages)

        else:
            mail_admins("Snapgene server error", 
                        "There was an error with creating the preview for {} with snapgene server.\n\nErrors: {}.".format(plasmid_map_path, str(messages)), 
                        fail_silently=True)
            raise Exception

    def get_plasmid_map_features(self, plasmid_map_path, attempt_number=3, messages=[]):
        """ Given a path to a snapgene plasmid map (.dna), use snapegene server
        to return features, as json"""

        if attempt_number > 0:
            try:
                config = Config()
                server_ports = config.get_server_ports()
                for port in server_ports.values():
                    try:
                        client = Client(port, zmq.Context())
                    except:
                        continue
                    else:
                        break
            
                argument = {"request":"reportFeatures", "inputFile": plasmid_map_path}
                r = client.requestResponse(argument, 10000)
                r_code = r.get('code', 1)
                if r_code > 0:
                    error_message = 'reportFeatures - error ' + r_code
                    if error_message not in messages: messages.append(error_message)
                    client.close()
                    raise Exception
                
                client.close()

                return r
            
            except:
                self.get_plasmid_map_features(plasmid_map_path, attempt_number - 1, messages)
        
        else:
            mail_admins("Snapgene server error", 
                        "There was an error with getting plasmid features for {} with snapgene server.\n\nErrors: {}.".format(plasmid_map_path, str(messages)), 
                        fail_silently=True)
            raise Exception

    def convert_plasmid_map_gbk_to_dna(self, gbk_map_path, dna_map_path, attempt_number=3, messages=[]):
        """ Given a path to a snapgene plasmid map (.dna), use snapegene server
        to return features, as json"""

        if attempt_number > 0:
            try:
                config = Config()
                server_ports = config.get_server_ports()
                for port in server_ports.values():
                    try:
                        client = Client(port, zmq.Context())
                    except:
                        continue
                    else:
                        break
                
                argument = {"request":"importDNAFile", "inputFile": gbk_map_path, 'outputFile': dna_map_path}
                r = client.requestResponse(argument, 10000)
                r_code = r.get('code', 1)
                if r_code > 0:
                    error_message = 'importDNAFile - error ' + r_code
                    if error_message not in messages: messages.append(error_message)
                    client.close()
                    raise Exception

                client.close()
            
            except:
                self.convert_plasmid_map_gbk_to_dna(plasmid_map_path, attempt_number - 1, messages)
        
        else:
            mail_admins("Snapgene server error", 
                        "There was an error converting a gbk map to dna for {} with snapgene server.\n\nErrors: {}.".format(gbk_map_path, str(messages)), 
                        fail_silently=True)
            raise Exception

#################################################
#                 OLIGO PAGES                   #
#################################################

from .models import Oligo

class SearchFieldOptUsernameOligo(SearchFieldOptUsername):

    id_list = Oligo.objects.all().values_list('created_by', flat=True).distinct()

class SearchFieldOptLastnameOligo(SearchFieldOptLastname):

    id_list = Oligo.objects.all().values_list('created_by', flat=True).distinct()

class OligoQLSchema(DjangoQLSchema):
    '''Customize search functionality'''
    
    include = (Oligo, User) # Include only the relevant models to be searched
    
    def get_fields(self, model):
        '''Define fields that can be searched'''
        
        if model == Oligo:
            return ['id', 'name','sequence', FieldUse(), 'gene', 'restriction_site', 'description', 'comment', 'created_by',]
        elif model == User:
            return [SearchFieldOptUsernameOligo(), SearchFieldOptLastnameOligo()]
        return super(OligoQLSchema, self).get_fields(model)

class OligoExportResource(resources.ModelResource):
    """Defines a custom export resource class for Oligo"""
    
    class Meta:
        model = Oligo
        fields = ('id', 'name','sequence', 'us_e', 'gene', 'restriction_site', 'description', 'comment',
        'created_date_time', 'created_by__username',)

def export_oligo(modeladmin, request, queryset):
    """Export Oligo"""

    export_data = OligoExportResource().export(queryset)

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
export_oligo.short_description = "Export selected oligos"

class OligoPage(DjangoQLSearchMixin, SimpleHistoryWithSummaryAdmin, admin.ModelAdmin, Approval):
    list_display = ('id', 'name','get_oligo_short_sequence', 'restriction_site','created_by', 'approval')
    list_display_links = ('id',)
    list_per_page = 25
    formfield_overrides = {
    CharField: {'widget': TextInput(attrs={'size':'93'})},} # Make TextInput fields wider
    djangoql_schema = OligoQLSchema
    actions = [export_oligo]
    search_fields = ['id', 'name']

    def get_oligo_short_sequence(self, instance):
        '''This function allows you to define a custom field for the list view to
        be defined in list_display as the name of the function, e.g. in this case
        list_display = ('id', 'name', )'''
        
        if instance.sequence:
            if len(instance.sequence) <= 75:
                return instance.sequence
            else:
                return instance.sequence[0:75] + "..."
    get_oligo_short_sequence.short_description = 'Sequence'

    def save_model(self, request, obj, form, change):
        '''Override default save_model to limit a user's ability to save a record
        Superusers and lab managers can change all records
        Regular users can change only their own records
        Guests cannot change any record'''
        
        if obj.pk == None:
            
            obj.created_by = request.user
            obj.save()

            # If the request's user is the principal investigator, approve the record
            # right away. If not, create an approval record
            if request.user.labuser.is_principal_investigator:
                original_last_changed_date_time = obj.last_changed_date_time
                obj.created_approval_by_pi = True
                obj.approval_by_pi_date_time = timezone.now()
                obj.save_without_historical_record()
                Oligo.objects.filter(id=obj.pk).update(last_changed_date_time=original_last_changed_date_time)
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
                    obj.save_without_historical_record()
                    Oligo.objects.filter(id=obj.pk).update(last_changed_date_time=original_last_changed_date_time)
                return

            if self.can_change:

                # Approve right away if the request's user is the principal investigator. If not,
                # create an approval record
                if request.user.labuser.is_principal_investigator:
                    obj.last_changed_approval_by_pi = True
                    obj.approval_by_pi_date_time = timezone.now()
                    if obj.approval.all().exists():
                        approval_records = obj.approval.all()
                        approval_records.delete()
                else:
                    obj.last_changed_approval_by_pi = False

                    # If an approval record for this object does not exist, create one
                    if not obj.approval.all().exists():
                        obj.approval.create(activity_type='changed', activity_user=request.user)
                    else:
                        # If an approval record for this object exists, check if a message was 
                        # sent. If so, update the approval record's edited field
                        approval_obj = obj.approval.all().latest(field_name='message_date_time')
                        if approval_obj.message_date_time:
                            if obj.last_changed_date_time > approval_obj.message_date_time:
                                approval_obj.edited = True
                                approval_obj.save()

                obj.save()

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
                return ['created_date_time', 'created_approval_by_pi', 'last_changed_date_time', 'last_changed_approval_by_pi','created_by'] 
            else:
                return ['name','sequence', 'us_e', 'gene', 'restriction_site', 'description', 'comment', 'created_date_time',
                'created_approval_by_pi', 'last_changed_date_time', 'last_changed_approval_by_pi', 'created_by',]
        else:
            return ['created_date_time', 'created_approval_by_pi', 'last_changed_date_time', 'last_changed_approval_by_pi',]
    
    def add_view(self,request,extra_context=None):
        '''Override default add_view to show only desired fields'''
        
        self.fields = ('name','sequence', 'us_e', 'gene', 'restriction_site', 'description', 'comment', )
        return super(OligoPage,self).add_view(request)

    def change_view(self,request,object_id,extra_context=None):
        '''Override default change_view to show only desired fields'''

        self.can_change = False
        extra_context = extra_context or {}

        if object_id:
            self.can_change = request.user == Oligo.objects.get(pk=object_id).created_by or \
                    request.user.groups.filter(name='Lab manager').exists() or \
                    request.user.is_superuser or request.user.labuser.is_principal_investigator
        
            if self.can_change:

                extra_context = {'show_close': True,
                                 'show_save_and_add_another': True,
                                 'show_save_and_continue': True,
                                 'show_save_as_new': True,
                                 'show_save': True,}

            else:

                extra_context = {'show_close': True,
                                 'show_save_and_add_another': False,
                                 'show_save_and_continue': False,
                                 'show_save_as_new': False,
                                 'show_save': False,}

            extra_context['show_disapprove'] = True if request.user.groups.filter(name='Approval manager').exists() else False

        if '_saveasnew' in request.POST:
            self.fields = ('name','sequence', 'us_e', 'gene', 'restriction_site', 'description', 'comment' )
        else:
            self.fields = ('name','sequence', 'us_e', 'gene', 'restriction_site', 'description', 'comment',
                'created_date_time', 'created_approval_by_pi', 'last_changed_date_time', 'last_changed_approval_by_pi', 'created_by',)

        return super(OligoPage,self).change_view(request,object_id, extra_context=extra_context)

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
            return HttpResponseRedirect(reverse("admin:record_approval_recordtobeapproved_change", args=(obj.approval.latest('created_date_time').id,)))
        
        return super(OligoPage,self).response_change(request,obj)

#################################################
#            SC. POMBE STRAIN PAGES             #
#################################################

from .models import ScPombeStrain
from .models import ScPombeStrainEpisomalPlasmid

class SearchFieldOptUsernameScPom(SearchFieldOptUsername):

    id_list = ScPombeStrain.objects.all().values_list('created_by', flat=True).distinct()

class SearchFieldOptLastnameScPom(SearchFieldOptLastname):

    id_list = ScPombeStrain.objects.all().values_list('created_by', flat=True).distinct()

class FieldEpisomalPlasmidFormZProjectScPom(StrField):
    
    name = 'episomal_plasmids_formz_projects_title'
    suggest_options = True

    def get_options(self):
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
            'phenotype', 'received_from', 'comment', 'created_by', FieldFormZProject(), FieldEpisomalPlasmidFormZProjectScPom()]
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
    verbose_name_plural = "Episomal plasmids"
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

class ScPombeStrainPage(DjangoQLSearchMixin, SimpleHistoryWithSummaryAdmin, admin.ModelAdmin, Approval):
    list_display = ('id', 'name', 'auxotrophic_marker', 'mating_type', 'approval',)
    list_display_links = ('id', )
    list_per_page = 25
    formfield_overrides = {CharField: {'widget': TextInput(attrs={'size':'93'})},}
    djangoql_schema = ScPombeStrainQLSchema
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
                    obj.approval_user = request.user
                    obj.approval_by_pi_date_time = timezone.now()
                    if obj.approval.all().exists():
                        approval_records = obj.approval.all()
                        approval_records.delete()
                else:
                    obj.last_changed_approval_by_pi = False
                    obj.approval_user = None

                    # If an approval record for this object does not exist, create one
                    if not obj.approval.all().exists():
                        obj.approval.create(activity_type='changed', activity_user=request.user)
                    else:
                        # If an approval record for this object exists, check if a message was 
                        # sent. If so, update the approval record's edited field
                        approval_obj = obj.approval.all().latest(field_name='message_date_time')
                        if approval_obj.message_date_time:
                            if obj.last_changed_date_time > approval_obj.message_date_time:
                                approval_obj.edited = True
                                approval_obj.save()

                obj.save()

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
        
        integrated_plasmids = obj.integrated_plasmids.all().order_by('id')
        cassette_plasmids = obj.cassette_plasmids.all().order_by('id')
        episomal_plasmids = obj.episomal_plasmids.all().order_by('id')

        obj.history_integrated_plasmids = str(tuple(integrated_plasmids.values_list('id', flat=True))).replace(',)', ')') if integrated_plasmids else ""
        obj.history_cassette_plasmids = str(tuple(cassette_plasmids.values_list('id', flat=True))).replace(',)', ')') if cassette_plasmids else ""
        obj.history_episomal_plasmids = str(tuple(episomal_plasmids.values_list('id', flat=True))).replace(',)', ')') if episomal_plasmids else ""

        plasmid_id_list = integrated_plasmids | cassette_plasmids | episomal_plasmids.filter(scpombestrainepisomalplasmid__present_in_stocked_strain=True) # Merge querysets
        if plasmid_id_list:
            plasmid_id_list = tuple(plasmid_id_list.distinct().order_by('id').values_list('id', flat=True))
            obj.history_all_plasmids_in_stocked_strain = str(plasmid_id_list).replace(',)', ')')

        obj.history_formz_projects = str(tuple(obj.formz_projects.all().order_by('short_title_english').values_list('short_title_english', flat=True))).replace(',)', ')') if obj.formz_projects.all() else ""
        obj.history_formz_gentech_methods = str(tuple(obj.formz_gentech_methods.all().order_by('english_name').values_list('english_name', flat=True))).replace(',)', ')') if obj.formz_gentech_methods.all() else ""
        obj.history_formz_elements = str(tuple(obj.formz_elements.all().order_by('name').values_list('name', flat=True))).replace(',)', ')') if obj.formz_elements.all() else ""

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

        if object_id:
            
            self.can_change = request.user == ScPombeStrain.objects.get(pk=object_id).created_by or \
                    request.user.groups.filter(name='Lab manager').exists() or \
                    request.user.is_superuser or request.user.labuser.is_principal_investigator
            extra_context = extra_context or {}
            extra_context['show_formz'] = True
            obj = ScPombeStrain.objects.get(pk=object_id)
            
            if obj.history_all_plasmids_in_stocked_strain:
                extra_context['plasmid_id_list'] = obj.history_all_plasmids_in_stocked_strain
            
            if request.user == obj.created_by or request.user.groups.filter(name='Lab manager').exists() or \
                request.user.is_superuser or request.user.labuser.is_principal_investigator:

                extra_context = {'show_close': True,
                                'show_save_and_add_another': True,
                                'show_save_and_continue': True,
                                'show_save_as_new': True,
                                'show_save': True,
                                'show_obj_permission': True
                                }

            else:

                 extra_context = {'show_close': True,
                                 'show_save_and_add_another': False,
                                 'show_save_and_continue': False,
                                 'show_save_as_new': False,
                                 'show_save': False,
                                 'show_obj_permission': False}
            
            extra_context['show_disapprove'] = True if request.user.groups.filter(name='Approval manager').exists() else False
            extra_context['show_formz'] = True

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
        else:
            self.fieldsets = (
            (None, {
                'fields': ('box_number', 'parent_1', 'parent_2', 'parental_strain', 'mating_type', 'auxotrophic_marker', 'name',
                'integrated_plasmids', 'cassette_plasmids', 'phenotype', 'received_from', 'comment', 'created_date_time', 
                'created_approval_by_pi', 'last_changed_date_time', 'last_changed_approval_by_pi','created_by',)
            }),
            ('FormZ', {
                'classes': ('collapse',),
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
            return HttpResponseRedirect(reverse("admin:record_approval_recordtobeapproved_change", args=(obj.approval.latest('created_date_time').id,)))
        
        return super(ScPombeStrainPage,self).response_change(request,obj)

#################################################
#              E. COLI STRAIN PAGES             #
#################################################

from .models import EColiStrain

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
            'note', 'created_by', FieldFormZProject(), ]
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
export_ecolistrain.short_description = "Export selected strains"

class EColiStrainPage(DjangoQLSearchMixin, SimpleHistoryWithSummaryAdmin, admin.ModelAdmin, Approval):
    list_display = ('id', 'name', 'resistance', 'us_e','purpose', 'approval')
    list_display_links = ('id', )
    list_per_page = 25
    formfield_overrides = {CharField: {'widget': TextInput(attrs={'size':'93'})},}
    djangoql_schema = EColiStrainQLSchema
    actions = [export_ecolistrain, formz_as_html]
    search_fields = ['id', 'name']
    autocomplete_fields = ['formz_projects', 'formz_elements']
    
    def save_model(self, request, obj, form, change):
        '''Override default save_model to limit a user's ability to save a record
        Superusers and lab managers can change all records
        Regular users can change only their own records
        Guests cannot change any record'''

        if obj.pk == None:
            
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

            if self.can_change:
                
                # Approve right away if the request's user is the principal investigator. If not,
                # create an approval record
                if request.user.labuser.is_principal_investigator and request.user.id in obj.formz_projects.all().values_list('project_leader__id', flat=True):
                    obj.last_changed_approval_by_pi = True
                    obj.approval_user = request.user
                    obj.approval_by_pi_date_time = timezone.now()
                    if obj.approval.all().exists():
                        approval_records = obj.approval.all()
                        approval_records.delete()
                else:
                    obj.last_changed_approval_by_pi = False
                    obj.approval_user = None

                    # If an approval record for this object does not exist, create one
                    if not obj.approval.all().exists():
                        obj.approval.create(activity_type='changed', activity_user=request.user)
                    else:
                        # If an approval record for this object exists, check if a message was 
                        # sent. If so, update the approval record's edited field
                        approval_obj = obj.approval.all().latest(field_name='message_date_time')
                        if approval_obj.message_date_time:
                            if obj.last_changed_date_time > approval_obj.message_date_time:
                                approval_obj.edited = True
                                approval_obj.save()

                obj.save()
                
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
        
        self.can_change = False

        if object_id:
            
            obj = EColiStrain.objects.get(pk=object_id)

            if request.user == obj.created_by or request.user.groups.filter(name='Lab manager').exists() or \
                request.user.labuser.is_principal_investigator or request.user.is_superuser:
                
                self.can_change = True
                
                extra_context = {'show_close': True,
                                'show_save_and_add_another': True,
                                'show_save_and_continue': True,
                                'show_save_as_new': True,
                                'show_save': True,
                                'show_obj_permission': True}

            else:

                extra_context = {'show_close': True,
                                 'show_save_and_add_another': False,
                                 'show_save_and_continue': False,
                                 'show_save_as_new': False,
                                 'show_save': False,
                                 'show_obj_permission': False}
            
            extra_context['show_disapprove'] = True if request.user.groups.filter(name='Approval manager').exists() else False
            extra_context['show_formz'] = True

        self.fieldsets = (
            (None, {
                'fields': ('name', 'resistance', 'genotype', 'background', 'supplier', 'us_e', 'purpose', 'note', 'created_date_time', 
                'created_approval_by_pi', 'last_changed_date_time', 'last_changed_approval_by_pi', 'created_by',)
            }),
            ('FormZ', {
                'classes': ('collapse',),
                'fields': ('formz_projects', 'formz_risk_group', 'formz_elements', 'destroyed_date')
            }),
            )

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
            return HttpResponseRedirect(reverse("admin:record_approval_recordtobeapproved_change", args=(obj.approval.latest('created_date_time').id,)))
        
        return super(EColiStrainPage,self).response_change(request,obj)

    def save_related(self, request, form, formsets, change):
        
        super(EColiStrainPage, self).save_related(request, form, formsets, change)

        # Keep a record of the IDs of linked M2M fields in the main strain record
        # Not pretty, but it works

        obj = EColiStrain.objects.get(pk=form.instance.id)

        obj.history_formz_projects = str(tuple(obj.formz_projects.all().order_by('short_title_english').values_list('short_title_english', flat=True))).replace(',)', ')') if obj.formz_projects.all() else ""
        obj.history_formz_elements = str(tuple(obj.formz_elements.all().order_by('name').values_list('name', flat=True))).replace(',)', ')') if obj.formz_elements.all() else ""
        obj.save_without_historical_record()

        history_obj = obj.history.latest()
        history_obj.history_formz_projects = obj.history_formz_projects
        history_obj.history_formz_elements = obj.history_formz_elements
        history_obj.save()

#################################################
#               CELL LINE DOC                   #
#################################################

from .models import CellLineDoc 
from .models import CellLine as CellLine
from .models import CellLineEpisomalPlasmid

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

    def has_add_permission(self, request):
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

    def get_options(self):
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
            'created_by', FieldFormZProject(), FieldEpisomalPlasmidFormZProjectCellLine()]
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
export_cellline.short_description = "Export selected cell lines"

class CellLineEpisomalPlasmidInline(admin.TabularInline):
    
    autocomplete_fields = ['plasmid', 'formz_projects']
    model = CellLineEpisomalPlasmid
    verbose_name_plural = "Transiently transfected plasmids"
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

class CellLinePage(DjangoQLSearchMixin, SimpleHistoryWithSummaryAdmin, CustomGuardedModelAdmin, Approval):
    
    list_display = ('id', 'name', 'box_name', 'created_by', 'approval')
    list_display_links = ('id', )
    list_per_page = 25
    formfield_overrides = {CharField: {'widget': TextInput(attrs={'size':'93'})},}
    djangoql_schema = CellLineQLSchema
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
                obj.approval_user = request.user
                obj.approval_by_pi_date_time = timezone.now()
                if obj.approval.all().exists():
                    approval_records = obj.approval.all()
                    approval_records.delete()
            else:
                obj.last_changed_approval_by_pi = False
                obj.approval_user = None

                # If an approval record for this object does not exist, create one
                if not obj.approval.all().exists():
                    obj.approval.create(activity_type='changed', activity_user=request.user)
                else:
                    # If an approval record for this object exists, check if a message was 
                    # sent. If so, update the approval record's edited field
                    approval_obj = obj.approval.all().latest(field_name='message_date_time')
                    if approval_obj.message_date_time:
                        if obj.last_changed_date_time > approval_obj.message_date_time:
                            approval_obj.edited = True
                            approval_obj.save()

            obj.save()
    
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
        
        integrated_plasmids = obj.integrated_plasmids.all().order_by('id')
        episomal_plasmids = obj.episomal_plasmids.all().order_by('id')

        obj.history_integrated_plasmids = str(tuple(integrated_plasmids.values_list('id', flat=True))).replace(',)', ')') if integrated_plasmids else ""
        obj.history_episomal_plasmids = str(tuple(episomal_plasmids.values_list('id', flat=True))).replace(',)', ')') if episomal_plasmids else ""

        obj.history_formz_projects = str(tuple(obj.formz_projects.all().order_by('short_title_english').values_list('short_title_english', flat=True))).replace(',)', ')') if obj.formz_projects.all() else ""
        obj.history_formz_gentech_methods = str(tuple(obj.formz_gentech_methods.all().order_by('english_name').values_list('english_name', flat=True))).replace(',)', ')') if obj.formz_gentech_methods.all() else ""
        obj.history_formz_elements = str(tuple(obj.formz_elements.all().order_by('name').values_list('name', flat=True))).replace(',)', ')') if obj.formz_elements.all() else ""
        obj.history_documents = str(tuple(obj.celllinedoc_set.all().order_by('id').values_list('id', flat=True))).replace(',)', ')') if obj.celllinedoc_set.all() else ""

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
        
        if object_id:
            
            obj = CellLine.objects.get(pk=object_id)
            extra_context = extra_context or {}
            extra_context['show_formz'] = True
            
            if obj.history_integrated_plasmids:
                extra_context['plasmid_id_list'] = obj.history_integrated_plasmids
        
            if request.user == obj.created_by or request.user.groups.filter(name='Lab manager').exists() or \
                request.user.labuser.is_principal_investigator or request.user.is_superuser or \
                request.user.has_perm('collection_management.change_cellline', obj):
                
                self.can_change = True
                
                extra_context = {'show_close': True,
                            'show_save_and_add_another': True,
                            'show_save_and_continue': True,
                            'show_save_as_new': True,
                            'show_save': True,
                            'show_obj_permission': True,
                            }
            else:
                
                extra_context = {'show_close': True,
                                 'show_save_and_add_another': True,
                                 'show_save_and_continue': True,
                                 'show_save_as_new': False,
                                 'show_save': True,
                                 'show_obj_permission': False}

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

        else:
            self.fieldsets = (
            (None, {
                'fields': ('name', 'box_name', 'alternative_name', 'parental_line', 'organism', 'cell_type_tissue', 'culture_type', 'growth_condition',
                    'freezing_medium', 'received_from', 'integrated_plasmids', 'description_comment', 's2_work', 'created_date_time', 'created_approval_by_pi',
                'last_changed_date_time', 'last_changed_approval_by_pi', 'created_by',)
            }),
            ('FormZ', {
                'classes': ('collapse',),
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
            return HttpResponseRedirect(reverse("admin:record_approval_recordtobeapproved_change", args=(obj.approval.latest('created_date_time').id,)))
        
        return super(CellLinePage,self).response_change(request,obj)
    
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        
        try:
            request.resolver_match.args[0]
        except:
            
            # Exclude certain users from the 'Created by' field in the order form

            if db_field.name == 'organism':
                kwargs["queryset"] = Species.objects.filter(show_in_cell_line_collection=True)

        return super(CellLinePage, self).formfield_for_foreignkey(db_field, request, **kwargs)

#################################################
#                ANTIBODY PAGES                 #
#################################################

from .models import Antibody

class AntibodyQLSchema(DjangoQLSchema):
    '''Customize search functionality'''
    
    def get_fields(self, model):
        '''Define fields that can be searched'''
        
        if model == Antibody:
            return ['id', 'name', 'species_isotype', 'clone', 'received_from', 'catalogue_number', 'info_sheet',
                FieldLocation(), FieldApplication(), 'description_comment','info_sheet', ]
        return super(AntibodyQLSchema, self).get_fields(model)

class AntibodyExportResource(resources.ModelResource):
    """Defines a custom export resource class for Antibody"""
    
    class Meta:
        model = Antibody
        fields = ('id', 'name', 'species_isotype', 'clone', 'received_from', 'catalogue_number', 'l_ocation', 'a_pplication',
                'description_comment', 'info_sheet',)

def export_antibody(modeladmin, request, queryset):
    """Export Antibody"""

    export_data = AntibodyExportResource().export(queryset)

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
export_antibody.short_description = "Export selected antibodies"

class AntibodyPage(DjangoQLSearchMixin, SimpleHistoryWithSummaryAdmin, admin.ModelAdmin):
    
    list_display = ('id', 'name', 'catalogue_number', 'received_from', 'species_isotype', 'clone', 'l_ocation', 'get_sheet_short_name')
    list_display_links = ('id', )
    list_per_page = 25
    formfield_overrides = {CharField: {'widget': TextInput(attrs={'size':'93'})},}
    djangoql_schema = AntibodyQLSchema
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
            doc_dir_path = os.path.join(MEDIA_ROOT, 'collection_management/antibody/')
            old_file_name_abs_path = os.path.join(MEDIA_ROOT, obj.info_sheet.name)
            old_file_name, ext = os.path.splitext(os.path.basename(old_file_name_abs_path)) 
            new_file_name = os.path.join(
                'collection_management/antibody/',
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
                'description_comment', 'info_sheet', )
        return super(AntibodyPage,self).add_view(request)
    
    def change_view(self,request,object_id,extra_context=None):
        '''Override default change_view to show only desired fields'''

        self.fields = ('name', 'species_isotype', 'clone', 'received_from', 'catalogue_number', 'l_ocation', 'a_pplication',
                'description_comment', 'info_sheet','created_date_time','last_changed_date_time', )
        return super(AntibodyPage,self).change_view(request,object_id)

    def get_sheet_short_name(self, instance):
        '''Create custom column for information sheet
        It formats a html element a for the information sheet
        such that the text shown for a link is always View'''

        if instance.info_sheet:
            return mark_safe('<a href="{}">View</a>'.format(str(instance.info_sheet.url)))
        else:
            return ''
    get_sheet_short_name.short_description = 'Info Sheet'