# -*- coding: utf-8 -*-

from __future__ import unicode_literals

from .models import Tag

#################################################
#    DJANGO 'CORE' FUNCTIONALITIES IMPORTS      #
#################################################

from django.contrib import admin
from django.forms import TextInput
from django.db import models

#################################################
#        ADDED FUNCTIONALITIES IMPORTS          #
#################################################

# Advanced search functionalities from DjangoQL
from djangoql.admin import DjangoQLSearchMixin

# Object history tracking from django-simple-history
from simple_history.admin import SimpleHistoryAdmin

# Import/Export functionalities from django-import-export
from import_export.admin import ExportActionModelAdmin

#################################################
#               PROTOCOL PAGES                  #
#################################################

class ProtocolPage(ExportActionModelAdmin, DjangoQLSearchMixin, SimpleHistoryAdmin, admin.ModelAdmin):
    list_display = ('title', 'get_tags')
    list_display_links = ('title', )
    fields = ('title', 'content', 'tags')
    list_per_page = 25
    formfield_overrides = {models.CharField: {'widget': TextInput(attrs={'size':'93'})},}

    def save_model(self, request, obj, form, change): 
        '''Override default save_model to assign object to user who created it'''
        
        if obj.pk == None:
            obj.created_by = request.user
            obj.save()
        else:
            obj.save()

    def get_tags (self, instance):
        """ Pass tags to a custom column """

        return ', '.join(instance.tags.values_list('name',flat=True))
    get_tags.short_description = 'Tags'


class RecipePage(ExportActionModelAdmin, DjangoQLSearchMixin, SimpleHistoryAdmin, admin.ModelAdmin):
    list_display = ('title', 'get_tags')
    list_display_links = ('title', )
    fields = ('title', 'content', 'tags')
    list_per_page = 25
    formfield_overrides = {models.CharField: {'widget': TextInput(attrs={'size':'93'})},}

    def save_model(self, request, obj, form, change): 
        '''Override default save_model to assign object to user who created it'''
        
        if obj.pk == None:
            obj.created_by = request.user
            obj.save()
        else:
            obj.save()

    def get_tags (self, instance):
        """ Pass tags to a custom column """

        return ', '.join(instance.tags.values_list('name',flat=True))
    get_tags.short_description = 'Tags'

class TagPage(ExportActionModelAdmin, DjangoQLSearchMixin, SimpleHistoryAdmin, admin.ModelAdmin):
    list_display = ('name',)
    list_display_links = ('name', )
    list_per_page = 25
    formfield_overrides = {models.CharField: {'widget': TextInput(attrs={'size':'93'})},}