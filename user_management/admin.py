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
    inlines= (LabUserInline,)
    critical_groups = None
    
    def save_model(self, request, obj, form, change):
        
        # Set is_active and is_staff to True for newly created users
        if obj.pk == None:
            obj.is_active = True
            obj.is_staff = True
            obj.save()
            LabUser.objects.create(user=obj)
        else:
            
            # If somebody tries to save a user for which it cannot see some of its groups,
            # save these groups to critical_groups and add them back to the user in save_related
            if request.user.is_superuser or request.user.labuser.is_principal_investigator:
                self.critical_groups = []
            else:
                old_user = User.objects.get(id=obj.pk)
                critical_groups = old_user.groups.exclude(name__in=['Guest', 'Regular lab member', 'Order manager', 'Lab manager'])
                self.critical_groups = list(critical_groups)
            
            obj.save()

        # If is_principal_investigator is True check whether a principal_investigator already exists
        # and if so set the field to False
        if obj.labuser.is_principal_investigator:
            if User.objects.filter(labuser__is_principal_investigator=True).exists():
                obj.labuser.is_principal_investigator = False
                obj.save()

    def save_related(self, request, form, formsets, change):

        '''If somebody tries to save a user for which it cannot see some of its groups,
        get these groups from critical_groups and add them back to the user'''
        
        super(LabUserAdmin, self).save_related(request, form, formsets, change)

        if self.critical_groups:
            obj = User.objects.get(pk=form.instance.id)
            for g in self.critical_groups:
                obj.groups.add(g)
    
    def get_readonly_fields(self, request, obj=None):
        '''Override default get_readonly_fields to define user-specific read-only fields'''
        
        if obj:
            if request.user.is_superuser or request.user.labuser.is_principal_investigator:
                return []
            else:
                if obj.is_superuser or obj.labuser.is_principal_investigator:
                    return ['groups', 'user_permissions', 'is_active', 'is_staff', 'username', 'password',
                            'first_name', 'last_name', 'email', 'is_superuser', 'username']
                else:
                    return []
        else:
            return []

    def change_view(self,request,object_id,extra_context=None):
        '''Override default change_view to show only desired fields'''
        
        extra_context = extra_context or {}

        if request.user.is_superuser or request.user.labuser.is_principal_investigator:
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

    def get_formsets_with_inlines(self, request, obj=None):
        """Show is_principal_investigator inline only for superusers"""

        if request.user.is_superuser and obj:
            for inline in self.get_inline_instances(request, obj):
                yield inline.get_formset(request, obj), inline

    def get_queryset(self, request):
        
        # Show superusers only for superusers
        # Also do not show AnonymousUser

        qs = super(LabUserAdmin, self).get_queryset(request)
        
        if not request.user.is_superuser:
            return qs.exclude(is_superuser=True).exclude(username='AnonymousUser')
        else:
            return qs.exclude(username='AnonymousUser')

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

    def formfield_for_manytomany(self, db_field, request, **kwargs):
        '''Show important groups only to superusers and principal investigators'''

        from django.contrib.auth.models import Group

        if db_field.name == "groups":
            if request.user.is_superuser or request.user.labuser.is_principal_investigator:
                kwargs["queryset"] =  Group.objects.all()
            else:
                kwargs["queryset"] = Group.objects.filter(name__in=['Guest', 'Regular lab member', 'Order manager', 'Lab manager'])
        return super(LabUserAdmin, self).formfield_for_manytomany(db_field, request, **kwargs)