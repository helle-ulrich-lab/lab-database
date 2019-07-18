from django.contrib import admin
from django.core.exceptions import PermissionDenied

class NucleicAcidPurityPage(admin.ModelAdmin):
    list_display = ('english_name', 'german_name')
    list_display_links = ('english_name', )
    list_per_page = 25
    ordering = ['english_name']

class NucleicAcidRiskPage(admin.ModelAdmin):
    list_display = ('english_name', 'german_name')
    list_display_links = ('english_name', )
    list_per_page = 25
    ordering = ['english_name']

class GenTechMethodPage(admin.ModelAdmin):
    list_display = ('english_name', 'german_name')
    list_display_links = ('english_name', )
    list_per_page = 25
    ordering = ['english_name']

class FormZProjectPage(admin.ModelAdmin):
    list_display = ('id', 'title')
    list_display_links = ('id', )
    list_per_page = 25
    search_fields = ['id', 'title']

    def has_module_permission(self, request):
        if request.user.groups.filter(name='Lab manager').exists() or request.user.is_superuser:
            return True
        else:
            return False

class FormZBaseElementPage(admin.ModelAdmin):
    list_display = ('id', 'name')
    list_display_links = ('id', )
    list_per_page = 25
    search_fields = ['id', 'name']

    def has_module_permission(self, request):
        if request.user.groups.filter(name='Lab manager').exists() or request.user.is_superuser:
            return True
        else:
            return False

class ZkbsPlasmidPage(admin.ModelAdmin):
    list_display = ('id', 'name', 'source')
    list_display_links = ('id', )
    list_per_page = 25
    search_fields = ['name']

    def has_module_permission(self, request):
        if request.user.groups.filter(name='Lab manager').exists() or request.user.is_superuser:
            return True
        else:
            return False

class FormZHeaderPage(admin.ModelAdmin):
    list_display = ('operator',)
    list_display_links = ('operator',)
    list_per_page = 25

    def add_view(self,request,extra_content=None):
        '''Override default add_view to prevent addition of new records,
        One is enough!'''
        
        raise PermissionDenied