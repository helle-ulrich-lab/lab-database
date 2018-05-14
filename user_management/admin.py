# -*- coding: utf-8 -*-

from __future__ import unicode_literals

#################################################
#    DJANGO 'CORE' FUNCTIONALITIES IMPORTS      #
#################################################

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User
from django.contrib import messages

#################################################
#        ADDED FUNCTIONALITIES IMPORTS          #
#################################################

import os
import sys

# Google Sheets API to add new orders to Order Master List
import pygsheets

#################################################
#                OTHER IMPORTS                  #
#################################################

from django_project.private_settings import LAB_MEMBERS_SHEET_ID

# Switch from default ASCII to utf-8 encoding, needed for the Google Docs stuff to work
reload(sys)
sys.setdefaultencoding('utf-8')

#################################################
#       EXTENDED LAB MEMEBER USER INLINES       #
#################################################

from .models import LabUser

class LabUserInline(admin.StackedInline):
    model = LabUser
    can_delete = False
    verbose_name_plural = 'Additional Fields'

class LabUserAdmin(BaseUserAdmin):
    inlines = (LabUserInline, )
    list_display = ('username', 'email', 'first_name', 'last_name', 'get_abbreviation_code', 'is_staff', 'is_active', 'get_user_groups')
    
    def get_user_groups (self, instance):
        """ Pass a user's group membership to a custom column """

        return ', '.join(instance.groups.values_list('name',flat=True))
    get_user_groups.short_description = 'Groups'

    def get_abbreviation_code(self, instance):
        ''' Pass a user's abbreviation code to a custom column'''

        return instance.labuser.abbreviation_code
    get_abbreviation_code.short_description = 'User Code'
    
    def user_pretty_name(self):
        ''' Create a pretty name for a user to be shown as its unicode attribute'''
        
        pretty_name = self.first_name[0].upper() + '. ' + self.last_name.title()
        return pretty_name
    User.__unicode__ = user_pretty_name

    actions = ['update_lab_users_google_sheet']

    def update_lab_users_google_sheet (self, request, queryset):
        """ Update active user list sheet on GoogleDocs """
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
        except Exception, err:
            messages.error(request, 'The user list on GoogleDocs could not be updated. Error: ' + str(err))

    update_lab_users_google_sheet.short_description = "Update lab user list on GoogleDocs"