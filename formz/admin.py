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
from django.db.models import Q
from django.utils.text import capfirst
from django.conf.urls import url
from django.urls import path
from django.http import Http404
from django.core.exceptions import PermissionDenied
from django.forms import ValidationError
from django.apps import apps
from django.utils.encoding import force_text
from django.shortcuts import render
from django.contrib import messages

from .models import FormZHeader

from formz.models import FormZStorageLocation

from formz.update_zkbs_records import update_zkbs_celllines, update_zkbs_oncogenes, update_zkbs_plasmids

from formz.models import FormZStorageLocation
from formz.models import FormZHeader
from formz.models import ZkbsCellLine

#################################################
#                 FORMZ ADMIN                   #
#################################################

class FormZAdmin(admin.AdminSite):
    
    def get_formz_urls(self):

        urls = [path('<path:object_id>/formz/', self.admin_view(self.formz_view)),
                url(r'^formz/(?P<model_name>.*)/upload_zkbs_excel_file$', self.admin_view(self.upload_zkbs_excel_file_view)),]

        return urls
    
    def formz_view(self, request, *args, **kwargs):
        """View for Formblatt Z form"""
        
        app_label, model_name, obj_id = kwargs['object_id'].split('/')
        model = apps.get_model(app_label, model_name)
        model_content_type = ContentType.objects.get(app_label=app_label, model=model_name)
        opts = model._meta
        obj = model.objects.get(id=int(obj_id))
        
        # Get storage location object or create a new 'empty' one
        if FormZStorageLocation.objects.get(collection_model=model_content_type):
            storage_location = FormZStorageLocation.objects.get(collection_model=model_content_type)
        else:
            storage_location = FormZStorageLocation(
                collection_model = None,
                storage_location = None,
                species_name = None,
                species_risk_group = None
            )

        # Get FormZ header
        if FormZHeader.objects.all().first():
            formz_header = FormZHeader.objects.all().first()
        else:
            formz_header = None

        # Get all sequence elements
        obj.common_formz_elements = obj.get_all_common_formz_elements()
        obj.uncommon_formz_elements =  obj.get_all_uncommon_formz_elements()
        obj.instock_plasmids = obj.get_all_instock_plasmids()
        obj.transient_episomal_plasmids = obj.get_all_transient_episomal_plasmids()

        # If object is a cell line, get info that is specific for cell lines
        # only, such as S2 plasmids and virus packaking line
        if model_name == 'cellline':
            storage_location.species_name = obj.organism
            obj.s2_plasmids = obj.celllineepisomalplasmid_set.all().filter(s2_work_episomal_plasmid=True).distinct().order_by('id')
            try:
                virus_packaging_cell_line = ZkbsCellLine.objects.filter(name__iexact='293T (HEK 293T)').order_by('id')[0]
            except:
                virus_packaging_cell_line = ZkbsCellLine(name = '293T (HEK 293T)')
            transfected = True
        else:
            obj.s2_plasmids = None
            transfected = False
            virus_packaging_cell_line = None

        context = {
        'title': 'FormZ: {}'.format(obj),
        'module_name': capfirst(force_text(opts.verbose_name_plural)),
        'site_header': self.site_header,
        'has_permission': self.has_permission(request),
        'app_label': app_label,
        'opts': opts,
        'site_url': self.site_url, 
        'object': obj,
        'storage_location': storage_location,
        'formz_header': formz_header,
        'transfected': transfected, 
        'virus_packaging_cell_line': virus_packaging_cell_line,}

        return render(request, 'admin/formz/formz.html', context)

    def upload_zkbs_excel_file_view(self, request ,*args, **kwargs):
        """View for form to upload Excel files from ZKBS and update
        database"""

        # Only allow superusers, FormZ or regular managers to access this view
        if not (request.user.is_superuser or request.user.groups.filter(name='FormZ manager').exists() or request.user.groups.filter(name='Lab manager').exists()):
            raise PermissionDenied
        
        # Set link to ZKBS pages for cell lines, oncogenes and plasmids
        allowed_models = {"zkbscellline": "https://zag.bvl.bund.de/zelllinien/index.jsf?dswid=5287&dsrid=51",
                          "zkbsoncogene": "https://zag.bvl.bund.de/onkogene/index.jsf?dswid=5287&dsrid=864",
                          "zkbsplasmid": "https://zag.bvl.bund.de/vektoren/index.jsf?dswid=5287&dsrid=234"}

        # Get model name
        model_name = kwargs['model_name']

        # Check that that the page is rendered only for the models specified above
        if model_name in [m_name for m_name, url in allowed_models.items()]:

            # Set some variables for the admin view
            app_label = 'formz'
            model = apps.get_model(app_label, model_name)
            opts = model._meta
            verbose_model_name_plural = capfirst(force_text(opts.verbose_name_plural))

            file_missing_error = False

            # If the form has been posted
            if request.method == 'POST':

                file_processing_errors = []
                
                # Check that a file is present
                if "file" in request.FILES:

                    # Based on model, call relative function
                    if model_name == "zkbscellline": file_processing_errors = update_zkbs_celllines(request.FILES['file'].file)
                    elif model_name == "zkbsoncogene": file_processing_errors = update_zkbs_oncogenes(request.FILES['file'].file)
                    elif model_name == "zkbsplasmid": file_processing_errors = update_zkbs_plasmids(request.FILES['file'].file)

                    # Collect errors, if any
                    if file_processing_errors:
                        for e in file_processing_errors:
                            messages.error(request, e)
                    else:
                        messages.success(request, "The {} have been updated successfully.".format(verbose_model_name_plural))

                    return HttpResponseRedirect(".")

                else:
                    file_missing_error = True

            context = {
                'title': 'Update ' + verbose_model_name_plural,
                'module_name': verbose_model_name_plural,
                'site_header': self.site_header,
                'has_permission': self.has_permission(request),
                'app_label': app_label,
                'opts': opts,
                'site_url': self.site_url,
                'zkbs_url': allowed_models[model_name],
                'file_missing_error': file_missing_error}
        
            return render(request, 'admin/formz/update_zkbs_records.html', context)

        else:
            raise Http404()

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

        html_str = ''

        for loc in FormZStorageLocation.objects.all().order_by('collection_model__model'):
            model = loc.collection_model.model_class()
            if model.objects.filter(Q(formz_projects__id=instance.id) | Q(formz_projects__parent_project__id=instance.id)).exists():
                html_str = html_str + "<a href='/{}/{}/?q-l=on&q=formz_projects_title+in+{}'>{}</a>".format(
                    loc.collection_model.app_label,
                    loc.collection_model.model,
                    projects,
                    capfirst(model._meta.verbose_name_plural))
        
        html_str = html_str.replace('><', '> | <')
        
        return mark_safe(html_str)
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

        donor_organisms = self.cleaned_data.get('donor_organism', None)
        donor_organisms = donor_organisms.all() if donor_organisms else None
        donor_organisms_names = donor_organisms.values_list('name_for_search', flat=True) if donor_organisms else []

        max_risk_group = donor_organisms.order_by('-risk_group').values_list('risk_group', flat=True).first() if donor_organisms and not (len(donor_organisms_names)==1 and 'none' in donor_organisms_names) else 0

        description = self.cleaned_data.get('description', None)

        if max_risk_group > 1 and not description:
            self.add_error('description', "If the donor organism's risk group is > 1, a description must be provided")

        nuclei_acid_purity = self.cleaned_data.get('nuc_acid_purity', None)

        if nuclei_acid_purity:
            if nuclei_acid_purity.english_name == 'synthetic fragment' and not description:
                self.add_error('description', "If an element is a synthetic fragment, a description must be provided")

        return self.cleaned_data

class FormZBaseElementPage(admin.ModelAdmin):
    
    list_display = ('name', 'get_donor_organism', 'description', 'get_extra_labels')
    list_display_links = ('name', )
    list_per_page = 25
    search_fields = ['name', 'extra_label__label']
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

    def changelist_view(self, request, extra_context=None):
        
        # Check which user is request the page and if Lab Manager, FormZ Manager or superuser
        # show update record button

        extra_context = extra_context or {}

        if request.user.is_superuser or request.user.groups.filter(name='FormZ manager').exists() or request.user.groups.filter(name='Lab manager').exists():
            extra_context["has_update_from_excel_permission"] = True
        else:
            extra_context["has_update_from_excel_permission"] = False
        
        return super(ZkbsPlasmidPage, self).changelist_view(request, extra_context=extra_context)

class ZkbsOncogenePage(admin.ModelAdmin):
    list_display = ('name', 'synonym', 'species', 'risk_potential')
    list_display_links = ('name', )
    list_per_page = 25
    search_fields = ['name']
    ordering = ['name', 'synonym']

    def changelist_view(self, request, extra_context=None):
        
        # Check which user is request the page and if Lab Manager, FormZ Manager or superuser
        # show update record button

        extra_context = extra_context or {}

        if request.user.is_superuser or request.user.groups.filter(name='FormZ manager').exists() or request.user.groups.filter(name='Lab manager').exists():
            extra_context["has_update_from_excel_permission"] = True
        else:
            extra_context["has_update_from_excel_permission"] = False
        
        return super(ZkbsOncogenePage, self).changelist_view(request, extra_context=extra_context)

class ZkbsCellLinePage(admin.ModelAdmin):
    list_display = ('name', 'synonym', 'organism', 'risk_potential', 'origin', 'virus', 'genetically_modified')
    list_display_links = ('name', )
    list_per_page = 25
    search_fields = ['name', 'synonym']
    ordering = ['name']

    def changelist_view(self, request, extra_context=None):
        
        # Check which user is request the page and if Lab Manager, FormZ Manager or superuser
        # show update record button

        extra_context = extra_context or {}

        if request.user.is_superuser or request.user.groups.filter(name='FormZ manager').exists() or request.user.groups.filter(name='Lab manager').exists():
            extra_context["has_update_from_excel_permission"] = True
        else:
            extra_context["has_update_from_excel_permission"] = False
        
        return super(ZkbsCellLinePage, self).changelist_view(request, extra_context=extra_context)

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