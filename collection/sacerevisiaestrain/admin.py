from django.contrib import admin
from django.urls import resolve
from django.utils.safestring import mark_safe

from common.admin import (
    AddDocFileInlineMixin,
    DocFileInlineMixin,
)
from formz.actions import formz_as_html

from ..sacerevisiaestrain.models import (
    SaCerevisiaeStrainDoc,
    SaCerevisiaeStrainEpisomalPlasmid,
)
from ..shared.admin import (
    CollectionUserProtectionAdmin,
    CustomGuardedModelAdmin,
    SortAutocompleteResultsId,
)
from .actions import export_sacerevisiaestrain
from .forms import SaCerevisiaeStrainAdminForm
from .search import SaCerevisiaeStrainQLSchema


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


class SaCerevisiaeStrainAdmin(
    SortAutocompleteResultsId,
    CustomGuardedModelAdmin,
    CollectionUserProtectionAdmin,
):
    list_display = ("id", "name", "mating_type", "background", "created_by", "approval")
    list_display_links = ("id",)
    djangoql_schema = SaCerevisiaeStrainQLSchema
    actions = [export_sacerevisiaestrain, formz_as_html]
    form = SaCerevisiaeStrainAdminForm
    search_fields = ["id", "name"]
    show_plasmids_in_model = True
    autocomplete_fields = [
        "parent_1",
        "parent_2",
        "integrated_plasmids",
        "cassette_plasmids",
        "formz_projects",
        "formz_gentech_methods",
        "sequence_features",
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
        "sequence_features",
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
