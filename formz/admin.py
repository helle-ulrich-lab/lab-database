#################################################
#    DJANGO 'CORE' FUNCTIONALITIES IMPORTS      #
#################################################

from django.contrib import admin
from django.core.exceptions import PermissionDenied
from django.contrib.contenttypes.models import ContentType
from django.utils.safestring import mark_safe
from django.contrib.auth.models import User
from django import forms
from django.http import HttpResponseRedirect
from django.contrib import messages

from .models import FormZHeader

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
from .models import Species
from .models import FormZBaseElement
from .models import FormZBaseElementExtraLabel

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

        return mark_safe("""<a href='{}+{projects}'>Cell lines</a> | 
                            <a href='{}+{projects}'>Plasmids</a> | 
                            <a href='{}+{projects}'>Strains - Sa. cerevisiae</a> | 
                            <a href='{}+{projects}'>Strains - Sc. pombe</a>""".format(
            '/collection_management/cellline/?q-l=on&q=formz_projects_title+in',
            '/collection_management/plasmid/?q-l=on&q=formz_projects_title+in', 
            '/collection_management/sacerevisiaestrain/?q-l=on&q=formz_projects_title+in', 
            '/collection_management/scpombestrain/?q-l=on&q=formz_projects_title+in', 
            projects=projects
            )
            )
    model_search_link.short_description = ''

    def main_project(self, instance):
        return instance.parent_project
    main_project.short_description = 'Main project'

class FormZBaseElementExtraLabelPage(admin.TabularInline):
    model = FormZBaseElementExtraLabel
    verbose_name_plural = mark_safe("aliases <span style='text-transform:none;'>- Must be identical (CASE-SENSITIVE!) to a feature name in a plasmid map for auto-detection to work</span>")
    verbose_name = 'alias'
    ordering = ("label",)
    extra = 0
    template = 'admin/tabular.html'
    min_num = 1

    def get_formset(self, request, obj=None, **kwargs):

        #  Check that the minimum number of aliases is indeed 1
        formset = super().get_formset(request, obj=None, **kwargs)
        formset.validate_min = True
        return formset

class FormZBaseElementForm(forms.ModelForm):
    
    class Meta:
        model = FormZBaseElement
        fields = '__all__'

    def clean(self):

        """Check if description is present for donor_organism_risk > 1"""

        donor_organism = self.cleaned_data.get('donor_organism', None)

        max_risk_group = donor_organism.all().order_by('-risk_group').values_list('risk_group', flat=True).first()
        max_risk_group = max_risk_group if max_risk_group else 0

        description = self.cleaned_data.get('description', None)

        if max_risk_group > 1 and not description:
            self.add_error('description', "If the donor organism's risk group is > 1, a description must be provided")

        nuclei_acid_purity = self.cleaned_data.get('nuc_acid_purity', None)

        if nuclei_acid_purity.english_name == 'synthetic fragment' and not description:
            self.add_error('description', "If an element is a synthetic fragment, a description must be provided")

        return self.cleaned_data

class FormZBaseElementPage(admin.ModelAdmin):
    
    list_display = ('name', 'get_donor_organism', 'description', 'get_extra_labels')
    list_display_links = ('name', )
    list_per_page = 25
    search_fields = ['name']
    ordering = ['name']
    autocomplete_fields = ['zkbs_oncogene', 'donor_organism']
    inlines = [FormZBaseElementExtraLabelPage]
    form = FormZBaseElementForm
    
    def get_extra_labels(self, instance):
        return ', '.join(instance.extra_label.all().values_list('label',flat=True))
    get_extra_labels.short_description = 'aliases'

    def get_donor_organism(self, instance):
        
        species_names = []
        for species in instance.donor_organism.all():
            species_names.append(species.latin_name if species.latin_name else species.common_name)
        return ', '.join(species_names)

    get_donor_organism.short_description = 'donor organism'

class ZkbsPlasmidPage(admin.ModelAdmin):
    list_display = ('name', 'source', 'purpose')
    list_display_links = ('name', )
    list_per_page = 25
    search_fields = ['name']
    ordering = ['name']

class ZkbsOncogenePage(admin.ModelAdmin):
    list_display = ('name', 'synonym', 'species', 'risk_potential')
    list_display_links = ('name', )
    list_per_page = 25
    search_fields = ['name']
    ordering = ['name', 'synonym']

class ZkbsCellLinePage(admin.ModelAdmin):
    list_display = ('name', 'synonym', 'organism', 'risk_potential', 'origin', 'virus', 'genetically_modified')
    list_display_links = ('name', )
    list_per_page = 25
    search_fields = ['name', 'synonym']
    ordering = ['name']

class FormZHeaderPage(admin.ModelAdmin):
    
    list_display = ('operator',)
    list_display_links = ('operator',)
    list_per_page = 25

    def add_view(self,request,extra_context=None):
        
        if FormZHeader.objects.all().exists():
            # Override default add_view to prevent addition of new records, one is enough!
            messages.error(request, 'Nice try, you can only have one header')
            return HttpResponseRedirect("..")
        else:
            return super(FormZHeaderPage,self).add_view(request)

class FormZStorageLocationPage(admin.ModelAdmin):
    
    list_display = ('collection_model', 'storage_location', 'species_name')
    list_display_links = ('collection_model',)
    list_per_page = 25
    autocomplete_fields = ['species_name']

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
                kwargs["queryset"] = ContentType.objects.filter(model__contains='strain').exclude(model__contains='historical').exclude(model__contains='plasmid').exclude(model__contains='summary') | \
                    ContentType.objects.filter(model='plasmid') | \
                    ContentType.objects.filter(model='cellline')

        return super(FormZStorageLocationPage, self).formfield_for_foreignkey(db_field, request, **kwargs)

class SpeciesForm(forms.ModelForm):
    
    class Meta:
        model = Species
        fields = '__all__'

    def clean_latin_name(self):
        
        if not self.instance.pk:
            qs = Species.objects.filter(name_for_search=self.cleaned_data["latin_name"]) 
            
            if 'common_name' in self.cleaned_data.keys():
                qs = qs | Species.objects.filter(name_for_search=self.cleaned_data["common_name"])
            
            if qs:
                raise forms.ValidationError('The name of an organism must be unique')
            else:
                return self.cleaned_data["latin_name"]
        else:
            return self.cleaned_data["latin_name"]

    def clean_common_name(self):
        
        if not self.instance.pk:
            qs = Species.objects.filter(name_for_search=self.cleaned_data["common_name"])
            
            if 'latin_name' in self.cleaned_data.keys():
                qs = qs | Species.objects.filter(name_for_search=self.cleaned_data["latin_name"])
            
            if qs:
                raise forms.ValidationError('The name of an organism must be unique')
            else:
                return self.cleaned_data["common_name"]
        else:
            return self.cleaned_data["common_name"]

class SpeciesPage(admin.ModelAdmin):
    
    list_display = ('species_name', 'risk_group')
    list_display_links = ('species_name',)
    list_per_page = 25
    search_fields = ['name_for_search']
    ordering = ['name_for_search']
    fields = ['latin_name', 'common_name', 'risk_group', 'show_in_cell_line_collection']
    form = SpeciesForm

    def species_name(self, instance):
        return instance.name_for_search
    species_name.short_description = 'organism name'