from django.contrib import admin
from djangoql.schema import DjangoQLSchema
from import_export import resources

from collection.admin.shared import (
    CollectionSimpleAdmin,
    FieldApplication,
    FieldLocation,
)
from collection.models import Antibody, AntibodyDoc
from common.shared import AddDocFileInlineMixin, DocFileInlineMixin, export_objects


class AntibodyQLSchema(DjangoQLSchema):
    """Customize search functionality for Antibody"""

    def get_fields(self, model):
        """Define fields that can be searched"""

        if model == Antibody:
            return [
                "id",
                "name",
                "species_isotype",
                "clone",
                "received_from",
                "catalogue_number",
                "info_sheet",
                FieldLocation(),
                FieldApplication(),
                "description_comment",
                "info_sheet",
                "availability",
            ]
        return super().get_fields(model)


class AntibodyExportResource(resources.ModelResource):
    """Defines a custom export resource class for Antibody"""

    class Meta:
        model = Antibody
        fields = (
            "id",
            "name",
            "species_isotype",
            "clone",
            "received_from",
            "catalogue_number",
            "l_ocation",
            "a_pplication",
            "description_comment",
            "info_sheet",
            "availability",
        )
        export_order = fields


@admin.action(description="Export selected antibodies")
def export_antibody(modeladmin, request, queryset):
    """Export Antibody"""

    export_data = AntibodyExportResource().export(queryset)
    return export_objects(request, queryset, export_data)


class AntibodyDocInline(DocFileInlineMixin):
    """Inline to view existing Antibody documents"""

    model = AntibodyDoc


class AntibodyAddDocInline(AddDocFileInlineMixin):
    """Inline to add new Antibody documents"""

    model = AntibodyDoc


class AntibodyPage(CollectionSimpleAdmin):
    list_display = (
        "id",
        "name",
        "catalogue_number",
        "received_from",
        "species_isotype",
        "clone",
        "l_ocation",
        "get_sheet_short_name",
        "availability",
    )
    list_display_links = ("id",)
    djangoql_schema = AntibodyQLSchema
    actions = [export_antibody]
    search_fields = ["id", "name"]
    inlines = [AntibodyDocInline, AntibodyAddDocInline]
    clone_ignore_fields = ["info_sheet"]
    obj_specific_fields = [
        "name",
        "species_isotype",
        "clone",
        "received_from",
        "catalogue_number",
        "l_ocation",
        "a_pplication",
        "description_comment",
        "info_sheet",
        "availability",
    ]
    obj_unmodifiable_fields = [
        "created_date_time",
        "last_changed_date_time",
    ]
    add_view_fieldsets = [
        [
            None,
            {"fields": obj_specific_fields},
        ],
    ]
    change_view_fieldsets = [
        [
            None,
            {"fields": obj_specific_fields + obj_unmodifiable_fields},
        ],
    ]
    history_array_fields = {
        "history_documents": AntibodyDoc,
    }
