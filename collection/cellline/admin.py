from django.contrib import admin
from django.urls import resolve
from django.utils.safestring import mark_safe

from common.admin import (
    AddDocFileInlineMixin,
    DocFileInlineMixin,
)
from formz.actions import formz_as_html
from formz.models import Species

from ..shared.admin import (
    CollectionUserProtectionAdmin,
    CustomGuardedModelAdmin,
    SortAutocompleteResultsId,
)
from .actions import export_cellline
from .models import CellLineDoc, CellLineEpisomalPlasmid
from .search import CellLineQLSchema


class CellLineDocAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "name",
    )
    list_display_links = (
        "id",
        "name",
    )
    list_per_page = 25
    ordering = ["id"]

    def has_module_permission(self, request):
        """Hide module from Admin"""
        return False

    def get_readonly_fields(self, request, obj=None):
        """Override default get_readonly_fields"""

        if obj:
            return [
                "name",
                "description",
                "date_of_test",
                "cell_line",
                "created_date_time",
            ]

    def add_view(self, request, extra_context=None):
        """Override default add_view to show only desired fields"""

        self.fields = ["name", "description", "cell_line", "comment", "date_of_test"]
        return super().add_view(request)

    def change_view(self, request, object_id, extra_context=None):
        """Override default change_view to show only desired fields"""

        self.fields = [
            "name",
            "description",
            "date_of_test",
            "cell_line",
            "comment",
            "created_date_time",
        ]
        return super().change_view(request, object_id)


class CellLineDocInline(DocFileInlineMixin):
    """Inline to view existing cell line documents"""

    model = CellLineDoc
    fields = ["description", "date_of_test", "get_doc_short_name", "comment"]
    readonly_fields = fields[:-1]


class AddCellLineDocInline(AddDocFileInlineMixin):
    """Inline to add new cell line documents"""

    model = CellLineDoc
    fields = ["description", "date_of_test", "name", "comment"]


class CellLineEpisomalPlasmidInline(admin.TabularInline):
    autocomplete_fields = ["plasmid", "formz_projects"]
    model = CellLineEpisomalPlasmid
    verbose_name_plural = mark_safe(
        'Transiently transfected plasmids <span style="text-transform:lowercase;">'
        '(virus packaging plasmids are highlighted in <span style="color:var(--accent)">'
        "yellow</span>)</span>"
    )
    verbose_name = "Episomal Plasmid"
    extra = 0
    template = "admin/tabular.html"

    def get_parent_object(self, request):
        """
        Returns the parent object from the request or None.
        """

        resolved = resolve(request.path_info)
        if resolved.kwargs:
            return self.parent_model.objects.get(pk=resolved.kwargs["object_id"])
        return None

    def get_queryset(self, request):
        """Do not show as collapsed in add view"""

        parent_object = self.get_parent_object(request)
        self.classes = ["collapse"]

        if parent_object:
            parent_obj_episomal_plasmids = parent_object.episomal_plasmids.all()
            if parent_obj_episomal_plasmids.filter(
                celllineepisomalplasmid__s2_work_episomal_plasmid=True
            ):
                self.classes = None
        else:
            self.classes = None
        return super().get_queryset(request)


class CellLineAdmin(
    SortAutocompleteResultsId, CustomGuardedModelAdmin, CollectionUserProtectionAdmin
):
    list_display = ("id", "name", "box_name", "created_by", "approval")
    list_display_links = ("id",)
    djangoql_schema = CellLineQLSchema
    inlines = [CellLineEpisomalPlasmidInline, CellLineDocInline, AddCellLineDocInline]
    actions = [export_cellline, formz_as_html]
    search_fields = ["id", "name"]
    show_plasmids_in_model = True
    autocomplete_fields = [
        "parental_line",
        "integrated_plasmids",
        "formz_projects",
        "zkbs_cell_line",
        "formz_gentech_methods",
        "sequence_features",
    ]
    obj_specific_fields = [
        "name",
        "box_name",
        "alternative_name",
        "parental_line",
        "organism",
        "cell_type_tissue",
        "culture_type",
        "growth_condition",
        "freezing_medium",
        "received_from",
        "integrated_plasmids",
        "description_comment",
        "s2_work",
        "formz_projects",
        "formz_risk_group",
        "zkbs_cell_line",
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
            {"fields": obj_specific_fields[:13]},
        ],
        [
            "FormZ",
            {"classes": tuple(), "fields": obj_specific_fields[13:]},
        ],
    ]
    change_view_fieldsets = [
        [
            None,
            {"fields": obj_specific_fields[:13] + obj_unmodifiable_fields},
        ],
        [
            "FormZ",
            {"classes": (("collapse",)), "fields": obj_specific_fields[13:]},
        ],
    ]

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        try:
            request.resolver_match.args[0]
        except Exception:
            # For organism field, only show those species for
            # which show_in_cell_line_collect was ticked
            if db_field.name == "organism":
                kwargs["queryset"] = Species.objects.filter(
                    show_in_cell_line_collection=True
                )

        return super().formfield_for_foreignkey(db_field, request, **kwargs)
