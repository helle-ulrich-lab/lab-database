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

def export_as_docx(modeladmin, request, queryset):
    """ Admin adction to export Protocol or Recipe as
    a .docx file
    """
    import pypandoc
    from django_project.settings import MEDIA_ROOT
    from django.http import HttpResponse
    import os
    import string
    from random import choice
    from bs4 import BeautifulSoup
    from django.contrib import messages
    import time

    try:
        allchar = string.ascii_letters + string.punctuation + string.digits

        input_html_text = ''
        for item in queryset:
            input_html_text += '<h1>' + item.title + '</h1>' + item.content
        
        soup = BeautifulSoup(input_html_text, "html.parser")
        for img in soup.findAll('img'):
            img.attrs["src"] = 'http://localhost:8443' + img.attrs["src"]

        file_name = MEDIA_ROOT + "temp/" + "".join(choice(allchar) for x in range(20))
        pypandoc.convert_text(soup, 'docx', format='html', outputfile=file_name,  extra_args=['-V', 'papersize:a4'])
        
        with open (file_name, 'r') as download_file:
            response = HttpResponse(download_file, content_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document')
            response['Content-Disposition'] = 'attachment; filename=pages_' + time.strftime("%Y%m%d") + "_" + time.strftime("%H%M%S") + '.docx'
        os.remove(file_name)
    except Exception as err:
        messages.error(request, "Could not export record. Error: " + str(err))
    if 'response' not in locals():
        response = ''
    return response

export_as_docx.short_description = "Export selected as .docx"

#################################################
#               PROTOCOL PAGES                  #
#################################################

class ProtocolPage(ExportActionModelAdmin, DjangoQLSearchMixin, SimpleHistoryAdmin, admin.ModelAdmin):
    list_display = ('title', 'get_tags')
    list_display_links = ('title', )
    fields = ('title', 'content', 'tags')
    list_per_page = 25
    formfield_overrides = {models.CharField: {'widget': TextInput(attrs={'size':'93'})},}
    actions = [export_as_docx]

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
    actions = [export_as_docx]

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