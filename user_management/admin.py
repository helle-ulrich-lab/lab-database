# -*- coding: utf-8 -*-

from __future__ import unicode_literals

#################################################
#    DJANGO 'CORE' FUNCTIONALITIES IMPORTS      #
#################################################

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User

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