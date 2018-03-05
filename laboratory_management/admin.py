# -*- coding: utf-8 -*-

from __future__ import unicode_literals

#################################################
#    DJANGO 'CORE' FUNCTIONALITIES IMPORTS      #
#################################################

from django.contrib import admin
from django.core.exceptions import PermissionDenied

#################################################
#           LAB MANAGEMENT URL PAGES            #
#################################################

class UrlPage(admin.ModelAdmin):
    list_display = ('id','title','url','category','editable', 'created_by',)
    list_display_links = ('id','title', )
    list_per_page = 25
    ordering = ['id']
    
    def save_model(self, request, obj, form, change):
        '''Override default save_model to limit a user's ability to save a record
        Superusers and lab managers can change all records
        Regular users can change only their own records
        Guests cannot change any record'''

        if obj.pk == None:
            obj.created_by = request.user
            obj.save()
        else:
            if request.user.is_superuser or request.user == obj.created_by or request.user.groups.filter(name='Lab manager').exists():
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
            if not (request.user.is_superuser or request.user.groups.filter(name='Lab manager').exists() or request.user == obj.created_by):
                return ['title', 'url', 'editable', 'category', 'created_by',]
            else:
                return ['created_date_time', 'last_changed_date_time',]
        else:
            return ['created_date_time', 'last_changed_date_time',]
    
    def add_view(self,request,extra_content=None):
        '''Override default add_view to show only desired fields'''

        self.fields = ('title', 'url', 'category', 'editable',)
        return super(UrlPage,self).add_view(request)

    def change_view(self,request,object_id,extra_content=None):
        '''Override default change_view to show only desired fields'''

        self.fields = ('title', 'url', 'category', 'editable',)
        return super(UrlPage,self).change_view(request,object_id)

#################################################
#         LAB MANAGEMENT CATEGORY PAGES         #
#################################################

class CategoryPage(admin.ModelAdmin):
    list_display = ('id','name','colour', 'created_by',)
    list_display_links = ('id','name', )
    list_per_page = 25
    ordering = ['id']
    
    def save_model(self, request, obj, form, change):
        '''Override default save_model to limit a user's ability to save a record
        Superusers and lab managers can change all records
        Regular users can change only their own records
        Guests cannot change any record'''

        if obj.pk == None:
            obj.created_by = request.user
            obj.save()
        else:
            if request.user.is_superuser or request.user == obj.created_by or request.user.groups.filter(name='Lab manager').exists():
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
            if not (request.user.is_superuser or request.user.groups.filter(name='Lab manager').exists() or request.user == obj.created_by):
                return ['name', 'colour', 'created_by',]
            else:
                return ['created_date_time', 'last_changed_date_time',]
        else:
            return ['created_date_time', 'last_changed_date_time',]
    
    def add_view(self,request,extra_content=None):
        '''Override default add_view to show only desired fields'''

        self.fields = ('name', 'colour',)
        return super(CategoryPage,self).add_view(request)

    def change_view(self,request,object_id,extra_content=None):
        '''Override default change_view to show only desired fields'''

        self.fields = ('name', 'colour',)
        return super(CategoryPage,self).change_view(request,object_id)