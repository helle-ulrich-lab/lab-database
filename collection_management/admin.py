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

# Instantiate custom admin site 
my_admin_site = MyAdminSite()

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

class SaCerevisiaeStrainPage(ExportActionModelAdmin, DjangoQLSearchMixin, SimpleHistoryAdmin, admin.ModelAdmin):
    list_display = ('id', 'name', 'mating_type','created_by',)
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
                'us_e', 'note', 'reference','created_date_time', 'last_changed_date_time', 'created_by',]
            else:
                return ['created_date_time', 'last_changed_date_time',]
        else:
            return ['created_date_time', 'last_changed_date_time',]
    
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
        'us_e', 'note', 'reference', 'created_date_time', 'last_changed_date_time', 'created_by',)
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

class HuPlasmidPage(ExportActionModelAdmin, DjangoQLSearchMixin, SimpleHistoryAdmin, admin.ModelAdmin):
    list_display = ('id', 'name', 'selection', 'get_plasmidmap_short_name', 'created_by',)
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
                obj.save()
            else:
                if obj.created_by.id == 6: # Allow saving object, if record belongs to Helle (user id = 6)
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
                'reference', 'plasmid_map', 'created_date_time', 'last_changed_date_time', 'created_by',]
            else:
                if obj.created_by.id == 6: # Show plasmid_map and note as editable fields, if record belongs to Helle (user id = 6)
                    return ['name', 'other_name', 'parent_vector', 'selection', 'us_e', 'construction_feature', 'received_from', 
                    'reference', 'created_date_time', 'last_changed_date_time', 'created_by',]
                else:
                    return ['created_date_time', 'last_changed_date_time',]
        else:
            return ['created_date_time', 'last_changed_date_time',]
    
    def add_view(self,request,extra_content=None):
        '''Override default add_view to show only desired fields'''
        
        self.fields = ('name', 'other_name', 'parent_vector', 'selection', 'us_e', 'construction_feature', 'received_from', 'note', 
                'reference', 'plasmid_map',)
        return super(HuPlasmidPage,self).add_view(request)
    
    def change_view(self,request,object_id,extra_content=None):
        '''Override default change_view to show only desired fields'''
        
        self.fields = ('name', 'other_name', 'parent_vector', 'selection', 'us_e', 'construction_feature', 'received_from', 'note', 
                'reference', 'plasmid_map', 'created_date_time', 'last_changed_date_time', 'created_by',)
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

class OligoPage(ExportActionModelAdmin, DjangoQLSearchMixin, SimpleHistoryAdmin, admin.ModelAdmin):
    list_display = ('id', 'name','sequence', 'restriction_site','created_by')
    list_display_links = ('id',)
    list_per_page = 25
    formfield_overrides = {
    models.CharField: {'widget': TextInput(attrs={'size':'93'})},} # Make TextInput fields wider
    djangoql_schema = OligoQLSchema

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
                return ['name','sequence', 'us_e', 'gene', 'restriction_site', 'description', 'comment', 'created_date_time', 'last_changed_date_time', 'created_by',]
            else:
                return ['created_date_time', 'last_changed_date_time',]
        else:
            return ['created_date_time', 'last_changed_date_time',]
    
    def add_view(self,request,extra_content=None):
        '''Override default add_view to show only desired fields'''
        
        self.fields = ('name','sequence', 'us_e', 'gene', 'restriction_site', 'description', 'comment', )
        return super(OligoPage,self).add_view(request)

    def change_view(self,request,object_id,extra_content=None):
        '''Override default change_view to show only desired fields'''
        
        self.fields = ('name','sequence', 'us_e', 'gene', 'restriction_site', 'description', 'comment', 'created_date_time', 'last_changed_date_time', 'created_by',)
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
            return ['id', 'box_number', 'parental_strain', 'mating_type', 'auxotrophic_marker', 'genotype',
                    'phenotype', 'received_from', 'comment', 'created_by',]
        elif model == User:
            return [SearchFieldOptUsername(), SearchFieldOptLastname()]
        return super(ScPombeStrainQLSchema, self).get_fields(model)

class ScPombeStrainPage(ExportActionModelAdmin, DjangoQLSearchMixin, SimpleHistoryAdmin, admin.ModelAdmin):
    list_display = ('id', 'genotype', 'auxotrophic_marker', 'mating_type',)
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
                obj.save()
            else:
                raise PermissionDenied
    
    def get_readonly_fields(self, request, obj=None):
        '''Override default get_readonly_fields to define user-specific read-only fields
        If a user is not a superuser, lab manager or the user who created a record
        return all fields as read-only 
        'created_date_time' and 'last_changed_date_time' fields must always be read-only
        because their set by Django itself'''
        
        if not (request.user.is_superuser or request.user.groups.filter(name='Lab manager').exists() or request.user == obj.created_by) or request.user.groups.filter(name='Guest').exists():
            if obj:
                return ['box_number', 'parental_strain', 'mating_type', 'auxotrophic_marker', 'genotype',
        'phenotype', 'received_from', 'comment', 'created_date_time', 'last_changed_date_time', 'created_by',]
            else:
                return ['created_date_time', 'last_changed_date_time',]
        else:
            return ['created_date_time', 'last_changed_date_time',]

    def add_view(self,request,extra_content=None):
        '''Override default add_view to show only desired fields'''
        
        self.fields = ('box_number', 'parental_strain', 'mating_type', 'auxotrophic_marker', 'genotype',
        'phenotype', 'received_from', 'comment', )
        return super(ScPombeStrainPage,self).add_view(request)

    def change_view(self,request,object_id,extra_content=None):
        '''Override default change_view to show only desired fields'''
        
        self.fields = ('box_number', 'parental_strain', 'mating_type', 'auxotrophic_marker', 'genotype',
        'phenotype', 'received_from', 'comment', 'created_date_time', 'last_changed_date_time', 'created_by',)
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

class NzPlasmidPage(ExportActionModelAdmin, DjangoQLSearchMixin, SimpleHistoryAdmin, admin.ModelAdmin):
    list_display = ('id', 'name', 'selection', 'get_plasmidmap_short_name','created_by',)
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
                'reference', 'plasmid_map', 'created_date_time', 'last_changed_date_time', 'created_by',]
            else:
                return ['created_date_time', 'last_changed_date_time',]
        else:
            return ['created_date_time', 'last_changed_date_time',]
    
    def add_view(self,request,extra_content=None):
        '''Override default add_view to show only desired fields'''
        
        self.fields = ('name', 'other_name', 'parent_vector', 'selection', 'us_e', 'construction_feature', 'received_from', 'note', 
                'reference', 'plasmid_map',)
        return super(NzPlasmidPage,self).add_view(request)

    def change_view(self,request,object_id,extra_content=None):
        '''Override default change_view to show only desired fields'''
        
        self.fields = ('name', 'other_name', 'parent_vector', 'selection', 'us_e', 'construction_feature', 'received_from', 'note', 
                'reference', 'plasmid_map', 'created_date_time', 'last_changed_date_time', 'created_by',)
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

class EColiStrainPage(ExportActionModelAdmin, DjangoQLSearchMixin, SimpleHistoryAdmin, admin.ModelAdmin):
    list_display = ('id', 'name', 'resistance', 'us_e','purpose')
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
                'created_date_time', 'last_changed_date_time', 'created_by',]
            else:
                return ['created_date_time', 'last_changed_date_time',]
        else:
            return ['created_date_time', 'last_changed_date_time',]
    
    def add_view(self,request,extra_content=None):
        '''Override default add_view to show only desired fields'''

        self.fields = ('name', 'resistance', 'genotype', 'supplier', 'us_e', 'purpose', 'note',)
        return super(EColiStrainPage,self).add_view(request)

    def change_view(self,request,object_id,extra_content=None):
        '''Override default change_view to show only desired fields'''

        self.fields = ('name', 'resistance', 'genotype', 'supplier', 'us_e', 'purpose', 'note',
                'created_date_time', 'last_changed_date_time', 'created_by',)
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
#          MAMMALIAN CELL LINE PAGES            #
#################################################

from .models import MammalianLine as collection_management_MammalianLine

class MammalianLineQLSchema(DjangoQLSchema):
    '''Customize search functionality'''
    
    include = (collection_management_MammalianLine, User) # Include only the relevant models to be searched

    def get_fields(self, model):
        '''Define fields that can be searched'''
        
        if model == collection_management_MammalianLine:
            return ['id', 'name', 'box_name', 'alternative_name', 'organism', 'cell_type_tissue', 'culture_type', 
            'growth_condition','freezing_medium', 'received_from', 'description_comment', 'created_by',]
        elif model == User:
            return [SearchFieldOptUsername(), SearchFieldOptLastname()]
        return super(MammalianLineQLSchema, self).get_fields(model)

class MammalianLinePage(ExportActionModelAdmin, DjangoQLSearchMixin, SimpleHistoryAdmin, admin.ModelAdmin):
    list_display = ('id', 'name', 'box_name', 'created_by')
    list_display_links = ('id', )
    list_per_page = 25
    formfield_overrides = {models.CharField: {'widget': TextInput(attrs={'size':'93'})},}
    djangoql_schema = MammalianLineQLSchema
    
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
                return ['name', 'box_name', 'alternative_name', 'organism', 'cell_type_tissue', 'culture_type', 'growth_condition',
                'freezing_medium', 'received_from', 'description_comment','created_date_time', 'last_changed_date_time', 'created_by',]
            else:
                return ['created_date_time', 'last_changed_date_time',]
        else:
            return ['created_date_time', 'last_changed_date_time',]
    
    def add_view(self,request,extra_content=None):
        '''Override default add_view to show only desired fields'''

        self.fields = ('name', 'box_name', 'alternative_name', 'organism', 'cell_type_tissue', 'culture_type', 'growth_condition',
                'freezing_medium', 'received_from', 'description_comment',)
        return super(MammalianLinePage,self).add_view(request)

    def change_view(self,request,object_id,extra_content=None):
        '''Override default change_view to show only desired fields'''

        self.fields = ('name', 'box_name', 'alternative_name', 'organism', 'cell_type_tissue', 'culture_type', 'growth_condition',
                'freezing_medium', 'received_from', 'description_comment','created_date_time', 'last_changed_date_time', 'created_by',)
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

class AntibodyPage(ExportActionModelAdmin, DjangoQLSearchMixin, SimpleHistoryAdmin, admin.ModelAdmin):
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

        self.fields = ('name', 'species_isotype', 'clone', 'received_from', 'catalogue_number', 'l_ocation', 'a-pplication',
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