from django import forms
from django.contrib import admin
from django.contrib.auth.models import User
from django.urls import resolve
from django.utils.safestring import mark_safe
from djangoql.schema import DjangoQLSchema, StrField
from import_export import resources
from import_export.fields import Field

from collection.admin.shared import (
    CollectionUserProtectionAdmin,
    CustomGuardedModelAdmin,
    FieldCassettePlasmidM2M,
    FieldCreated,
    FieldEpisomalPlasmidM2M,
    FieldFormZProject,
    FieldIntegratedPlasmidM2M,
    FieldLastChanged,
    FieldParent1,
    FieldParent2,
    FieldUse,
    SortAutocompleteResultsId,
    formz_as_html,
)
from collection.models import (
    Plasmid,
    SaCerevisiaeStrain,
    SaCerevisiaeStrainDoc,
    SaCerevisiaeStrainEpisomalPlasmid,
)
from common.search import (
    SearchCustomFieldUserLastnameWithOptions,
    SearchCustomFieldUserUsernameWithOptions,
)
from common.shared import (
    AddDocFileInlineMixin,
    DocFileInlineMixin,
    export_objects,
)
from formz.models import FormZBaseElement, FormZProject, GenTechMethod


class SearchFieldOptUsernameSaCerStrain(SearchCustomFieldUserUsernameWithOptions):
    id_list = (
        SaCerevisiaeStrain.objects.all().values_list("created_by", flat=True).distinct()
    )


class SearchFieldOptLastnameSaCerStrain(SearchCustomFieldUserLastnameWithOptions):
    id_list = (
        SaCerevisiaeStrain.objects.all().values_list("created_by", flat=True).distinct()
    )


class FieldEpisomalPlasmidFormZProjectSaCerStrain(StrField):
    name = "episomal_plasmids_formz_projects_title"
    suggest_options = True

    def get_options(self, search):
        return FormZProject.objects.all().values_list("short_title", flat=True)

    def get_lookup_name(self):
        return "sacerevisiaestrainepisomalplasmid__formz_projects__short_title"


class SaCerevisiaeStrainQLSchema(DjangoQLSchema):
    """Customize search functionality"""

    include = (
        SaCerevisiaeStrain,
        User,
    )  # Include only the relevant models to be searched

    def get_fields(self, model):
        """Define fields that can be searched"""

        if model == SaCerevisiaeStrain:
            return [
                "id",
                "name",
                "relevant_genotype",
                "mating_type",
                "chromosomal_genotype",
                FieldParent1(),
                FieldParent2(),
                "parental_strain",
                "construction",
                "modification",
                FieldIntegratedPlasmidM2M(),
                FieldCassettePlasmidM2M(),
                FieldEpisomalPlasmidM2M(),
                "plasmids",
                "selection",
                "phenotype",
                "background",
                "received_from",
                FieldUse(),
                "note",
                "reference",
                "created_by",
                FieldCreated(),
                FieldLastChanged(),
                FieldFormZProject(),
                FieldEpisomalPlasmidFormZProjectSaCerStrain(),
            ]
        elif model == User:
            return [
                SearchFieldOptUsernameSaCerStrain(),
                SearchFieldOptLastnameSaCerStrain(),
            ]
        return super().get_fields(model)


class SaCerevisiaeStrainExportResource(resources.ModelResource):
    """Defines a custom export resource class for SaCerevisiaeStrain"""

    episomal_plasmids_in_stock = Field()
    other_plasmids = Field(attribute="plasmids", column_name="other_plasmids_info")
    additional_parental_strain_info = Field(
        attribute="parental_strain", column_name="additional_parental_strain_info"
    )

    def dehydrate_episomal_plasmids_in_stock(self, strain):
        return (
            str(
                tuple(
                    strain.episomal_plasmids.filter(
                        sacerevisiaestrainepisomalplasmid__present_in_stocked_strain=True
                    ).values_list("id", flat=True)
                )
            )
            .replace(" ", "")
            .replace(",)", ")")[1:-1]
        )

    class Meta:
        model = SaCerevisiaeStrain
        fields = (
            "id",
            "name",
            "relevant_genotype",
            "mating_type",
            "chromosomal_genotype",
            "parent_1",
            "parent_2",
            "additional_parental_strain_info",
            "construction",
            "modification",
            "integrated_plasmids",
            "cassette_plasmids",
            "episomal_plasmids_in_stock",
            "other_plasmids",
            "selection",
            "phenotype",
            "background",
            "received_from",
            "us_e",
            "note",
            "reference",
            "created_date_time",
            "created_by__username",
        )
        export_order = fields


@admin.action(description="Export selected strains")
def export_sacerevisiaestrain(modeladmin, request, queryset):
    """Export SaCerevisiaeStrain"""

    export_data = SaCerevisiaeStrainExportResource().export(queryset)
    return export_objects(request, queryset, export_data)


class SaCerevisiaeStrainForm(forms.ModelForm):
    class Meta:
        model = SaCerevisiaeStrain
        fields = "__all__"

    def clean_name(self):
        """Check if name is unique before saving"""

        if not self.instance.pk:
            qs = self._meta.model.objects.filter(name=self.cleaned_data["name"])
            if qs.exists():
                raise forms.ValidationError("Strain with this name already exists.")
            else:
                return self.cleaned_data["name"]
        else:
            return self.cleaned_data["name"]


class SaCerevisiaeStrainEpisomalPlasmidInline(admin.TabularInline):
    autocomplete_fields = ["plasmid", "formz_projects"]
    model = SaCerevisiaeStrainEpisomalPlasmid
    verbose_name_plural = mark_safe(
        'Episomal plasmids <span style="text-transform:lowercase;">'
        '(highlighted in <span style="color:var(--accent)">yellow</span>, '
        "if present in the stocked strain</span>)"
    )
    verbose_name = "Episomal Plasmid"
    ordering = (
        "-present_in_stocked_strain",
        "id",
    )
    extra = 0
    template = "admin/tabular.html"

    def get_parent_object(self, request):
        """
        Returns the parent object from the request or None.

        Note that this only works for Inlines, because the `parent_model`
        is not available in the regular admin.ModelAdmin as an attribute.
        """

        resolved = resolve(request.path_info)
        if resolved.kwargs:
            return self.parent_model.objects.get(pk=resolved.kwargs["object_id"])
        return None

    def get_queryset(self, request):
        """Modify to conditionally collapse inline if there is an episomal
        plasmid in the -80 stock"""

        self.classes = ["collapse"]

        parent_object = self.get_parent_object(request)
        if parent_object:
            parent_obj_episomal_plasmids = parent_object.episomal_plasmids.all()
            if parent_obj_episomal_plasmids.filter(
                sacerevisiaestrainepisomalplasmid__present_in_stocked_strain=True
            ):
                self.classes = []
        else:
            self.classes = []
        return super().get_queryset(request)


class SaCerevisiaeStrainDocInline(DocFileInlineMixin):
    """Inline to view existing Sa. cerevisiae strain documents"""

    model = SaCerevisiaeStrainDoc


class SaCerevisiaeStrainAddDocInline(AddDocFileInlineMixin):
    """Inline to add new Sa. cerevisiae strain documents"""

    model = SaCerevisiaeStrainDoc


class SaCerevisiaeStrainPage(
    SortAutocompleteResultsId,
    CustomGuardedModelAdmin,
    CollectionUserProtectionAdmin,
):
    list_display = ("id", "name", "mating_type", "background", "created_by", "approval")
    list_display_links = ("id",)
    djangoql_schema = SaCerevisiaeStrainQLSchema
    actions = [export_sacerevisiaestrain, formz_as_html]
    form = SaCerevisiaeStrainForm
    search_fields = ["id", "name"]
    m2m_save_ignore_fields = ["history_all_plasmids_in_stocked_strain"]
    show_plasmids_in_model = True
    autocomplete_fields = [
        "parent_1",
        "parent_2",
        "integrated_plasmids",
        "cassette_plasmids",
        "formz_projects",
        "formz_gentech_methods",
        "formz_elements",
    ]
    inlines = [
        SaCerevisiaeStrainEpisomalPlasmidInline,
        SaCerevisiaeStrainDocInline,
        SaCerevisiaeStrainAddDocInline,
    ]
    obj_specific_fields = [
        "name",
        "relevant_genotype",
        "mating_type",
        "chromosomal_genotype",
        "parent_1",
        "parent_2",
        "parental_strain",
        "construction",
        "modification",
        "integrated_plasmids",
        "cassette_plasmids",
        "plasmids",
        "selection",
        "phenotype",
        "background",
        "received_from",
        "us_e",
        "note",
        "reference",
        "formz_projects",
        "formz_risk_group",
        "formz_gentech_methods",
        "formz_elements",
        "destroyed_date",
    ]
    obj_unmodifiable_fields = [
        "created_date_time",
        "created_approval_by_pi",
        "last_changed_date_time",
        "last_changed_approval_by_pi",
        "created_by",
    ]
    add_view_fieldsets = [
        [
            None,
            {"fields": obj_specific_fields[:19]},
        ],
        [
            "FormZ",
            {
                "classes": tuple(),
                "fields": obj_specific_fields[19:],
            },
        ],
    ]
    change_view_fieldsets = [
        [
            None,
            {"fields": obj_specific_fields[:19] + obj_unmodifiable_fields},
        ],
        [
            "FormZ",
            {"classes": (("collapse",)), "fields": obj_specific_fields[19:]},
        ],
    ]
    history_array_fields = {
        "history_integrated_plasmids": Plasmid,
        "history_cassette_plasmids": Plasmid,
        "history_episomal_plasmids": Plasmid,
        "history_all_plasmids_in_stocked_strain": Plasmid,
        "history_formz_projects": FormZProject,
        "history_formz_gentech_methods": GenTechMethod,
        "history_formz_elements": FormZBaseElement,
        "history_documents": SaCerevisiaeStrainDoc,
    }

    def save_related(self, request, form, formsets, change):
        obj, history_obj = super().save_related(
            request,
            form,
            formsets,
            change,
        )

        plasmid_id_list = (
            obj.integrated_plasmids.all()
            | obj.cassette_plasmids.all()
            | obj.episomal_plasmids.filter(
                sacerevisiaestrainepisomalplasmid__present_in_stocked_strain=True
            )
        )
        if plasmid_id_list:
            obj.history_all_plasmids_in_stocked_strain = list(
                plasmid_id_list.order_by("id")
                .distinct("id")
                .values_list("id", flat=True)
            )
            obj.save_without_historical_record()

            history_obj.history_all_plasmids_in_stocked_strain = (
                obj.history_all_plasmids_in_stocked_strain
            )
            history_obj.save()

        # Clear non-relevant fields for in-stock episomal plasmids
        for (
            in_stock_episomal_plasmid
        ) in SaCerevisiaeStrainEpisomalPlasmid.objects.filter(
            sacerevisiae_strain__id=form.instance.id
        ).filter(present_in_stocked_strain=True):
            in_stock_episomal_plasmid.formz_projects.clear()
