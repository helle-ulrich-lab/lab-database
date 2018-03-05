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
    list_display = ('username', 'email', 'first_name', 'last_name', 'get_abbreviation_code', 'is_staff',)
    
    def get_abbreviation_code(self, instance):
        ''' Pass a user's abbreviation code to a custom column'''

        return instance.labuser.abbreviation_code
    get_abbreviation_code.short_description = 'User Code'
    
    def user_pretty_name(self):
        ''' Create a pretty name for a user to be shown as its unicode attribute'''
        
        pretty_name = self.first_name[0].upper() + '. ' + self.last_name.title()
        return pretty_name
    User.__unicode__ = user_pretty_name