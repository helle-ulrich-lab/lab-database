#################################################
#    DJANGO 'CORE' FUNCTIONALITIES IMPORTS      #
#################################################

from django.contrib import admin
from django.core.exceptions import PermissionDenied
from django.contrib.contenttypes.models import ContentType
from django.utils.safestring import mark_safe
from django.contrib.auth.models import User

#################################################
#             MODEL ADMIN CLASSES               #
#################################################

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
    search_fields = ['english_name']

from .models import FormZProject
from .models import FormZUsers

class FormZUsersInline(admin.TabularInline):
    # autocomplete_fields = ['user']
    model = FormZUsers
    verbose_name_plural = "users"
    verbose_name = 'user'
    extra = 0
    template = 'admin/tabular.html'
    
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        
        # Exclude certain users from the 'User' field

        if db_field.name == 'user':
            kwargs["queryset"] = User.objects.exclude(id__in=[1, 20, 36]).order_by('last_name')
        
        return super(FormZUsersInline, self).formfield_for_foreignkey(db_field, request, **kwargs)

class FormZProjectPage(admin.ModelAdmin):
    
    list_display = ('title', 'short_title_english', 'main_project','model_search_link')
    list_display_links = ('title', )
    list_per_page = 25
    search_fields = ['id', 'short_title']
    autocomplete_fields = ['project_leader'] 

    def get_readonly_fields(self, request, obj=None):
        '''Override default get_readonly_fields to define user-specific read-only fields
        If a user is not a superuser, lab manager or the user who created a record
        return all fields as read-only
        'created_date_time' and 'last_changed_date_time' fields must always be read-only
        because their set by Django itself'''
        
        if obj:
            return ['short_title_english', 'short_title']
        else:
            return []

    def add_view(self,request,extra_context=None):
            
            # Do not show any inlines in add_view

            self.inlines = []

            return super(FormZProjectPage,self).add_view(request)

    def change_view(self,request,object_id,extra_context=None):
        '''Override default change_view to show only desired fields'''

        # Show Users inline only if project has safety level 2 
        if object_id:
            obj = FormZProject.objects.get(pk=object_id)
            if obj:
                if obj.safety_level == 2:
                    self.inlines = [FormZUsersInline]
                else:
                    self.inlines = []

        self.fields = ('title', 'short_title', 'short_title_english', 'parent_project', 'safety_level', 'project_leader', 'objectives',
                       'description', 'donor_organims', 'potential_risk_nuc_acid', 'vectors', 'recipient_organisms', 'generated_gmo', 
                       'hazard_activity', 'hazards_employee', 'beginning_work_date', 'end_work_date',)
        return super(FormZProjectPage,self).change_view(request,object_id)

    def model_search_link(self, instance):
        projects = str(tuple([instance.short_title] + list(FormZProject.objects.filter(parent_project_id=instance.id).values_list('short_title', flat=True)))).replace("'", '"').replace(',)', ')')

        return mark_safe("""<a href='{}+{projects}'>Mammalian cell lines</a> | 
                            <a href='{}+{projects}'>Plasmids</a> | 
                            <a href='{}+{projects}'>Strains - Sa. cerevisiae</a> | 
                            <a href='{}+{projects}'>Strains - Sc. pombe</a>""".format(
            '/collection_management/mammalianline/?q-l=on&q=formz_projects_title+in',
            '/collection_management/huplasmid/?q-l=on&q=formz_projects_title+in', 
            '/collection_management/sacerevisiaestrain/?q-l=on&q=formz_projects_title+in', 
            '/collection_management/scpombestrain/?q-l=on&q=formz_projects_title+in', 
            projects=projects
            )
            )
    model_search_link.short_description = ''

    def main_project(self, instance):
        return instance.parent_project
    main_project.short_description = 'Main project'

from .models import FormZBaseElementExtraLabel

class FormZBaseElementExtraLabelPage(admin.TabularInline):
    model = FormZBaseElementExtraLabel
    verbose_name_plural = "aliases"
    verbose_name = 'alias'
    ordering = ("label",)
    extra = 0
    template = 'admin/tabular.html'

class FormZBaseElementPage(admin.ModelAdmin):
    
    list_display = ('name', 'description', 'donor_organism', 'get_extra_labels')
    list_display_links = ('name', )
    list_per_page = 25
    search_fields = ['name']
    ordering = ['name']
    autocomplete_fields = ['zkbs_oncogene']
    inlines = [FormZBaseElementExtraLabelPage]

    # def has_module_permission(self, request):

    #     # Show this model on the admin home page only for superusers and
    #     # lab managers
    #     if request.user.groups.filter(name='Lab manager').exists() or request.user.is_superuser:
    #         return True
    #     else:
    #         return False
    
    def get_extra_labels(self, instance):
        return ', '.join(instance.extra_label.all().values_list('label',flat=True))
    get_extra_labels.short_description = 'aliases'

class ZkbsPlasmidPage(admin.ModelAdmin):
    list_display = ('name', 'source', 'purpose')
    list_display_links = ('name', )
    list_per_page = 25
    search_fields = ['name']
    ordering = ['name']

    # def has_module_permission(self, request):
        
    #     # Show this model on the admin home page only for superusers and
    #     # lab managers
    #     if request.user.groups.filter(name='Lab manager').exists() or request.user.is_superuser:
    #         return True
    #     else:
    #         return False

class ZkbsOncogenePage(admin.ModelAdmin):
    list_display = ('name', 'synonym', 'species', 'risk_potential')
    list_display_links = ('name', )
    list_per_page = 25
    search_fields = ['name']
    ordering = ['name', 'synonym']

    # def has_module_permission(self, request):
        
    #     # Show this model on the admin home page only for superusers and
    #     # lab managers
    #     if request.user.groups.filter(name='Lab manager').exists() or request.user.is_superuser:
    #         return True
    #     else:
    #         return False

class ZkbsCellLinePage(admin.ModelAdmin):
    list_display = ('name', 'synonym', 'organism', 'risk_potential', 'origin', 'virus', 'genetically_modified')
    list_display_links = ('name', )
    list_per_page = 25
    search_fields = ['name', 'synonym']
    ordering = ['name']

    # def has_module_permission(self, request):
        
    #     # Show this model on the admin home page only for superusers and
    #     # lab managers
    #     if request.user.groups.filter(name='Lab manager').exists() or request.user.is_superuser:
    #         return True
    #     else:
    #         return False

class FormZHeaderPage(admin.ModelAdmin):
    
    list_display = ('operator',)
    list_display_links = ('operator',)
    list_per_page = 25

    def add_view(self,request,extra_content=None):
        
        # Override default add_view to prevent addition of new records, one is enough!
        raise PermissionDenied

class FormZStorageLocationPage(admin.ModelAdmin):
    
    list_display = ('collection_model', 'storage_location', 'species_name')
    list_display_links = ('collection_model',)
    list_per_page = 25

    def has_module_permission(self, request):
        
        # Show this model on the admin home page only for superusers and
        # lab managers
        if request.user.groups.filter(name='Lab manager').exists() or request.user.is_superuser:
            return True
        else:
            return False
    
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        
        try:
            request.resolver_match.args[0]
        except:
            
            # Include only relevant models from collection_management app

            if db_field.name == 'collection_model':
                kwargs["queryset"] = ContentType.objects.filter(id__in=[59,63,67,68])

        return super(FormZStorageLocationPage, self).formfield_for_foreignkey(db_field, request, **kwargs)