# -*- coding: utf-8 -*-

from __future__ import unicode_literals

#################################################
#    DJANGO 'CORE' FUNCTIONALITIES IMPORTS      #
#################################################

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User
from django.utils.translation import ugettext_lazy as _

#################################################
#       EXTENDED LAB MEMEBER USER INLINES       #
#################################################

from .models import LabUser

class LabUserInline(admin.StackedInline):
    model = LabUser

class LabUserAdmin(BaseUserAdmin):
    list_display = ('username', 'email', 'first_name', 'last_name', 'is_staff', 'is_active', 'get_user_groups')
    inlines= ()
    
    def save_model(self, request, obj, form, change):
        
        # Set is_active and is_staff to True for newly created users
        if obj.pk == None:
            obj.is_active = True
            obj.is_staff = True
            obj.save()
            LabUser.objects.create(user=obj)
        else:
            obj.save()

        # If is_principal_investigator is True check whether a principal_investigator already exists
        # and if so set the field to False
        if obj.labuser.is_principal_investigator:
            if User.objects.filter(labuser__is_principal_investigator=True):
                obj.labuser.is_principal_investigator = False
                obj.save()

    def change_view(self,request,object_id,extra_context=None):
        '''Override default change_view to show only desired fields'''
        
        extra_context = extra_context or {}

        if request.user.is_superuser:
            self.inlines = (LabUserInline,)
            self.fieldsets = (
                (None, {'fields': ('username', 'password')}),
                (_('Personal info'), {'fields': ('first_name', 'last_name', 'email')}),
                (_('Permissions'), {
                    'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions'),
                })
                )
        else:
            self.fieldsets = (
                (None, {'fields': ('username', 'password')}),
                (_('Personal info'), {'fields': ('first_name', 'last_name', 'email')}),
                (_('Permissions'), {
                    'fields': ('is_active', 'is_staff', 'groups',),
                })
                )

        return super(LabUserAdmin,self).change_view(request,object_id, extra_context=extra_context)
    
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