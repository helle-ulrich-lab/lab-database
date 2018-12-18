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

class LabUserAdmin(BaseUserAdmin):
    list_display = ('username', 'email', 'first_name', 'last_name', 'is_staff', 'is_active', 'get_user_groups')
    
    def get_user_groups (self, instance):
        """ Pass a user's group membership to a custom column """

        return ', '.join(instance.groups.values_list('name',flat=True))
    get_user_groups.short_description = 'Groups'

    def user_pretty_name(self):
        ''' Create a pretty name for a user to be shown as its unicode attribute'''
        
        if self.first_name:
            pretty_name = self.first_name[0].upper() + '. ' + self.last_name.title()
            return pretty_name
        else:
            return self.username
    User.__str__ = user_pretty_name