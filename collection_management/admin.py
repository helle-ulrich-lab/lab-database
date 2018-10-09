# -*- coding: utf-8 -*-

from __future__ import unicode_literals

#################################################
#    DJANGO 'CORE' FUNCTIONALITIES IMPORTS      #
#################################################

from django import forms

from django.contrib import admin
from django.contrib import messages
from django.contrib.auth.admin import UserAdmin

from django.apps import apps
from django.db import models

from django.core.urlresolvers import reverse
from django.core.mail import send_mail
from django.core.exceptions import PermissionDenied

from django.utils.translation import ugettext as _, ugettext_lazy
from django.utils.text import capfirst

from django.forms import TextInput
from django.views.decorators.cache import never_cache
from django.http import HttpResponseRedirect
from django.urls import NoReverseMatch, reverse

from . import views

#################################################
#        ADDED FUNCTIONALITIES IMPORTS          #
#################################################

import os

# Advanced search functionalities from DjangoQL
from djangoql.admin import DjangoQLSearchMixin
from djangoql.schema import DjangoQLSchema, StrField

# Object history tracking from django-simple-history
from simple_history.admin import SimpleHistoryAdmin

# Import/Export functionalities from django-import-export
from import_export.admin import ExportActionModelAdmin

# Google Sheets API to add new orders to Order Master List
import pygsheets

#################################################
#                OTHER IMPORTS                  #
#################################################

from django.contrib.auth.models import Group, User
from django.contrib.auth.admin import GroupAdmin, UserAdmin
from .models import ArcheNoahAnimal as collection_management_ArcheNoahAnimal

#################################################
#                CUSTOM CLASSES                 #
#################################################

class Approval():
    def approval(self, instance):
        if instance.last_changed_approval_by_pi:
            return instance.last_changed_approval_by_pi
        else:
            return instance.created_approval_by_pi
    approval.boolean = True
    approval.short_description = "Approved"

from django.contrib.admin.utils import unquote
from django.contrib.contenttypes.models import ContentType
from django.conf import settings
from django.utils.encoding import force_text
from django.shortcuts import get_object_or_404, render

USER_NATURAL_KEY = tuple(
    key.lower() for key in settings.AUTH_USER_MODEL.split('.', 1))

class SimpleHistoryWithSymmaryAdmin(SimpleHistoryAdmin):
    
    object_history_template = "admin/object_history.html"
    
    def history_view(self, request, object_id, extra_context=None):
        """The 'history' admin view for this model."""

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
        history_list_display = getattr(self, "history_list_display", [])
        # If no history was found, see whether this object even exists.
        try:
            obj = self.get_queryset(request).get(**{pk_name: object_id})
        except model.DoesNotExist:
            try:
                obj = action_list.latest('history_date').instance
            except action_list.model.DoesNotExist:
                raise http.Http404

        if not self.has_change_permission(request, obj):
            raise PermissionDenied

        # Set attribute on each action_list entry from admin methods
        for history_list_entry in history_list_display:
            value_for_entry = getattr(self, history_list_entry, None)
            if value_for_entry and callable(value_for_entry):
                for list_entry in action_list:
                    setattr(list_entry, history_list_entry,
                            value_for_entry(list_entry))

        # Create data structure for history summary
        history_summary_data = []
        try:
            history_summary = obj.history.all()
            if len(history_summary) > 1:
                history_pairs = pairwise(history_summary)
                for history_element in history_pairs:
                    delta = history_element[0].diff_against(history_element[1])
                    if delta:
                        changes_list = []
                        changes = delta.changes
                        if delta.changes:
                            for change in delta.changes:
                                if not change.field.endswith(("time", "_pi")): # Do not show created/changed date/time or approval by PI fields
                                    field_name = change.field if change.field[1] != "_" else change.field[:1] + change.field[2:]
                                    changes_list.append(
                                        (field_name.replace("_", " ").capitalize(), 
                                        change.old if change.old else 'None', 
                                        change.new if change.new else 'None'))
                            if changes_list:
                                history_summary_data.append(
                                    (history_element[0].last_changed_date_time, 
                                    User.objects.get(id=int(history_element[0].history_user_id)), 
                                    changes_list))
        except:
            pass

        content_type = ContentType.objects.get_by_natural_key(
            *USER_NATURAL_KEY)
        admin_user_view = 'admin:%s_%s_change' % (content_type.app_label,
                                                  content_type.model)
        context = {
            'title': _('Change history: %s') % force_text(obj),
            'action_list': action_list,
            'module_name': capfirst(force_text(opts.verbose_name_plural)),
            'object': obj,
            'root_path': getattr(self.admin_site, 'root_path', None),
            'app_label': app_label,
            'opts': opts,
            'admin_user_view': admin_user_view,
            'history_list_display': history_list_display,
            'history_summary_data': history_summary_data,
        }
        context.update(extra_context or {})
        extra_kwargs = {}
        return render(request, self.object_history_template, context,
                      **extra_kwargs)

#################################################
#               CUSTOM ADMIN SITE               #
#################################################

class MyAdminSite(admin.AdminSite):
    '''Create a custom admin site called MyAdminSite'''
    
    # Text to put at the end of each page's <title>.
    site_title = ugettext_lazy('Ulrich Lab Intranet')

    # Text to put in each page's <h1>.
    site_header = ugettext_lazy('Ulrich Lab Intranet')

    # Text to put at the top of the admin index page.
    index_title = ugettext_lazy('Home')

    # URL for the "View site" link at the top of each admin page.
    site_url = '/'

    def get_urls(self):
        from django.conf.urls import url
        urls = super(MyAdminSite, self).get_urls()
        # Note that custom urls get pushed to the list (not appended)
        # This doesn't work with urls += ...
        urls = [
            url(r'^update_gdocs_user_list$', self.update_lab_users_google_sheet),
            url(r'^approval_summary/$', self.admin_view(self.approval_summary)),
            url(r'^approval_summary/approve$', self.admin_view(self.approve_approval_summary)),
            url(r'^order_management/my_orders_redirect$', self.admin_view(self.my_orders_redirect)),
            #url(r'^uploads/(?P<folder>[\w\-]+)/(?P<file_name>.*)$', self.admin_view(self.document_view)),
            url(r'secure_location/(?P<file_name>.*)$', self.admin_view(self.document_view)),

        ] + urls
        return urls
    
    def update_lab_users_google_sheet (self, request):
        """ Update active user list sheet on GoogleDocs """

        import os
        import sys

        import pygsheets

        from django_project.private_settings import LAB_MEMBERS_SHEET_ID

        try:
            # Log in to GoogleDocs
            base_path = os.path.abspath(os.path.join(os.path.dirname( __file__ ), '..'))
            gc = pygsheets.authorize(service_file=base_path + "/beyond_django/gdrive_access_credentials.json", no_cache=True)
            # Open user list Google sheet
            spreadsheet = gc.open_by_key(LAB_MEMBERS_SHEET_ID)
            worksheet = spreadsheet.worksheet('title', 'Users')
            # Get list of active users 
            users = [[user.first_name, user.last_name, user.email, user.labuser.abbreviation_code] \
                    for user in User.objects.filter(is_active=True).exclude(id__in=[1,6,20]).exclude(groups__name='Guest').order_by('last_name')]
            # Update user list Google sheet
            worksheet.clear(start=(2,1))
            worksheet.update_cells(crange=(2,1), values=users, extend=True)
            messages.success(request, 'The user list on GoogleDocs was updated successfully')
        except Exception as err:
            messages.error(request, 'The user list on GoogleDocs could not be updated. Error: ' + str(err))
        return HttpResponseRedirect("../")

    def approval_summary(self, request):
        """ View to show all added and changed records from 
        collection_management that have been added or changed
        and that need to be approved by Helle"""
        
        from django.shortcuts import render
        from django.apps import apps

        if request.user.is_superuser or request.user.groups.filter(name='Lab manager').exists(): # Only allow superusers and lab managers to access the page
            data = []
            app = apps.get_app_config('collection_management')
            for model in app.models.values():
                if not model._meta.verbose_name.lower().startswith(("historical", "arche", "antibody", "mammalian cell line document")): # Skip certain models within collection_management
                    added = model.objects.all().filter(created_approval_by_pi=False)
                    changed = model.objects.all().filter(last_changed_approval_by_pi=False).exclude(id__in=added)
                    if added or changed:
                        data.append(
                            (str(model._meta.verbose_name_plural).capitalize(),
                            str(model.__name__).lower(), 
                            list(added.only('id','name','created_by')),
                            list(changed.only('id','name','created_by'))
                            ))
            context = {
            'user': request.user,
            'site_header': self.site_header,
            'has_permission': self.has_permission(request), 
            'site_url': self.site_url, 
            'title':"Records to be approved", 
            'data':data
            }
            return render(request, 'admin/approval_summary.html', context)
        else:
            raise PermissionDenied
            
    def approve_approval_summary(self, request):
        """ Approve all records that are pending approval """

        if request.user.id == 6: # Only allow Helle to approve records
            try:
                app = apps.get_app_config('collection_management')
                for model in app.models.values():
                    if not model._meta.verbose_name.lower().startswith(("historical", "arche", "antibody", "mammalian cell line document")): # Skip certain models within collection_management 
                        model.objects.all().filter(created_approval_by_pi=False).update(created_approval_by_pi=True)
                        model.objects.all().filter(last_changed_approval_by_pi=False).update(last_changed_approval_by_pi=True)
                messages.success(request, 'The records have been approved')
                return HttpResponseRedirect("/approval_summary/")
            except Exception as err:
                messages.error(request, 'The records could not be approved. Error: ' + str(err))
                return HttpResponseRedirect("/approval_summary/")
        else:
            raise PermissionDenied

    def my_orders_redirect(self, request):
        """ Redirect user to their My Orders page """

        return HttpResponseRedirect(request.user.labuser.personal_order_list_url)

    from django.contrib.auth.decorators import login_required

    def document_view(self, request, *args, **kwargs):
        """Create protected view for file, remember to include login_required, but maybe
        not required because part of the admin site, which by default requires login"""

        from django.http import HttpResponse

        # response = HttpResponse(kwargs.get('file_name',"default value"))
        
        # from collection_management.models import NzPlasmid

        # obj_id = int(kwargs.get('file_name',"default value").split("_")[0][3:])
        # document = NzPlasmid.objects.get(id=obj_id)
        response = HttpResponse()
        # response.content = document.plasmid_map.read()
        response["Content-Disposition"] = "attachment; filename={0}".format(kwargs.get('file_name',"default value"))
        response['X-Accel-Redirect'] = "/secret/{0}".format(kwargs.get('file_name',"default value"))
        return response

# Instantiate custom admin site 
my_admin_site = MyAdminSite()

# Disable delete selected action
my_admin_site.disable_action('delete_selected')

#################################################
#          CUSTOM USER SEARCH OPTIONS           #
#################################################

class SearchFieldOptUsername(StrField):
    """Create a list of unique users' usernames for search"""

    model = User
    name = 'username'
    suggest_options = True

    def get_options(self):
        """exclude(id__in=[1,20]) removes admin and guest accounts from 
        the list of options, distinct() returns only unique values
        sorted in alphabetical order"""

        return super(SearchFieldOptUsername, self).get_options().\
        exclude(id__in=[1,20]).\
        distinct().\
        order_by(self.name).\
        values_list(self.name, flat=True)

class SearchFieldOptLastname(StrField):
    """Create a list of unique user's last names for search"""

    model = User
    name = 'last_name'
    suggest_options = True

    def get_options(self):
        """exclude(id__in=[1,20]) removes admin and guest accounts from 
        the list of options, distinct() returns only unique values
        sorted in alphabetical order"""
        
        return super(SearchFieldOptLastname, self).\
        get_options().\
        exclude(id__in=[1,20]).\
        distinct().order_by(self.name).\
        values_list(self.name, flat=True)

#################################################
#          SA. CEREVISIAE STRAIN PAGES          #
#################################################

from .models import SaCerevisiaeStrain as collection_management_SaCerevisiaeStrain

class SaCerevisiaeStrainQLSchema(DjangoQLSchema):
    '''Customize search functionality'''
    
    include = (collection_management_SaCerevisiaeStrain, User) # Include only the relevant models to be searched

    def get_fields(self, model):
        ''' Define fields that can be searched'''
        
        if model == collection_management_SaCerevisiaeStrain:
            return ['id', 'name', 'relevant_genotype', 'mating_type', 'chromosomal_genotype', 'parental_strain',
                'construction', 'modification', 'plasmids', 'selection', 'phenotype', 'background', 'received_from',
                'us_e', 'note', 'reference', 'created_by',]
        elif model == User:
            return [SearchFieldOptUsername(), SearchFieldOptLastname()]
        return super(SaCerevisiaeStrainQLSchema, self).get_fields(model)

class SaCerevisiaeStrainPage(ExportActionModelAdmin, DjangoQLSearchMixin, SimpleHistoryWithSymmaryAdmin, admin.ModelAdmin, Approval):
    list_display = ('id', 'name', 'mating_type','created_by', 'approval')
    list_display_links = ('id', )
    list_per_page = 25
    formfield_overrides = {models.CharField: {'widget': TextInput(attrs={'size':'93'})},} # Make TextInput fields wider
    djangoql_schema = SaCerevisiaeStrainQLSchema
    
    def save_model(self, request, obj, form, change):
        '''Override default save_model to limit a user's ability to save a record
        Superusers and lab managers can change all records
        Regular users can change only their own records
        Guests cannot change any record'''
        
        if obj.pk == None:
            obj.created_by = request.user
            obj.save()
        else:
            if request.user.is_superuser or request.user == collection_management_SaCerevisiaeStrain.objects.get(pk=obj.pk).created_by or request.user.groups.filter(name='Lab manager').exists():
                obj.last_changed_approval_by_pi = False
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
            if not (request.user.is_superuser or request.user.groups.filter(name='Lab manager').exists() or request.user == obj.created_by) or request.user.groups.filter(name='Guest').exists():
                return ['name', 'relevant_genotype', 'mating_type', 'chromosomal_genotype', 'parental_strain',
                'construction', 'modification', 'plasmids', 'selection', 'phenotype', 'background', 'received_from',
                'us_e', 'note', 'reference', 'created_date_time', 'created_approval_by_pi', 'last_changed_date_time',
                'last_changed_approval_by_pi', 'created_by',]
            else:
                return ['created_date_time', 'created_approval_by_pi', 'last_changed_date_time', 'last_changed_approval_by_pi',]
        else:
            return ['created_date_time', 'created_approval_by_pi', 'last_changed_date_time', 'last_changed_approval_by_pi',]
    
    def add_view(self,request,extra_content=None):
        '''Override default add_view to show only desired fields'''
        
        self.fields = ('name', 'relevant_genotype', 'mating_type', 'chromosomal_genotype', 'parental_strain',
        'construction', 'modification', 'plasmids', 'selection', 'phenotype', 'background', 'received_from',
        'us_e', 'note', 'reference',)
        return super(SaCerevisiaeStrainPage,self).add_view(request)

    def change_view(self,request,object_id,extra_content=None):
        '''Override default change_view to show only desired fields'''
        
        self.fields = ('name', 'relevant_genotype', 'mating_type', 'chromosomal_genotype', 'parental_strain',
        'construction', 'modification', 'plasmids', 'selection', 'phenotype', 'background', 'received_from',
        'us_e', 'note', 'reference', 'created_date_time', 'created_approval_by_pi', 'last_changed_date_time', 
        'last_changed_approval_by_pi', 'created_by',)
        return super(SaCerevisiaeStrainPage,self).change_view(request,object_id)
    
    def changeform_view(self, request, object_id=None, form_url='', extra_context=None):
        """Override default changeform_view to hide Save buttons when certain conditions (same as
        those in get_readonly_fields method) are met"""

        extra_context = extra_context or {}
        extra_context['show_submit_line'] = True
        if object_id:
            obj = collection_management_SaCerevisiaeStrain.objects.get(pk=object_id)
            if obj:
                if not (request.user.is_superuser or request.user.groups.filter(name='Lab manager').exists() or request.user == obj.created_by) or request.user.groups.filter(name='Guest').exists():
                    extra_context['show_submit_line'] = False
        return super(SaCerevisiaeStrainPage, self).changeform_view(request, object_id, extra_context=extra_context)

my_admin_site.register(collection_management_SaCerevisiaeStrain, SaCerevisiaeStrainPage)

#################################################
#                PLASMID PAGES                  #
#################################################

from .models import HuPlasmid as collection_management_HuPlasmid

class HuPlasmidQLSchema(DjangoQLSchema):
    '''Customize search functionality'''
    
    include = (collection_management_HuPlasmid, User) # Include only the relevant models to be searched

    def get_fields(self, model):
        '''Define fields that can be searched'''
        
        if model == collection_management_HuPlasmid:
            return ['id', 'name', 'other_name', 'parent_vector', 'selection', 'us_e', 'construction_feature', 'received_from', 'note', 
                'reference', 'created_by',]
        elif model == User:
            return [SearchFieldOptUsername(), SearchFieldOptLastname()]
        return super(HuPlasmidQLSchema, self).get_fields(model)

class HuPlasmidPage(ExportActionModelAdmin, DjangoQLSearchMixin, SimpleHistoryWithSymmaryAdmin, admin.ModelAdmin, Approval):
    list_display = ('id', 'name', 'selection', 'get_plasmidmap_short_name', 'created_by', 'approval')
    list_display_links = ('id', )
    list_per_page = 25
    formfield_overrides = {models.CharField: {'widget': TextInput(attrs={'size':'93'})},} # Make TextInput fields wider
    djangoql_schema = HuPlasmidQLSchema
    
    def save_model(self, request, obj, form, change):
        '''Override default save_model to limit a user's ability to save a record
        Superusers and lab managers can change all records
        Regular users can change only their own records
        Guests cannot change any record'''
        
        if obj.pk == None:
            obj.created_by = request.user
            obj.save()
        else:
            if request.user.is_superuser or request.user == collection_management_HuPlasmid.objects.get(pk=obj.pk).created_by or request.user.groups.filter(name='Lab manager').exists():
                obj.last_changed_approval_by_pi = False
                obj.save()
            else:
                if obj.created_by.id == 6: # Allow saving object, if record belongs to Helle (user id = 6)
                    obj.last_changed_approval_by_pi = False
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
            if not (request.user.is_superuser or request.user.groups.filter(name='Lab manager').exists() or request.user == obj.created_by or obj.created_by.id == 6) or request.user.groups.filter(name='Guest').exists():
                return ['name', 'other_name', 'parent_vector', 'selection', 'us_e', 'construction_feature', 'received_from', 'note', 
                'reference', 'plasmid_map', 'created_date_time', 'created_approval_by_pi', 'last_changed_date_time',
                'last_changed_approval_by_pi', 'created_by',]
            else:
                if obj.created_by.id == 6 and not (request.user.is_superuser or request.user.groups.filter(name='Lab manager').exists()): # Show plasmid_map and note as editable fields, if record belongs to Helle (user id = 6)
                    return ['name', 'other_name', 'parent_vector', 'selection', 'us_e', 'construction_feature', 'received_from', 
                    'reference', 'created_date_time', 'created_approval_by_pi', 'last_changed_date_time',
                    'last_changed_approval_by_pi', 'created_by',]
                else:
                    return ['created_date_time', 'created_approval_by_pi', 'last_changed_date_time', 'last_changed_approval_by_pi',]
        else:
            return ['created_date_time', 'created_approval_by_pi', 'last_changed_date_time', 'last_changed_approval_by_pi',]
    
    def add_view(self,request,extra_content=None):
        '''Override default add_view to show only desired fields'''
        
        self.fields = ('name', 'other_name', 'parent_vector', 'selection', 'us_e', 'construction_feature', 'received_from', 'note', 
                'reference', 'plasmid_map',)
        return super(HuPlasmidPage,self).add_view(request)
    
    def change_view(self,request,object_id,extra_content=None):
        '''Override default change_view to show only desired fields'''
        
        self.fields = ('name', 'other_name', 'parent_vector', 'selection', 'us_e', 'construction_feature', 'received_from', 'note', 
                'reference', 'plasmid_map', 'created_date_time', 'created_approval_by_pi', 'last_changed_date_time',
                'last_changed_approval_by_pi', 'created_by',)
        return super(HuPlasmidPage,self).change_view(request,object_id)

    def changeform_view(self, request, object_id=None, form_url='', extra_context=None):
        """Override default changeform_view to hide Save buttons when certain conditions (same as
        those in get_readonly_fields method) are met"""

        extra_context = extra_context or {}
        extra_context['show_submit_line'] = True
        if object_id:
            obj = collection_management_HuPlasmid.objects.get(pk=object_id)
            if obj:
                if not (request.user.is_superuser or request.user.groups.filter(name='Lab manager').exists() or request.user == obj.created_by or obj.created_by.id == 6) or request.user.groups.filter(name='Guest').exists():
                    extra_context['show_submit_line'] = False
        return super(HuPlasmidPage, self).changeform_view(request, object_id, extra_context=extra_context)

    def get_plasmidmap_short_name(self, instance):
        '''This function allows you to define a custom field for the list view to
        be defined in list_display as the name of the function, e.g. in this case
        list_display = ('id', 'name', 'selection', 'get_plasmidmap_short_name','created_by',)'''
        if instance.plasmid_map:
            plasmid_name_for_download = "pHU" + str(instance.pk) + " - " + str(instance.name) + "." + str(instance.plasmid_map).split(".")[-1]
            return '<a href="%s" download="%s">Download</a>' % (str(instance.plasmid_map.url), plasmid_name_for_download)
        else:
            return ''
    get_plasmidmap_short_name.allow_tags = True
    get_plasmidmap_short_name.short_description = 'Plasmid map'

    # Add custom js (or css) files to all pages that belong to this model
    class Media:
        js = ('admin/js/vendor/jquery/jquery.js',
        'admin/js/admin/ChangeDownloadLink.js',)

my_admin_site.register(collection_management_HuPlasmid, HuPlasmidPage)

#################################################
#                 OLIGO PAGES                   #
#################################################

from .models import Oligo as collection_management_Oligo

class OligoQLSchema(DjangoQLSchema):
    '''Customize search functionality'''
    
    include = (collection_management_Oligo, User) # Include only the relevant models to be searched
    
    def get_fields(self, model):
        '''Define fields that can be searched'''
        
        if model == collection_management_Oligo:
            return ['id', 'name','sequence', 'us_e', 'gene', 'restriction_site', 'description', 'comment', 'created_by',]
        elif model == User:
            return [SearchFieldOptUsername(), SearchFieldOptLastname()]
        return super(OligoQLSchema, self).get_fields(model)

class OligoPage(ExportActionModelAdmin, DjangoQLSearchMixin, SimpleHistoryWithSymmaryAdmin, admin.ModelAdmin, Approval):
    list_display = ('id', 'name','get_oligo_short_sequence', 'restriction_site','created_by', 'approval')
    list_display_links = ('id',)
    list_per_page = 25
    formfield_overrides = {
    models.CharField: {'widget': TextInput(attrs={'size':'93'})},} # Make TextInput fields wider
    djangoql_schema = OligoQLSchema

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
        else:
            if request.user.is_superuser or request.user == collection_management_Oligo.objects.get(pk=obj.pk).created_by or request.user.groups.filter(name='Lab manager').exists():
                obj.last_changed_approval_by_pi = False
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
            if not (request.user.is_superuser or request.user.groups.filter(name='Lab manager').exists() or request.user == obj.created_by) or request.user.groups.filter(name='Guest').exists():
                return ['name','sequence', 'us_e', 'gene', 'restriction_site', 'description', 'comment', 'created_date_time',
                'created_approval_by_pi', 'last_changed_date_time', 'last_changed_approval_by_pi', 'created_by',]
            else:
                return ['created_date_time', 'created_approval_by_pi', 'last_changed_date_time', 'last_changed_approval_by_pi',]
        else:
            return ['created_date_time', 'created_approval_by_pi', 'last_changed_date_time', 'last_changed_approval_by_pi',]
    
    def add_view(self,request,extra_content=None):
        '''Override default add_view to show only desired fields'''
        
        self.fields = ('name','sequence', 'us_e', 'gene', 'restriction_site', 'description', 'comment', )
        return super(OligoPage,self).add_view(request)

    def change_view(self,request,object_id,extra_content=None):
        '''Override default change_view to show only desired fields'''
        
        self.fields = ('name','sequence', 'us_e', 'gene', 'restriction_site', 'description', 'comment',
        'created_date_time', 'created_approval_by_pi', 'last_changed_date_time', 'last_changed_approval_by_pi', 'created_by',)
        return super(OligoPage,self).change_view(request,object_id)

    def changeform_view(self, request, object_id=None, form_url='', extra_context=None):
        """Override default changeform_view to hide Save buttons when certain conditions (same as
        those in get_readonly_fields method) are met"""

        extra_context = extra_context or {}
        extra_context['show_submit_line'] = True
        if object_id:
            obj = collection_management_Oligo.objects.get(pk=object_id)
            if obj:
                if not (request.user.is_superuser or request.user.groups.filter(name='Lab manager').exists() or request.user == obj.created_by) or request.user.groups.filter(name='Guest').exists():
                    extra_context['show_submit_line'] = False
        return super(OligoPage, self).changeform_view(request, object_id, extra_context=extra_context)

my_admin_site.register(collection_management_Oligo, OligoPage)

#################################################
#            SC. POMBE STRAIN PAGES             #
#################################################

from .models import ScPombeStrain as collection_management_ScPombeStrain

class ScPombeStrainQLSchema(DjangoQLSchema):
    '''Customize search functionality'''
    
    include = (collection_management_ScPombeStrain, User) # Include only the relevant models to be searched

    def get_fields(self, model):
        '''Define fields that can be searched'''
        
        if model == collection_management_ScPombeStrain:
            return ['id', 'box_number', 'parental_strain', 'mating_type', 'auxotrophic_marker', 'name',
                    'phenotype', 'received_from', 'comment', 'created_by',]
        elif model == User:
            return [SearchFieldOptUsername(), SearchFieldOptLastname()]
        return super(ScPombeStrainQLSchema, self).get_fields(model)

class ScPombeStrainPage(ExportActionModelAdmin, DjangoQLSearchMixin, SimpleHistoryWithSymmaryAdmin, admin.ModelAdmin, Approval):
    list_display = ('id', 'name', 'auxotrophic_marker', 'mating_type', 'approval',)
    list_display_links = ('id', )
    list_per_page = 25
    formfield_overrides = {models.CharField: {'widget': TextInput(attrs={'size':'93'})},}
    djangoql_schema = ScPombeStrainQLSchema

    def save_model(self, request, obj, form, change):
        '''Override default save_model to limit a user's ability to save a record
        Superusers and lab managers can change all records
        Regular users can change only their own records
        Guests cannot change any record'''
        
        if obj.pk == None:
            obj.created_by = request.user
            obj.save()
        else:
            if request.user.is_superuser or request.user == collection_management_ScPombeStrain.objects.get(pk=obj.pk).created_by or request.user.groups.filter(name='Lab manager').exists():
                obj.last_changed_approval_by_pi = False
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
            if not (request.user.is_superuser or request.user.groups.filter(name='Lab manager').exists() or request.user == obj.created_by) or request.user.groups.filter(name='Guest').exists():
                return ['box_number', 'parental_strain', 'mating_type', 'auxotrophic_marker', 'name',
        'phenotype', 'received_from', 'comment', 'created_date_time', 'created_approval_by_pi',
        'last_changed_date_time', 'last_changed_approval_by_pi', 'created_by',]
            else:
                return ['created_date_time', 'created_approval_by_pi', 'last_changed_date_time', 'last_changed_approval_by_pi',]
        else:
            return ['created_date_time', 'created_approval_by_pi', 'last_changed_date_time', 'last_changed_approval_by_pi',]

    def add_view(self,request,extra_content=None):
        '''Override default add_view to show only desired fields'''
        
        self.fields = ('box_number', 'parental_strain', 'mating_type', 'auxotrophic_marker', 'name',
        'phenotype', 'received_from', 'comment', )
        return super(ScPombeStrainPage,self).add_view(request)

    def change_view(self,request,object_id,extra_content=None):
        '''Override default change_view to show only desired fields'''
        
        self.fields = ('box_number', 'parental_strain', 'mating_type', 'auxotrophic_marker', 'name',
        'phenotype', 'received_from', 'comment', 'created_date_time', 'created_approval_by_pi',
        'last_changed_date_time', 'last_changed_approval_by_pi', 'created_by',)
        return super(ScPombeStrainPage,self).change_view(request,object_id)

    def changeform_view(self, request, object_id=None, form_url='', extra_context=None):
        """Override default changeform_view to hide Save buttons when certain conditions (same as
        those in get_readonly_fields method) are met"""

        extra_context = extra_context or {}
        extra_context['show_submit_line'] = True
        if object_id:
            obj = collection_management_ScPombeStrain.objects.get(pk=object_id)
            if obj:
                if not (request.user.is_superuser or request.user.groups.filter(name='Lab manager').exists() or request.user == obj.created_by) or request.user.groups.filter(name='Guest').exists():
                    extra_context['show_submit_line'] = False
        return super(ScPombeStrainPage, self).changeform_view(request, object_id, extra_context=extra_context)

my_admin_site.register(collection_management_ScPombeStrain, ScPombeStrainPage)

#################################################
#                NZ PLASMID PAGES               #
#################################################

from .models import NzPlasmid as collection_management_NzPlasmid

class NzPlasmidQLSchema(DjangoQLSchema):
    '''Customize search functionality'''
    
    include = (collection_management_NzPlasmid, User) # Include only the relevant models to be searched

    def get_fields(self, model):
        '''Define fields that can be searched'''
        
        if model == collection_management_NzPlasmid:
            return ['id', 'name', 'other_name', 'parent_vector', 'selection', 'us_e', 'construction_feature', 'received_from', 'note', 
                'reference', 'created_by',]
        elif model == User:
            return [SearchFieldOptUsername(), SearchFieldOptLastname()]
        return super(NzPlasmidQLSchema, self).get_fields(model)

# class NzPlasmidCustomForm(forms.ModelForm):
#     class Meta:
#         model = collection_management_NzPlasmid
#         fields = '__all__'

#     def __init__(self, *args, **kwargs):
#         super(NzPlasmidCustomForm, self).__init__(*args, **kwargs)
#         self.fields['created_by'].queryset = self.fields['created_by'].queryset.exclude(id__in=[1,20]).order_by("last_name")                                            

class NzPlasmidPage(ExportActionModelAdmin, DjangoQLSearchMixin, SimpleHistoryWithSymmaryAdmin, admin.ModelAdmin, Approval):
    list_display = ('id', 'name', 'selection', 'get_plasmidmap_short_name','created_by', 'approval')
    list_display_links = ('id', )
    list_per_page = 25
    formfield_overrides = {models.CharField: {'widget': TextInput(attrs={'size':'93'})},}
    djangoql_schema = NzPlasmidQLSchema
    # form = NzPlasmidCustomForm
    
    def save_model(self, request, obj, form, change):
        '''Override default save_model to limit a user's ability to save a record
        Superusers and lab managers can change all records
        Regular users can change only their own records
        Guests cannot change any record'''

        if obj.pk == None:
            obj.created_by = request.user
            obj.save()
        else:
            if request.user.is_superuser or request.user == collection_management_NzPlasmid.objects.get(pk=obj.pk).created_by or request.user.groups.filter(name='Lab manager').exists():
                obj.last_changed_approval_by_pi = False
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
            if not (request.user.is_superuser or request.user.groups.filter(name='Lab manager').exists() or request.user == obj.created_by) or request.user.groups.filter(name='Guest').exists():
                return ['name', 'other_name', 'parent_vector', 'selection', 'us_e', 'construction_feature', 'received_from', 'note', 
                'reference', 'plasmid_map', 'created_date_time', 'created_approval_by_pi', 'last_changed_date_time',
                'last_changed_approval_by_pi', 'created_by',]
            else:
                return ['created_date_time', 'created_approval_by_pi', 'last_changed_date_time', 'last_changed_approval_by_pi',]
        else:
            return ['created_date_time', 'created_approval_by_pi', 'last_changed_date_time', 'last_changed_approval_by_pi',]
    
    def add_view(self,request,extra_content=None):
        '''Override default add_view to show only desired fields'''
        
        self.fields = ('name', 'other_name', 'parent_vector', 'selection', 'us_e', 'construction_feature', 'received_from', 'note', 
                'reference', 'plasmid_map',)
        return super(NzPlasmidPage,self).add_view(request)

    def change_view(self,request,object_id,extra_content=None):
        '''Override default change_view to show only desired fields'''
        
        self.fields = ('name', 'other_name', 'parent_vector', 'selection', 'us_e', 'construction_feature', 'received_from', 'note', 
                'reference', 'plasmid_map', 'created_date_time', 'created_approval_by_pi', 'last_changed_date_time',
                'last_changed_approval_by_pi', 'created_by',)
        return super(NzPlasmidPage,self).change_view(request,object_id)

    def changeform_view(self, request, object_id=None, form_url='', extra_context=None):
        """Override default changeform_view to hide Save buttons when certain conditions (same as
        those in get_readonly_fields method) are met"""

        extra_context = extra_context or {}
        extra_context['show_submit_line'] = True
        if object_id:
            obj = collection_management_NzPlasmid.objects.get(pk=object_id)
            if obj:
                if not (request.user.is_superuser or request.user.groups.filter(name='Lab manager').exists() or request.user == obj.created_by) or request.user.groups.filter(name='Guest').exists():
                    extra_context['show_submit_line'] = False
        return super(NzPlasmidPage, self).changeform_view(request, object_id, extra_context=extra_context)

    def get_plasmidmap_short_name(self, instance):
        '''This function allows you to define a custom field for the list view to
        be defined in list_display as the name of the function, e.g. in this case
        list_display = ('id', 'name', 'selection', 'get_plasmidmap_short_name','created_by',)'''
        if instance.plasmid_map:
            plasmid_name_for_download = "pNZ" + str(instance.pk) + " - " + str(instance.name) + "." + str(instance.plasmid_map).split(".")[-1]
            return '<a href="%s" download="%s">Download</a>' % (str(instance.plasmid_map.url), plasmid_name_for_download)
        else:
            return ''
    get_plasmidmap_short_name.allow_tags = True
    get_plasmidmap_short_name.short_description = 'Plasmid map'

    # Add custom js (or css) files to all pages that belong to this model
    class Media:
        js = ('admin/js/vendor/jquery/jquery.js',
        'admin/js/admin/ChangeDownloadLink.js',)

my_admin_site.register(collection_management_NzPlasmid, NzPlasmidPage)

#################################################
#              E. COLI STRAIN PAGES             #
#################################################

from .models import EColiStrain as collection_management_EColiStrain

class EColiStrainQLSchema(DjangoQLSchema):
    '''Customize search functionality'''
    
    include = (collection_management_EColiStrain, User) # Include only the relevant models to be searched

    def get_fields(self, model):
        '''Define fields that can be searched'''
        
        if model == collection_management_EColiStrain:
            return ['id', 'name', 'resistance', 'genotype', 'supplier', 'us_e', 'purpose', 'note', 'created_by',]
        elif model == User:
            return [SearchFieldOptUsername(), SearchFieldOptLastname()]
        return super(EColiStrainQLSchema, self).get_fields(model)

class EColiStrainPage(ExportActionModelAdmin, DjangoQLSearchMixin, SimpleHistoryWithSymmaryAdmin, admin.ModelAdmin, Approval):
    list_display = ('id', 'name', 'resistance', 'us_e','purpose', 'approval')
    list_display_links = ('id', )
    list_per_page = 25
    formfield_overrides = {models.CharField: {'widget': TextInput(attrs={'size':'93'})},}
    djangoql_schema = EColiStrainQLSchema
    
    def save_model(self, request, obj, form, change):
        '''Override default save_model to limit a user's ability to save a record
        Superusers and lab managers can change all records
        Regular users can change only their own records
        Guests cannot change any record'''

        if obj.pk == None:
            obj.created_by = request.user
            obj.save()
        else:
            if request.user.is_superuser or request.user == collection_management_EColiStrain.objects.get(pk=obj.pk).created_by or request.user.groups.filter(name='Lab manager').exists():
                obj.last_changed_approval_by_pi = False
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
            if not (request.user.is_superuser or request.user.groups.filter(name='Lab manager').exists() or request.user == obj.created_by) or request.user.groups.filter(name='Guest').exists():
                return ['name', 'resistance', 'genotype', 'supplier', 'us_e', 'purpose', 'note',
                'created_date_time', 'created_approval_by_pi', 'last_changed_date_time', 'last_changed_approval_by_pi', 'created_by',]
            else:
                return ['created_date_time', 'created_approval_by_pi', 'last_changed_date_time', 'last_changed_approval_by_pi',]
        else:
            return ['created_date_time', 'created_approval_by_pi', 'last_changed_date_time', 'last_changed_approval_by_pi',]
    
    def add_view(self,request,extra_content=None):
        '''Override default add_view to show only desired fields'''

        self.fields = ('name', 'resistance', 'genotype', 'supplier', 'us_e', 'purpose', 'note',)
        return super(EColiStrainPage,self).add_view(request)

    def change_view(self,request,object_id,extra_content=None):
        '''Override default change_view to show only desired fields'''

        self.fields = ('name', 'resistance', 'genotype', 'supplier', 'us_e', 'purpose', 'note',
                'created_date_time', 'created_approval_by_pi', 'last_changed_date_time',
                'last_changed_approval_by_pi', 'created_by',)
        return super(EColiStrainPage,self).change_view(request,object_id)
    
    def changeform_view(self, request, object_id=None, form_url='', extra_context=None):
        """Override default changeform_view to hide Save buttons when certain conditions (same as
        those in get_readonly_fields method) are met"""

        extra_context = extra_context or {}
        extra_context['show_submit_line'] = True
        if object_id:
            obj = collection_management_EColiStrain.objects.get(pk=object_id)
            if obj:
                if not (request.user.is_superuser or request.user.groups.filter(name='Lab manager').exists() or request.user == obj.created_by) or request.user.groups.filter(name='Guest').exists():
                    extra_context['show_submit_line'] = False
        return super(EColiStrainPage, self).changeform_view(request, object_id, extra_context=extra_context)

my_admin_site.register(collection_management_EColiStrain, EColiStrainPage)

#################################################
#           MAMMALIAN LINE DOC                  #
#################################################

from .models import MammalianLineDoc as collection_management_MammalianLineDoc
from .models import MammalianLine as collection_management_MammalianLine

class MammalianLinePageDoc(admin.ModelAdmin):
    list_display = ('id','name',)
    list_display_links = ('id','name', )
    list_per_page = 25
    ordering = ['id']

    def has_module_permission(self, request):
        '''Hide module from Admin'''
        return False

    def get_readonly_fields(self, request, obj=None):
        '''Override default get_readonly_fields to define user-specific read-only fields
        If a user is not a superuser, lab manager or the user who created a record
        return all fields as read-only 
        'created_date_time' and 'last_changed_date_time' fields must always be read-only
        because their set by Django itself'''

        if obj:
            return ['name', 'typ_e', 'date_of_test', 'mammalian_line', 'created_date_time',]
    
    def add_view(self,request,extra_content=None):
        '''Override default add_view to show only desired fields'''

        self.fields = (['name', 'typ_e', 'mammalian_line', 'date_of_test',])
        return super(MammalianLinePageDoc,self).add_view(request)

    def change_view(self,request,object_id,extra_content=None):
        '''Override default change_view to show only desired fields'''

        self.fields = (['name', 'typ_e', 'date_of_test', 'mammalian_line','created_date_time',])
        return super(MammalianLinePageDoc,self).change_view(request,object_id)

    def changeform_view(self, request, object_id=None, form_url='', extra_context=None):
        extra_context = extra_context or {}
        extra_context['show_submit_line'] = True
        if object_id:
            extra_context['show_submit_line'] = False
        return super(MammalianLinePageDoc, self).changeform_view(request, object_id, extra_context=extra_context)

my_admin_site.register(collection_management_MammalianLineDoc, MammalianLinePageDoc)

class MammalianLineDocInline(admin.TabularInline):
    model = collection_management_MammalianLineDoc
    verbose_name_plural = "Exsiting docs"
    extra = 0
    fields = ['typ_e', 'date_of_test', 'get_doc_short_name',]
    readonly_fields = ['get_doc_short_name', 'typ_e', 'date_of_test', ]

    def has_add_permission(self, request):
        return False
    
    def get_doc_short_name(self, instance):
        '''This function allows you to define a custom field for the list view to
        be defined in list_display as the name of the function, e.g. in this case
        list_display = ('id', 'name', 'selection', 'get_plasmidmap_short_name','created_by',)'''
        if instance.name:
            name_for_download = "mclHU" + str(collection_management_MammalianLine.objects.get(mammalianlinedoc=instance.pk)) + "_" + instance.typ_e + "_" + str(instance.date_of_test) +  str(instance.name).split(".")[-1]
            return '<a href="%s" download="%s">Download</a>' % (str(instance.name.url), name_for_download)
        else:
            return ''
    get_doc_short_name.allow_tags = True
    get_doc_short_name.short_description = 'Document'

class AddMammalianLineDocInline(admin.TabularInline):
    model = collection_management_MammalianLineDoc
    verbose_name_plural = "New docs"
    extra = 0
    fields = ['typ_e', 'date_of_test', 'name',]

    def has_change_permission(self, request, obj=None):
        return False

    def get_readonly_fields(self, request, obj=None):
        '''Override default get_readonly_fields to define user-specific read-only fields
        If a user is not a superuser, lab manager or the user who created a record
        return all fields as read-only 
        'created_date_time' and 'last_changed_date_time' fields must always be read-only
        because their set by Django itself'''

        if obj:
            if not (request.user.is_superuser or request.user.groups.filter(name='Lab manager').exists() or request.user == collection_management_MammalianLine.objects.get(pk=obj.pk).created_by) or request.user.groups.filter(name='Guest').exists():
                return ['typ_e', 'date_of_test', 'name',]
            else:
                return []
        else:
            return []

#################################################
#          MAMMALIAN CELL LINE PAGES            #
#################################################

class MammalianLineQLSchema(DjangoQLSchema):
    '''Customize search functionality'''
    
    include = (collection_management_MammalianLine, User) # Include only the relevant models to be searched

    def get_fields(self, model):
        '''Define fields that can be searched'''
        
        if model == collection_management_MammalianLine:
            return ['id', 'name', 'box_name', 'alternative_name', 'parental_line', 'organism', 'cell_type_tissue', 'culture_type', 
            'growth_condition','freezing_medium', 'received_from', 'description_comment', 'created_by',]
        elif model == User:
            return [SearchFieldOptUsername(), SearchFieldOptLastname()]
        return super(MammalianLineQLSchema, self).get_fields(model)

class MammalianLinePage(ExportActionModelAdmin, DjangoQLSearchMixin, SimpleHistoryWithSymmaryAdmin, admin.ModelAdmin, Approval):
    list_display = ('id', 'name', 'box_name', 'created_by', 'approval')
    list_display_links = ('id', )
    list_per_page = 25
    formfield_overrides = {models.CharField: {'widget': TextInput(attrs={'size':'93'})},}
    djangoql_schema = MammalianLineQLSchema
    inlines = [MammalianLineDocInline, AddMammalianLineDocInline]
    
    def save_model(self, request, obj, form, change):
        '''Override default save_model to limit a user's ability to save a record
        Superusers and lab managers can change all records
        Regular users can change only their own records
        Guests cannot change any record'''

        if obj.pk == None:
            obj.created_by = request.user
            obj.save()
        else:
            if request.user.is_superuser or request.user == collection_management_MammalianLine.objects.get(pk=obj.pk).created_by or request.user.groups.filter(name='Lab manager').exists():
                obj.last_changed_approval_by_pi = False
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
            if not (request.user.is_superuser or request.user.groups.filter(name='Lab manager').exists() or request.user == obj.created_by) or request.user.groups.filter(name='Guest').exists():
                return ['name', 'box_name', 'alternative_name', 'parental_line', 'organism', 'cell_type_tissue', 'culture_type', 'growth_condition',
                'freezing_medium', 'received_from', 'description_comment', 'created_date_time', 'created_approval_by_pi',
                'last_changed_date_time', 'last_changed_approval_by_pi', 'created_by',]
            else:
                return ['created_date_time', 'created_approval_by_pi', 'last_changed_date_time', 'last_changed_approval_by_pi',]
        else:
            return ['created_date_time', 'created_approval_by_pi', 'last_changed_date_time', 'last_changed_approval_by_pi',]
    
    def add_view(self,request,extra_content=None):
        '''Override default add_view to show only desired fields'''

        self.fields = ('name', 'box_name', 'alternative_name', 'parental_line', 'organism', 'cell_type_tissue', 'culture_type', 'growth_condition',
                'freezing_medium', 'received_from', 'description_comment',)
        return super(MammalianLinePage,self).add_view(request)

    def change_view(self,request,object_id,extra_content=None):
        '''Override default change_view to show only desired fields'''

        self.fields = ('name', 'box_name', 'alternative_name', 'parental_line', 'organism', 'cell_type_tissue', 'culture_type', 'growth_condition',
                'freezing_medium', 'received_from', 'description_comment', 'created_date_time', 'created_approval_by_pi',
                'last_changed_date_time', 'last_changed_approval_by_pi', 'created_by',)
        return super(MammalianLinePage,self).change_view(request,object_id)

    def changeform_view(self, request, object_id=None, form_url='', extra_context=None):
        extra_context = extra_context or {}
        extra_context['show_submit_line'] = True
        if object_id:
            obj = collection_management_MammalianLine.objects.get(pk=object_id)
            if obj:
                if not (request.user.is_superuser or request.user.groups.filter(name='Lab manager').exists() or request.user == obj.created_by) or request.user.groups.filter(name='Guest').exists():
                    extra_context['show_submit_line'] = False
        return super(MammalianLinePage, self).changeform_view(request, object_id, extra_context=extra_context)

    def get_formsets_with_inlines(self, request, obj=None):
        """Remove AddMammalianLineDocInline from add/change form if user who
        created a MammalianCellLine object is not the request user a lab manager
        or a superuser"""
        
        if obj:
            for inline in self.get_inline_instances(request, obj):
                if inline.verbose_name_plural == 'Exsiting docs':
                    yield inline.get_formset(request, obj), inline
                else:
                    if request.user == collection_management_MammalianLine.objects.get(pk=obj.pk).created_by or request.user.is_superuser or request.user.groups.filter(name='Lab manager').exists():
                        yield inline.get_formset(request, obj), inline
        else:
            for inline in self.get_inline_instances(request, obj):
                yield inline.get_formset(request, obj), inline

my_admin_site.register(collection_management_MammalianLine, MammalianLinePage)

#################################################
#                ANTIBODY PAGES                 #
#################################################

from .models import Antibody as collection_management_Antibody

class AntibodyQLSchema(DjangoQLSchema):
    '''Customize search functionality'''
    
    include = (collection_management_Antibody, User) # Include only the relevant models to be searched

    def get_fields(self, model):
        '''Define fields that can be searched'''
        
        if model == collection_management_Antibody:
            return ['id', 'name', 'species_isotype', 'clone', 'received_from', 'catalogue_number', 'info_sheet',
                'l_ocation', 'a_pplication', 'description_comment','info_sheet', 'created_by', 'arche_noah_choice',]
        elif model == User:
            return [SearchFieldOptUsername(), SearchFieldOptLastname()]
        return super(AntibodyQLSchema, self).get_fields(model)
        
class AntibodyPage(ExportActionModelAdmin, DjangoQLSearchMixin, SimpleHistoryWithSymmaryAdmin, admin.ModelAdmin):
    list_display = ('id', 'name', 'catalogue_number', 'species_isotype', 'clone', 'l_ocation', 'get_sheet_short_name')
    list_display_links = ('id', )
    list_per_page = 25
    #ordering = ('name',)
    formfield_overrides = {models.CharField: {'widget': TextInput(attrs={'size':'93'})},}
    djangoql_schema = AntibodyQLSchema
    
    def save_model(self, request, obj, form, change):
        '''Override default save_model to limit a user's ability to save a record
        Superusers and lab managers can change all records
        Regular users can change only their own records
        Guests cannot change any record'''

        if obj.pk == None:
            obj.created_by = request.user
            obj.save()
        else:
            if request.user.groups.filter(name='Guest').exists():
                raise PermissionDenied
            else:
                if obj.arche_noah_choice and not collection_management_ArcheNoahAnimal.objects.filter(object_id=obj.id):
                    arche_noah_obj = collection_management_ArcheNoahAnimal(content_object=obj, object_id=obj.id)
                    arche_noah_obj.save()
                obj.save()
    
    def get_readonly_fields(self, request, obj=None):
        '''Override default get_readonly_fields to define user-specific read-only fields
        If a user is not a superuser, lab manager or the user who created a record
        return all fields as read-only 
        'created_date_time' and 'last_changed_date_time' fields must always be read-only
        because their set by Django itself'''

        if obj:
            if request.user.groups.filter(name='Guest').exists():
                return ['name', 'species_isotype', 'clone', 'received_from', 'catalogue_number', 'info_sheet',
                'l_ocation', 'a_pplication', 'description_comment','info_sheet', 'created_by', 'created_date_time',
                'last_changed_date_time', 'arche_noah_choice',]
            else:
                return ['created_date_time', 'last_changed_date_time',]
        else:
            return ['created_date_time', 'last_changed_date_time',]
    
    def add_view(self,request,extra_content=None):
        '''Override default add_view to show only desired fields'''

        self.fields = ('name', 'species_isotype', 'clone', 'received_from', 'catalogue_number', 'l_ocation', 'a_pplication',
                'description_comment', 'info_sheet', 'arche_noah_choice',)
        return super(AntibodyPage,self).add_view(request)
    
    def change_view(self,request,object_id,extra_content=None):
        '''Override default change_view to show only desired fields'''

        self.fields = ('name', 'species_isotype', 'clone', 'received_from', 'catalogue_number', 'l_ocation', 'a_pplication',
                'description_comment', 'info_sheet','created_date_time','last_changed_date_time', 'arche_noah_choice',)
        return super(AntibodyPage,self).change_view(request,object_id)

    def changeform_view(self, request, object_id=None, form_url='', extra_context=None):
        extra_context = extra_context or {}
        extra_context['show_submit_line'] = True
        if object_id:
            obj = collection_management_Antibody.objects.get(pk=object_id)
            if obj:
                if request.user.groups.filter(name='Guest').exists():
                    extra_context['show_submit_line'] = False
        return super(AntibodyPage, self).changeform_view(request, object_id, extra_context=extra_context)

    def get_sheet_short_name(self, instance):
        '''Create custom column for information sheet
        It formats a html element a for the information sheet
        such that the text shown for a link is always View'''

        if instance.info_sheet:
            download_link = '/uploads/' + str(instance.info_sheet)
            return '<a href="%s">%s</a>' % (download_link, 'View')
        else:
            return ''
    get_sheet_short_name.allow_tags = True # needed to show output of get_sheet_short_name as html and not simple text
    get_sheet_short_name.short_description = 'Info Sheet'

    # Add custom js (or css) files to all pages that belong to this model
    class Media:
        js = ('admin/js/vendor/jquery/jquery.js',
        'admin/js/admin/ChangeDownloadLink.js',)

my_admin_site.register(collection_management_Antibody, AntibodyPage)

#################################################
#              ARCHE NOAH PAGES                 #
#################################################

class ArcheNoahAnimalPage(admin.ModelAdmin):
    list_display = ('content_type', 'object_id',)
    list_display_links = ('object_id', )
    ordering = ('content_type', 'object_id',)
    list_per_page = 25
    
my_admin_site.register(collection_management_ArcheNoahAnimal, ArcheNoahAnimalPage)

#################################################
#          LABORATORY MANAGEMENT PAGES          #
#################################################

from laboratory_management.models import Category as laboratory_management_Category
from laboratory_management.models import Url as laboratory_management_Url

from laboratory_management.admin import CategoryPage as laboratory_management_CategoryPage
from laboratory_management.admin import UrlPage as laboratory_management_UrlPage

my_admin_site.register(laboratory_management_Category, laboratory_management_CategoryPage)
my_admin_site.register(laboratory_management_Url, laboratory_management_UrlPage)

#################################################
#             ORDER MANAGEMENT PAGES            #
#################################################

from order_management.models import CostUnit as order_CostUnit
from order_management.models import Location as order_Location
from order_management.models import Order as order_management_Order

from order_management.admin import CostUnitPage as laboratory_management_CostUnitPage
from order_management.admin import LocationPage as laboratory_management_LocationPage
from order_management.admin import OrderPage as laboratory_management_OrderPage

my_admin_site.register(order_management_Order, laboratory_management_OrderPage)
my_admin_site.register(order_CostUnit, laboratory_management_CostUnitPage)
my_admin_site.register(order_Location, laboratory_management_LocationPage)

#################################################
#            CUSTOM USER/GROUP PAGES            #
#################################################

my_admin_site.register(Group, GroupAdmin)
my_admin_site.register(User, UserAdmin)

from user_management.models import LabUser as user_management_LabUser

from user_management.admin import LabUserAdmin as user_management_LabUserAdmin

my_admin_site.unregister(User)
my_admin_site.register(User, user_management_LabUserAdmin)

#################################################
#                PROTOCOL PAGES                 #
#################################################

from pages.models import Protocol as pages_Protocol
from pages.models import Recipe as pages_Recipe
from pages.models import Tag as pages_Tag

from pages.admin import ProtocolPage as pages_ProtocolPage
from pages.admin import RecipePage as pages_RecipePage
from pages.admin import TagPage as pages_TagPage

my_admin_site.register(pages_Protocol, pages_ProtocolPage)
my_admin_site.register(pages_Recipe, pages_RecipePage)
my_admin_site.register(pages_Tag, pages_TagPage)