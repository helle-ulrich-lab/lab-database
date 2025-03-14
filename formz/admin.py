import time

from django import forms
from django.apps import apps
from django.contrib import admin, messages
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import PermissionDenied
from django.db.models import Q
from django.http import Http404, HttpResponse, HttpResponseRedirect
from django.shortcuts import render
from django.urls import path, re_path
from django.utils.encoding import force_str
from django.utils.safestring import mark_safe
from django.utils.text import capfirst
from import_export import resources
from import_export.fields import Field

from .models import (
    Header,
    Project,
    ProjectUser,
    SequenceFeature,
    SequenceFeatureAlias,
    Species,
    StorageLocation,
)
from .update_zkbs_records import (
    update_zkbs_celllines,
    update_zkbs_oncogenes,
    update_zkbs_plasmids,
)

User = get_user_model()


class FormZAdminSite(admin.AdminSite):
    def get_formz_urls(self):
        urls = [
            path("<path:object_id>/formz/", self.admin_view(self.formz_view)),
            re_path(
                r"^formz/(?P<model_name>.*)/upload_zkbs_excel_file$",
                self.admin_view(self.upload_zkbs_excel_file_view),
            ),
        ]

        return urls

    def formz_view(self, request, *args, **kwargs):
        """View for Formblatt Z form"""

        app_label, model_name, obj_id = kwargs["object_id"].split("/")
        model = apps.get_model(app_label, model_name)
        opts = model._meta
        obj = model.objects.get(id=int(obj_id))

        # Get FormZ header
        if Header.objects.all().first():
            formz_header = Header.objects.all().first()
        else:
            formz_header = None

        context = {
            "title": f"FormZ: {obj}",
            "module_name": capfirst(force_str(opts.verbose_name_plural)),
            "site_header": self.site_header,
            "has_permission": self.has_permission(request),
            "app_label": app_label,
            "opts": opts,
            "site_url": self.site_url,
            "object": obj,
            "formz_header": formz_header,
        }

        return render(request, "admin/formz/formz.html", context)

    def upload_zkbs_excel_file_view(self, request, *args, **kwargs):
        """View for form to upload Excel files from ZKBS and update
        database"""

        # Only allow superusers, FormZ or regular managers to access this view
        if not (
            request.user.is_superuser
            or request.user.groups.filter(name="FormZ manager").exists()
            or request.user.groups.filter(name="Lab manager").exists()
        ):
            raise PermissionDenied

        # Set link to ZKBS pages for cell lines, oncogenes and plasmids
        allowed_models = {
            "zkbscellline": "https://zag.bvl.bund.de/zelllinien/index.jsf?dswid=5287&dsrid=51",
            "zkbsoncogene": "https://zag.bvl.bund.de/onkogene/index.jsf?dswid=5287&dsrid=864",
            "zkbsplasmid": "https://zag.bvl.bund.de/vektoren/index.jsf?dswid=5287&dsrid=234",
        }

        # Get model name
        model_name = kwargs["model_name"]

        # Check that that the page is rendered only for the models specified above
        if model_name in [m_name for m_name, url in allowed_models.items()]:
            # Set some variables for the admin view
            app_label = "formz"
            model = apps.get_model(app_label, model_name)
            opts = model._meta
            verbose_model_name_plural = capfirst(force_str(opts.verbose_name_plural))

            file_missing_error = False

            # If the form has been posted
            if request.method == "POST":
                file_processing_errors = []

                # Check that a file is present
                if "file" in request.FILES:
                    # Based on model, call relative function
                    if model_name == "zkbscellline":
                        file_processing_errors = update_zkbs_celllines(
                            request.FILES["file"].file
                        )
                    elif model_name == "zkbsoncogene":
                        file_processing_errors = update_zkbs_oncogenes(
                            request.FILES["file"].file
                        )
                    elif model_name == "zkbsplasmid":
                        file_processing_errors = update_zkbs_plasmids(
                            request.FILES["file"].file
                        )

                    # Collect errors, if any
                    if file_processing_errors:
                        for e in file_processing_errors:
                            messages.error(request, e)
                    else:
                        messages.success(
                            request,
                            "The {} have been updated successfully.".format(
                                verbose_model_name_plural
                            ),
                        )

                    return HttpResponseRedirect(".")

                else:
                    file_missing_error = True

            context = {
                "title": "Update " + verbose_model_name_plural,
                "module_name": verbose_model_name_plural,
                "site_header": self.site_header,
                "has_permission": self.has_permission(request),
                "app_label": app_label,
                "opts": opts,
                "site_url": self.site_url,
                "zkbs_url": allowed_models[model_name],
                "file_missing_error": file_missing_error,
            }

            return render(request, "admin/formz/update_zkbs_records.html", context)

        else:
            raise Http404()


class NucleicAcidPurityAdmin(admin.ModelAdmin):
    list_display = ("english_name", "german_name")
    list_display_links = ("english_name",)
    list_per_page = 25
    ordering = ["english_name"]


class NucleicAcidRiskAdmin(admin.ModelAdmin):
    list_display = ("english_name", "german_name")
    list_display_links = ("english_name",)
    list_per_page = 25
    ordering = ["english_name"]


class GenTechMethodAdmin(admin.ModelAdmin):
    list_display = ("english_name", "german_name")
    list_display_links = ("english_name",)
    list_per_page = 25
    ordering = ["english_name"]
    search_fields = ["english_name"]


class ProjectUserInline(admin.TabularInline):
    # autocomplete_fields = ['user']
    model = ProjectUser
    verbose_name_plural = "users"
    verbose_name = "user"
    extra = 0
    template = "admin/tabular.html"

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        # Exclude certain users from the 'User' field

        if db_field.name == "user":
            kwargs["queryset"] = User.objects.exclude(
                username__in=["admin", "guest", "AnonymousUser"]
            ).order_by("last_name")

        return super().formfield_for_foreignkey(db_field, request, **kwargs)


class ProjectForm(forms.ModelForm):
    def clean(self):
        # For main S2 projects, check whether any information has been added to
        # genetic_work_classification
        if self.cleaned_data.get("safety_level", 0) == 2:
            if not self.cleaned_data.get("parent_project"):
                if not self.cleaned_data.get("genetic_work_classification"):
                    raise forms.ValidationError(
                        {
                            "genetic_work_classification": [
                                "For S2 projects, the classification of genetic work must be provided.",
                            ]
                        }
                    )

        return self.cleaned_data


class ProjectAdmin(admin.ModelAdmin):
    list_display = ("title", "short_title_english", "main_project", "model_search_link")
    list_display_links = ("title",)
    list_per_page = 25
    search_fields = ["id", "short_title"]
    autocomplete_fields = ["project_leader", "deputy_project_leader"]
    form = ProjectForm

    def add_view(self, request, extra_context=None):
        # Do not show any inlines in add_view

        self.inlines = []

        return super().add_view(request)

    def change_view(self, request, object_id, extra_context=None):
        """Override default change_view to show only desired fields"""

        # Show Users inline only if project has safety level 2
        if object_id:
            obj = Project.objects.get(pk=object_id)
            if obj:
                if obj.safety_level == 2:
                    self.inlines = [ProjectUserInline]
                else:
                    self.inlines = []

        self.fields = (
            "title",
            "short_title",
            "short_title_english",
            "parent_project",
            "safety_level",
            "project_leader",
            "deputy_project_leader",
            "objectives",
            "description",
            "donor_organims",
            "potential_risk_nuc_acid",
            "vectors",
            "recipient_organisms",
            "generated_gmo",
            "hazard_activity",
            "hazards_employee",
            "beginning_work_date",
            "end_work_date",
            "genetic_work_classification",
        )
        return super().change_view(request, object_id)

    @admin.display(description="")
    def model_search_link(self, instance):
        projects = (
            str(
                tuple(
                    [instance.short_title]
                    + list(
                        Project.objects.filter(
                            parent_project_id=instance.id
                        ).values_list("short_title", flat=True)
                    )
                )
            )
            .replace("'", '"')
            .replace(",)", ")")
        )

        html_str = ""

        for loc in StorageLocation.objects.all().order_by("collection_model__model"):
            model = loc.collection_model.model_class()
            if model.objects.filter(
                Q(formz_projects__id=instance.id)
                | Q(formz_projects__parent_project__id=instance.id)
            ).exists():
                html_str = (
                    html_str
                    + "<a href='/{}/{}/?q-l=on&q=formz_projects_title+in+{}'>{}</a>".format(
                        loc.collection_model.app_label,
                        loc.collection_model.model,
                        projects,
                        capfirst(model._meta.verbose_name_plural),
                    )
                )

        html_str = html_str.replace("><", "> | <")

        return mark_safe(html_str)

    @admin.display(description="Main project")
    def main_project(self, instance):
        return instance.parent_project


class SequenceFeatureAliasAdmin(admin.TabularInline):
    model = SequenceFeatureAlias
    verbose_name_plural = mark_safe(
        "aliases <span style='text-transform:none;'>- Must be identical (CASE-SENSITIVE!) to a feature name in a plasmid map for auto-detection to work</span>"
    )
    verbose_name = "alias"
    ordering = ("label",)
    extra = 0
    template = "admin/tabular.html"
    min_num = 1

    def get_formset(self, request, obj=None, **kwargs):
        #  Check that the minimum number of aliases is indeed 1
        formset = super().get_formset(request, obj=None, **kwargs)
        formset.validate_min = True
        return formset


class SequenceFeatureForm(forms.ModelForm):
    class Meta:
        model = SequenceFeature
        fields = "__all__"

    def clean(self):
        """Check if description is present for donor_organism_risk > 1"""

        donor_organisms = self.cleaned_data.get("donor_organism", None)
        donor_organisms = donor_organisms.all() if donor_organisms else None
        donor_organisms_names = (
            donor_organisms.values_list("name_for_search", flat=True)
            if donor_organisms
            else []
        )

        max_risk_group = (
            donor_organisms.order_by("-risk_group")
            .values_list("risk_group", flat=True)
            .first()
            if donor_organisms
            and not (
                len(donor_organisms_names) == 1 and "none" in donor_organisms_names
            )
            else 0
        )

        description = self.cleaned_data.get("description", None)

        if max_risk_group > 1 and not description:
            self.add_error(
                "description",
                "If the donor organism's risk group is > 1, a description must be provided",
            )

        nuclei_acid_purity = self.cleaned_data.get("nuc_acid_purity", None)

        if nuclei_acid_purity:
            if (
                nuclei_acid_purity.english_name == "synthetic fragment"
                and not description
            ):
                self.add_error(
                    "description",
                    "If a sequence feature is a synthetic fragment, a description must be provided",
                )

        return self.cleaned_data


class SequenceFeatureResource(resources.ModelResource):
    """Defines a custom export resource class for SequenceFeature"""

    donor_organism_name_rg = Field()
    aliases = Field()

    def dehydrate_donor_organism_name_rg(self, e):
        return ", ".join(
            f"{n} (RG{rg})" if rg else n
            for n, rg in e.donor_organism.values_list("name_for_search", "risk_group")
        )

    def dehydrate_aliases(self, e):
        return ", ".join(e.alias.values_list("label", flat=True))

    class Meta:
        model = SequenceFeature
        fields = (
            "id",
            "name",
            "donor_organism_name_rg",
            "nuc_acid_purity__english_name",
            "nuc_acid_risk__english_name",
            "zkbs_oncogene__name",
            "description",
            "aliases",
        )
        export_order = (
            "id",
            "name",
            "donor_organism_name_rg",
            "nuc_acid_purity__english_name",
            "nuc_acid_risk__english_name",
            "zkbs_oncogene__name",
            "description",
            "aliases",
        )


@admin.action(description="Export selected sequence elements as XLSX")
def export_sequence_features(modeladmin, request, queryset):
    """Export Sequence feature"""

    export_data = SequenceFeatureResource().export(queryset)

    response = HttpResponse(
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    response["Content-Disposition"] = 'attachment; filename="{}_{}_{}.xlsx'.format(
        queryset.model.__name__, time.strftime("%Y%m%d"), time.strftime("%H%M%S")
    )
    response.write(export_data.xlsx)

    return response


class SequenceFeatureAdmin(admin.ModelAdmin):
    list_display = ("name", "get_donor_organism", "description", "get_aliass")
    list_display_links = ("name",)
    list_per_page = 25
    search_fields = ["name", "alias__label"]
    ordering = ["name"]
    autocomplete_fields = ["zkbs_oncogene", "donor_organism"]
    inlines = [SequenceFeatureAliasAdmin]
    form = SequenceFeatureForm
    actions = [export_sequence_features]

    @admin.display(description="aliases")
    def get_aliass(self, instance):
        return ", ".join(instance.alias.all().values_list("label", flat=True))

    @admin.display(description="donor organism")
    def get_donor_organism(self, instance):
        species_names = []
        for species in instance.donor_organism.all():
            species_names.append(
                species.latin_name if species.latin_name else species.common_name
            )
        return ", ".join(species_names)


class ZkbsPlasmidAdmin(admin.ModelAdmin):
    list_display = ("name", "source", "purpose")
    list_display_links = ("name",)
    list_per_page = 25
    search_fields = ["name"]
    ordering = ["name"]

    def changelist_view(self, request, extra_context=None):
        # Check which user is request the page and if Lab Manager, FormZ Manager or superuser
        # show update record button

        extra_context = extra_context or {}

        if (
            request.user.is_superuser
            or request.user.groups.filter(name="FormZ manager").exists()
            or request.user.groups.filter(name="Lab manager").exists()
        ):
            extra_context["has_update_from_excel_permission"] = True
        else:
            extra_context["has_update_from_excel_permission"] = False

        return super().changelist_view(request, extra_context=extra_context)


class ZkbsOncogeneAdmin(admin.ModelAdmin):
    list_display = ("name", "synonym", "species", "risk_potential")
    list_display_links = ("name",)
    list_per_page = 25
    search_fields = ["name"]
    ordering = ["name", "synonym"]

    def changelist_view(self, request, extra_context=None):
        # Check which user is request the page and if Lab Manager, FormZ Manager or superuser
        # show update record button

        extra_context = extra_context or {}

        if (
            request.user.is_superuser
            or request.user.groups.filter(name="FormZ manager").exists()
            or request.user.groups.filter(name="Lab manager").exists()
        ):
            extra_context["has_update_from_excel_permission"] = True
        else:
            extra_context["has_update_from_excel_permission"] = False

        return super().changelist_view(request, extra_context=extra_context)


class ZkbsCellLineAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "synonym",
        "organism",
        "risk_potential",
        "origin",
        "virus",
        "genetically_modified",
    )
    list_display_links = ("name",)
    list_per_page = 25
    search_fields = ["name", "synonym"]
    ordering = ["name"]

    def changelist_view(self, request, extra_context=None):
        # Check which user is request the page and if Lab Manager, FormZ Manager or superuser
        # show update record button

        extra_context = extra_context or {}

        if (
            request.user.is_superuser
            or request.user.groups.filter(name="FormZ manager").exists()
            or request.user.groups.filter(name="Lab manager").exists()
        ):
            extra_context["has_update_from_excel_permission"] = True
        else:
            extra_context["has_update_from_excel_permission"] = False

        return super().changelist_view(request, extra_context=extra_context)


class HeaderAdmin(admin.ModelAdmin):
    list_display = ("operator",)
    list_display_links = ("operator",)
    list_per_page = 25

    def add_view(self, request, extra_context=None):
        if Header.objects.all().exists():
            # Override default add_view to prevent addition of new records, one is enough!
            messages.error(request, "Nice try, you can only have one header")
            return HttpResponseRedirect("..")
        else:
            return super().add_view(request)


class StorageLocationAdmin(admin.ModelAdmin):
    list_display = ("collection_model_prettified", "storage_location", "species")
    list_display_links = ("collection_model_prettified",)
    list_per_page = 25
    autocomplete_fields = ["species"]

    @admin.display(description="Collection")
    def collection_model_prettified(self, instance):
        return str(
            instance.collection_model.model_class()._meta.verbose_name.capitalize()
        )

    def has_module_permission(self, request):
        # Show this model on the admin home page only for superusers and
        # lab managers
        if (
            request.user.groups.filter(name="Lab manager").exists()
            or request.user.is_superuser
        ):
            return True
        else:
            return False

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        try:
            request.resolver_match.args[0]
        except Exception:
            # Include only relevant models from collection app

            if db_field.name == "collection_model":
                kwargs["queryset"] = (
                    ContentType.objects.filter(model__contains="strain")
                    .exclude(model__contains="historical")
                    .exclude(model__contains="plasmid")
                    .exclude(model__contains="summary")
                    | ContentType.objects.filter(model="plasmid")
                    | ContentType.objects.filter(model="cellline")
                )

        return super().formfield_for_foreignkey(db_field, request, **kwargs)


class SpeciesForm(forms.ModelForm):
    class Meta:
        model = Species
        fields = "__all__"

    def clean_latin_name(self):
        if not self.instance.pk:
            qs = Species.objects.filter(name_for_search=self.cleaned_data["latin_name"])

            if "common_name" in self.cleaned_data.keys():
                qs = qs | Species.objects.filter(
                    name_for_search=self.cleaned_data["common_name"]
                )

            if qs:
                raise forms.ValidationError("The name of an organism must be unique")
            else:
                return self.cleaned_data["latin_name"]
        else:
            return self.cleaned_data["latin_name"]

    def clean_common_name(self):
        if not self.instance.pk:
            qs = Species.objects.filter(
                name_for_search=self.cleaned_data["common_name"]
            )

            if "latin_name" in self.cleaned_data.keys():
                qs = qs | Species.objects.filter(
                    name_for_search=self.cleaned_data["latin_name"]
                )

            if qs:
                raise forms.ValidationError("The name of an organism must be unique")
            else:
                return self.cleaned_data["common_name"]
        else:
            return self.cleaned_data["common_name"]


class SpeciesAdmin(admin.ModelAdmin):
    list_display = ("name", "risk_group")
    list_display_links = ("name",)
    list_per_page = 25
    search_fields = ["name_for_search"]
    ordering = ["name_for_search"]
    fields = ["latin_name", "common_name", "risk_group", "show_in_cell_line_collection"]
    form = SpeciesForm

    @admin.display(description="name")
    def name(self, instance):
        return instance.name_for_search
